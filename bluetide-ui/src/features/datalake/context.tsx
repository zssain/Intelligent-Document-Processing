import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datalakeService } from './services/datalake.service'
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
}

const DatalakeContext = createContext<DatalakeContextValue | null>(null)

// ---------------------------------------------------------------------------
// Normalise helpers
// ---------------------------------------------------------------------------

function normaliseS3(data: any): DatalakeFile[] {
  return (data?.pdfs ?? []).map((p: any) => ({
    id: p.key,
    name: p.key.split('/').pop() || p.key,
    source: 's3' as ConnectorSource,
    size: p.size ?? 0,
    modified: p.last_modified ?? '',
    url: undefined,
  }))
}

function normaliseSharePoint(data: any): DatalakeFile[] {
  return (data?.pdfs ?? []).map((p: any) => ({
    id: p.item_id,
    name: p.name,
    source: 'sharepoint' as ConnectorSource,
    size: p.size ?? 0,
    modified: p.lastModifiedDateTime ?? '',
    url: p.webUrl,
  }))
}

function normaliseGDrive(data: any): DatalakeFile[] {
  return (data?.pdfs ?? []).map((p: any) => ({
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
  })
  const spProbe = useQuery({
    queryKey: ['datalake-probe', 'sharepoint'],
    queryFn: () => datalakeService.sharepoint.list(1),
    retry: 0,
    staleTime: 60_000,
  })
  const gdProbe = useQuery({
    queryKey: ['datalake-probe', 'gdrive'],
    queryFn: () => datalakeService.gdrive.list(1),
    retry: 0,
    staleTime: 60_000,
  })

  const connectorStatuses: ConnectorStatus[] = [
    {
      source: 's3',
      status: s3Probe.isLoading ? 'syncing' : s3Probe.isError ? 'disconnected' : 'connected',
      totalFiles: (s3Probe.data as any)?.total_pdfs,
      message: s3Probe.error ? String(s3Probe.error) : undefined,
    },
    {
      source: 'sharepoint',
      status: spProbe.isLoading ? 'syncing' : spProbe.isError ? 'disconnected' : 'connected',
      totalFiles: (spProbe.data as any)?.total_pdfs,
      message: spProbe.error ? String(spProbe.error) : undefined,
    },
    {
      source: 'gdrive',
      status: gdProbe.isLoading ? 'syncing' : gdProbe.isError ? 'disconnected' : 'connected',
      totalFiles: (gdProbe.data as any)?.total_pdfs,
      message: gdProbe.error ? String(gdProbe.error) : undefined,
    },
  ]

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

  return (
    <DatalakeContext.Provider
      value={{
        activeSource,
        setActiveSource,
        files,
        isLoadingFiles,
        filesError: filesError as Error | null,
        refetchFiles: () => { refetchFiles() },
        connectorStatuses,
        triggerSync,
        isSyncing: syncMutation.isPending,
        lastSyncResult,
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
