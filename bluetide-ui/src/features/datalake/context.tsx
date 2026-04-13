import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datalakeService } from './services/datalake.service'
import { usePermissions } from '@/shared/hooks/usePermissions'
import type {
  ConnectorSource,
  DatalakeFile,
  SyncResponse,
  ConnectorStatus,
} from './types'

// ---------------------------------------------------------------------------
// Context value
// ---------------------------------------------------------------------------

interface DatalakeContextValue {
  /** Which connector tab is active */
  activeSource: ConnectorSource
  setActiveSource: (s: ConnectorSource) => void

  /** Normalised file list for active source */
  files: DatalakeFile[]
  isLoadingFiles: boolean
  filesError: Error | null
  refetchFiles: () => void

  /** Connector status list */
  connectorStatuses: ConnectorStatus[]

  /** Sync actions */
  triggerSync: (opts?: { force?: boolean; full_scan?: boolean; limit?: number }) => void
  isSyncing: boolean
  lastSyncResult: SyncResponse | null

  /** Selection state for multi-select */
  selectedIds: Set<string>
  selectedFiles: DatalakeFile[]
  toggleSelect: (id: string) => void
  toggleSelectAll: () => void
  clearSelection: () => void
  isAllSelected: boolean

  /** Permission helpers */
  canSyncActive: boolean
  canDownloadActive: boolean
}

const DatalakeContext = createContext<DatalakeContextValue | null>(null)

// ---------------------------------------------------------------------------
// Normalise helpers
// ---------------------------------------------------------------------------

function normaliseS3(data: any): DatalakeFile[] {
  return (data?.files ?? data?.pdfs ?? []).map((p: any) => ({
    id: p.key,
    name: p.key.split('/').pop() || p.key,
    source: 's3' as ConnectorSource,
    size: p.size ?? 0,
    modified: p.last_modified ?? '',
    url: undefined,
  }))
}

function normaliseSharePoint(data: any): DatalakeFile[] {
  return (data?.files ?? data?.pdfs ?? []).map((p: any) => ({
    id: p.item_id,
    name: p.name,
    source: 'sharepoint' as ConnectorSource,
    size: p.size ?? 0,
    modified: p.lastModifiedDateTime ?? '',
    url: p.webUrl,
  }))
}

function normaliseGDrive(data: any): DatalakeFile[] {
  return (data?.files ?? data?.pdfs ?? []).map((p: any) => ({
    id: p.file_id,
    name: p.name,
    source: 'gdrive' as ConnectorSource,
    size: p.size ?? 0,
    modified: p.modifiedTime ?? '',
    url: p.webViewLink,
  }))
}

const NORMALIZERS: Record<ConnectorSource, (d: any) => DatalakeFile[]> = {
  s3: normaliseS3,
  sharepoint: normaliseSharePoint,
  gdrive: normaliseGDrive,
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function DatalakeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { canViewSource, canSyncSource, canDownloadSource, allowedSources } = usePermissions()
  const [activeSource, setActiveSource] = useState<ConnectorSource>('s3')
  const [lastSyncResult, setLastSyncResult] = useState<SyncResponse | null>(null)

  // ------ List query ------
  const {
    data: rawData,
    isLoading: isLoadingFiles,
    error: filesError,
    refetch: refetchFiles,
  } = useQuery<any>({
    queryKey: ['datalake-list', activeSource],
    queryFn: () => (datalakeService as any)[activeSource].list(100),
    retry: 1,
    staleTime: 30_000,
  })

  const files: DatalakeFile[] = rawData ? (NORMALIZERS as any)[activeSource](rawData) : []

  // ------ Connector statuses (parallel probes) ------
  const s3Probe = useQuery({
    queryKey: ['datalake-probe', 's3'],
    queryFn: () => datalakeService.s3.list(1),
    retry: 0,
    staleTime: 60_000,
    enabled: canViewSource('s3'),
  })
  const spProbe = useQuery({
    queryKey: ['datalake-probe', 'sharepoint'],
    queryFn: () => datalakeService.sharepoint.list(1),
    retry: 0,
    staleTime: 60_000,
    enabled: canViewSource('sharepoint'),
  })
  const gdProbe = useQuery({
    queryKey: ['datalake-probe', 'gdrive'],
    queryFn: () => datalakeService.gdrive.list(1),
    retry: 0,
    staleTime: 60_000,
    enabled: canViewSource('gdrive'),
  })

  /** Helper: check if a probe response indicates the connector is actually configured */
  function isConnectorConfigured(data: any): boolean {
    // Backend returns 200 with _note when not configured or empty
    // But if there's a _note but also total_files >= 0, it's still valid
    if (data == null) return false
    // If there's no _note, it's definitely configured
    if (!data._note) return true
    // If there IS a _note but also files/data, treat as configured
    if ((data.total_files ?? data.total_pdfs ?? 0) > 0) return true
    return false
  }

  const allConnectorStatuses: ConnectorStatus[] = [
    {
      source: 's3',
      status: s3Probe.isLoading ? 'syncing' : (s3Probe.isError || !isConnectorConfigured(s3Probe.data)) ? 'disconnected' : 'connected',
      totalFiles: isConnectorConfigured(s3Probe.data) ? ((s3Probe.data as any)?.total_files ?? (s3Probe.data as any)?.total_pdfs) : undefined,
      message: s3Probe.isError ? String(s3Probe.error) : (s3Probe.data as any)?._note,
    },
    {
      source: 'sharepoint',
      status: spProbe.isLoading ? 'syncing' : (spProbe.isError || !isConnectorConfigured(spProbe.data)) ? 'disconnected' : 'connected',
      totalFiles: isConnectorConfigured(spProbe.data) ? ((spProbe.data as any)?.total_files ?? (spProbe.data as any)?.total_pdfs) : undefined,
      message: spProbe.isError ? String(spProbe.error) : (spProbe.data as any)?._note,
    },
    {
      source: 'gdrive',
      status: gdProbe.isLoading ? 'syncing' : (gdProbe.isError || !isConnectorConfigured(gdProbe.data)) ? 'disconnected' : 'connected',
      totalFiles: isConnectorConfigured(gdProbe.data) ? ((gdProbe.data as any)?.total_files ?? (gdProbe.data as any)?.total_pdfs) : undefined,
      message: gdProbe.isError ? String(gdProbe.error) : (gdProbe.data as any)?._note,
    },
  ]

  // Filter connector statuses to only show sources user has access to
  const connectorStatuses = allConnectorStatuses.filter(
    (c) => canViewSource(c.source)
  )

  // ------ Sync mutation ------
  const syncMutation = useMutation<SyncResponse, Error, { force?: boolean; full_scan?: boolean; limit?: number }>({
    mutationFn: (opts) =>
      (datalakeService as any)[activeSource].sync(opts),
    onSuccess: (result: SyncResponse) => {
      setLastSyncResult(result)
      // Invalidate file list for the active source
      queryClient.invalidateQueries({ queryKey: ['datalake-list', activeSource] })
      queryClient.invalidateQueries({ queryKey: ['datalake-probe', activeSource] })
    },
  })

  const triggerSync = useCallback(
    (opts?: { force?: boolean; full_scan?: boolean; limit?: number }) => {
      syncMutation.mutate(opts ?? {})
    },
    [syncMutation],
  )

  // ------ Selection state ------
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Clear selection when source changes
  const setActiveSourceWithClear = useCallback((s: ConnectorSource) => {
    setActiveSource(s)
    setSelectedIds(new Set())
  }, [])

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === files.length && files.length > 0) {
        return new Set()
      }
      return new Set(files.map((f) => f.id))
    })
  }, [files])

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const isAllSelected = files.length > 0 && selectedIds.size === files.length

  const selectedFiles = useMemo(
    () => files.filter((f) => selectedIds.has(f.id)),
    [files, selectedIds],
  )

  return (
    <DatalakeContext.Provider
      value={{
        activeSource,
        setActiveSource: setActiveSourceWithClear,
        files,
        isLoadingFiles,
        filesError: filesError as Error | null,
        refetchFiles: () => { refetchFiles() },
        connectorStatuses,
        triggerSync,
        isSyncing: syncMutation.isPending,
        lastSyncResult,
        selectedIds,
        selectedFiles,
        toggleSelect,
        toggleSelectAll,
        clearSelection,
        isAllSelected,
        canSyncActive: canSyncSource(activeSource),
        canDownloadActive: canDownloadSource(activeSource),
      }}
    >
      {children}
    </DatalakeContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDatalake() {
  const ctx = useContext(DatalakeContext)
  if (!ctx) throw new Error('useDatalake must be used inside <DatalakeProvider>')
  return ctx
}
