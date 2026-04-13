import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { oauthService, type OAuthProvider } from '../services/oauth.service'
import { sourcesService } from '@/features/datalake/services/sources.service'
import { useIngestionMode } from '../ingestion-mode-context'
import { Button } from '@/shared/components/ui/button'
import {
  Link2,
  Unlink,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Info,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useTranslation } from 'react-i18next'
import { useCallback, useEffect, useMemo } from 'react'
import type { SourceConnection } from '@/features/datalake/types'

/**
 * Shows the OAuth connection status for the currently active connector mode
 * (Google Drive or SharePoint) and provides Connect / Disconnect actions.
 *
 * Also checks for linked source connections — if a source folder is linked
 * but the user hasn't completed personal OAuth, it shows a helpful message.
 *
 * Hidden when in Upload or S3 mode (no per-user OAuth needed).
 */
export function ConnectionStatus() {
  const { t } = useTranslation()
  const { activeMode, isConnectorMode } = useIngestionMode()
  const queryClient = useQueryClient()

  // Only show for Google Drive (per-user OAuth needed)
  const oauthProviders: OAuthProvider[] = ['gdrive']
  const isOAuthMode = isConnectorMode && oauthProviders.includes(activeMode as OAuthProvider)
  const provider = activeMode as OAuthProvider

  // Fetch connection status
  const { data: connections, isLoading } = useQuery({
    queryKey: ['oauth-connections'],
    queryFn: () => oauthService.getConnections(),
    enabled: isOAuthMode,
    staleTime: 30_000,
    retry: 1,
  })

  // Fetch linked source connections to check if a folder is already linked
  const { data: rawLinkedSources = [] } = useQuery<SourceConnection[]>({
    queryKey: ['source-connections'],
    queryFn: () => sourcesService.listConnections(),
    enabled: isOAuthMode,
    staleTime: 30_000,
  })

  const linkedSources = Array.isArray(rawLinkedSources) ? rawLinkedSources : []

  // Check if there's a linked source for the current provider
  const hasLinkedSource = useMemo(() => {
    return linkedSources.some((s) => s.provider === provider)
  }, [linkedSources, provider])

  // Check if OAuth is configured on the server (from connections response)
  const info = connections?.[provider]
  const isOAuthConfigured = info?.oauth_configured !== false

  // Listen for postMessage from OAuth popup (sent on success)
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'oauth-success') {
        // Refresh connection status immediately
        queryClient.invalidateQueries({ queryKey: ['oauth-connections'] })
        // Also refresh datalake probes
        queryClient.invalidateQueries({ queryKey: ['datalake-probe'] })
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [queryClient])

  // Connect mutation — opens OAuth consent in a new window
  const connectMutation = useMutation({
    mutationFn: (p: OAuthProvider) => oauthService.getConnectUrl(p),
    onSuccess: (url) => {
      const popup = window.open(url, 'oauth_popup', 'width=600,height=700')
      // Poll for popup close to refresh status (fallback if postMessage fails)
      if (popup) {
        const interval = setInterval(() => {
          try {
            if (popup.closed) {
              clearInterval(interval)
              queryClient.invalidateQueries({ queryKey: ['oauth-connections'] })
              queryClient.invalidateQueries({ queryKey: ['datalake-probe'] })
            }
          } catch {
            clearInterval(interval)
          }
        }, 1000)
      }
    },
    retry: false,
  })

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: (p: OAuthProvider) => oauthService.disconnect(p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-connections'] })
    },
  })

  const handleConnect = useCallback(() => {
    connectMutation.mutate(provider)
  }, [connectMutation, provider])

  const handleDisconnect = useCallback(() => {
    disconnectMutation.mutate(provider)
  }, [disconnectMutation, provider])

  // Don't render for S3 or Upload modes
  if (!isOAuthMode) return null

  // SharePoint with app-only credentials — show "ready" status instead of OAuth warning
  const isAppOnlyMode = provider === 'sharepoint' && (info as any)?.auth_mode === 'app_only'

  // If OAuth is not configured AND not app-only, show informational message
  if (!isLoading && !isOAuthConfigured && !isAppOnlyMode) {
    const providerLabel = provider === 'gdrive' ? 'Google Drive' : 'SharePoint'

    // If there's a linked source, show a softer message
    if (hasLinkedSource) {
      return (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-blue-500/30 bg-blue-500/5">
          <Info className="h-4 w-4 text-blue-500 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">
              {providerLabel} folder linked
            </p>
            <p className="text-[11px] text-muted-foreground">
              A {providerLabel} folder is linked. Use "Refresh" below to list files, or connect your personal account for direct access.
            </p>
          </div>
        </div>
      )
    }

    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-border/40 bg-muted/30">
        <AlertTriangle className="h-4 w-4 text-muted-foreground shrink-0" />
        <p className="text-sm text-muted-foreground">
          {providerLabel} OAuth is not configured on the server.
          Contact your admin to set up {providerLabel} credentials.
        </p>
      </div>
    )
  }

  // SharePoint in app-only mode: show "ready" status with no connect/disconnect needed
  if (!isLoading && isAppOnlyMode) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">
            SharePoint connected via admin credentials
          </p>
          <p className="text-[11px] text-muted-foreground">
            Paste a SharePoint folder URL below to connect and ingest files.
          </p>
        </div>
      </div>
    )
  }

  const isConnected = info?.connected ?? false
  const isPending = connectMutation.isPending || disconnectMutation.isPending

  // If not connected via OAuth but has a linked source, show a combined message
  if (!isLoading && !isConnected && hasLinkedSource) {
    const providerLabel = provider === 'gdrive' ? 'Google Drive' : 'SharePoint'
    return (
      <div className="flex items-center justify-between gap-4 px-4 py-3 rounded-xl border border-blue-500/30 bg-blue-500/5 transition-colors">
        <div className="flex items-center gap-3 min-w-0">
          <Info className="h-4 w-4 text-blue-500 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">
              {providerLabel} folder linked
            </p>
            <p className="text-[11px] text-muted-foreground">
              Connect your personal {providerLabel} account to access files directly.
            </p>
          </div>
        </div>
        <div className="shrink-0">
          <Button
            size="sm"
            variant="default"
            onClick={handleConnect}
            disabled={isPending}
            className="gap-1.5"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Link2 className="h-3.5 w-3.5" />
            )}
            {t('documents.connection.connect')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4 px-4 py-3 rounded-xl border transition-colors',
        isConnected
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-amber-500/30 bg-amber-500/5',
      )}
    >
      {/* Left: status */}
      <div className="flex items-center gap-3 min-w-0">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : isConnected ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
        )}

        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">
            {isConnected
              ? t('documents.connection.connected', {
                provider: provider === 'gdrive' ? 'Google Drive' : 'SharePoint',
              })
              : t('documents.connection.not_connected', {
                provider: provider === 'gdrive' ? 'Google Drive' : 'SharePoint',
              })}
          </p>
          {isConnected && info?.email && (
            <p className="text-[11px] text-muted-foreground truncate">{info.email}</p>
          )}
          {!isConnected && info?.error_reason && (
            <p className="text-[11px] text-destructive truncate">{info.error_reason}</p>
          )}
        </div>
      </div>

      {/* Right: action button */}
      <div className="shrink-0">
        {isConnected ? (
          <Button
            size="sm"
            variant="outline"
            onClick={handleDisconnect}
            disabled={isPending}
            className="gap-1.5 text-destructive hover:text-destructive"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Unlink className="h-3.5 w-3.5" />
            )}
            {t('documents.connection.disconnect')}
          </Button>
        ) : (
          <Button
            size="sm"
            variant="default"
            onClick={handleConnect}
            disabled={isPending}
            className="gap-1.5"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Link2 className="h-3.5 w-3.5" />
            )}
            {t('documents.connection.connect')}
          </Button>
        )}
      </div>
    </div>
  )
}

