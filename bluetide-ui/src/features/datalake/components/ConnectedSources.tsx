import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  HardDrive,
  Globe,
  Trash2,
  ExternalLink,
  FolderOpen,
  Loader2,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { sourcesService } from '../services/sources.service'
import { useIngestionMode } from '@/features/documents/ingestion-mode-context'
import type { SourceConnection } from '../types'

interface ConnectedSourcesProps {
  /** Called when a user clicks "Browse" on a connection — loads its files into the datalake context */
  onBrowse?: (connectionId: string, provider: string) => void
}

export function ConnectedSources({ onBrowse }: ConnectedSourcesProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: rawConnections = [], isLoading } = useQuery<SourceConnection[]>({
    queryKey: ['source-connections'],
    queryFn: () => sourcesService.listConnections(),
    staleTime: 30_000,
  })

  const connections = Array.isArray(rawConnections) ? rawConnections : []

  // Get active ingestion mode so we only show connections for the current tab
  const { activeMode } = useIngestionMode()

  // Filter connections to only show those matching the active mode
  const filteredConnections = connections.filter(
    (c) => c.provider === activeMode
  )

  const disconnectMutation = useMutation({
    mutationFn: (id: string) => sourcesService.disconnectSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['source-connections'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        {t('documents.sources.loading', 'Loading connections…')}
      </div>
    )
  }

  if (filteredConnections.length === 0) return null

  const providerIcon = (provider: string) =>
    provider === 'gdrive' ? (
      <HardDrive className="h-4 w-4 text-blue-500" />
    ) : (
      <Globe className="h-4 w-4 text-teal-500" />
    )

  const providerLabel = (provider: string) =>
    provider === 'gdrive'
      ? t('documents.modes.gdrive', 'Google Drive')
      : t('documents.modes.sharepoint', 'SharePoint')

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {t('documents.sources.connected_title', 'Linked Sources')}
      </h4>

      <div className="grid gap-2">
        {filteredConnections.map((conn) => (
          <div
            key={conn.connection_id}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border/50 bg-card/30 hover:bg-card/60 transition-colors group"
          >
            {/* Provider icon */}
            {providerIcon(conn.provider)}

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{conn.label}</span>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {providerLabel(conn.provider)}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                <span>
                  {t('documents.sources.file_count', '{{count}} files', {
                    count: conn.file_count,
                  })}
                </span>
                <span className="text-border">·</span>
                <span>{new Date(conn.connected_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Open original URL */}
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                asChild
              >
                <a href={conn.original_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </Button>

              {/* Browse files */}
              {onBrowse && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => onBrowse(conn.connection_id, conn.provider)}
                  title={t('documents.sources.browse', 'Browse files')}
                >
                  <FolderOpen className="h-3.5 w-3.5" />
                </Button>
              )}

              {/* Disconnect */}
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive"
                disabled={disconnectMutation.isPending}
                onClick={() => disconnectMutation.mutate(conn.connection_id)}
                title={t('documents.connection.disconnect', 'Disconnect')}
              >
                {disconnectMutation.isPending &&
                  disconnectMutation.variables === conn.connection_id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
