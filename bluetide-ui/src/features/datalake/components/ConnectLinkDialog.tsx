import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link2, Loader2, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Badge } from '@/shared/components/ui/badge'
import { sourcesService } from '../services/sources.service'
import type { ConnectLinkResponse } from '../types'

interface ConnectLinkDialogProps {
  /** Called after a successful connection */
  onConnected?: (result: ConnectLinkResponse) => void
}

export function ConnectLinkDialog({ onConnected }: ConnectLinkDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [isOpen, setIsOpen] = useState(false)
  const [url, setUrl] = useState('')
  const [label, setLabel] = useState('')

  const connectMutation = useMutation({
    mutationFn: () => sourcesService.connectViaLink(url, label || undefined),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['source-connections'] })
      setUrl('')
      setLabel('')
      setIsOpen(false)
      onConnected?.(data)
    },
  })

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!url.trim()) return
      connectMutation.mutate()
    },
    [url, connectMutation],
  )

  const isValidUrl = url.trim().length > 0 && (
    url.includes('drive.google.com') ||
    url.includes('docs.google.com') ||
    url.includes('sharepoint.com')
  )

  return (
    <div className="border border-border/50 rounded-lg bg-card/40 overflow-hidden">
      {/* Toggle header */}
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className="flex items-center justify-between w-full px-4 py-3 text-sm font-medium hover:bg-accent/50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-primary" />
          {t('documents.sources.connect_title', 'Connect via Link')}
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {/* Expandable form */}
      {isOpen && (
        <form onSubmit={handleSubmit} className="px-4 pb-4 space-y-3 border-t border-border/30 pt-3">
          <p className="text-xs text-muted-foreground">
            {t(
              'documents.sources.connect_description',
              'Paste a Google Drive or SharePoint folder URL. We\'ll verify access and list the files for processing.',
            )}
          </p>

          {/* URL input */}
          <div className="space-y-1.5">
            <Label htmlFor="source-url" className="text-xs">
              {t('documents.sources.url_label', 'Folder URL')}
            </Label>
            <Input
              id="source-url"
              type="url"
              placeholder="https://drive.google.com/drive/folders/... or https://yourorg.sharepoint.com/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={connectMutation.isPending}
              autoFocus
            />
          </div>

          {/* Optional label */}
          <div className="space-y-1.5">
            <Label htmlFor="source-label" className="text-xs">
              {t('documents.sources.label_field', 'Label (optional)')}
            </Label>
            <Input
              id="source-label"
              placeholder={t('documents.sources.label_placeholder', 'e.g. HR Documents')}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              disabled={connectMutation.isPending}
            />
          </div>

          {/* Error display */}
          {connectMutation.isError && (
            <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 rounded-md p-2">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                {(() => {
                  const err = connectMutation.error as any
                  const detail = err?.response?.data?.detail
                  // Backend returns { error: '...', message: '...' } in detail
                  if (detail?.message) return detail.message
                  if (typeof detail === 'string') return detail
                  // Axios network error (CORS block, server down, etc.)
                  if (err?.message === 'Network Error') {
                    return 'Cannot reach the server. Please check that the backend is running.'
                  }
                  return err?.message ||
                    t('documents.sources.connect_error', 'Failed to connect. Check the URL and try again.')
                })()}
              </span>
            </div>
          )}

          {/* Success display */}
          {connectMutation.isSuccess && (
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 rounded-md p-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>
                {t('documents.sources.connect_success', 'Connected! {{count}} files found.', {
                  count: connectMutation.data?.files?.length ?? 0,
                })}
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <Button
              type="submit"
              size="sm"
              disabled={!isValidUrl || connectMutation.isPending}
            >
              {connectMutation.isPending ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t('documents.sources.verifying', 'Verifying…')}
                </>
              ) : (
                <>
                  <Link2 className="h-3.5 w-3.5" />
                  {t('documents.sources.connect_btn', 'Connect & List Files')}
                </>
              )}
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsOpen(false)
                setUrl('')
                setLabel('')
                connectMutation.reset()
              }}
            >
              {t('common.cancel', 'Cancel')}
            </Button>

            {url && !isValidUrl && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                {t('documents.sources.unsupported_url', 'Unsupported URL')}
              </Badge>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
