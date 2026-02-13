import { useDatalake } from '../context'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import {
  RefreshCcw,
  Zap,
  CheckCircle2,
  XCircle,
  ArrowDownToLine,
  SkipForward,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useTranslation } from 'react-i18next'

export function SyncToolbar() {
  const { t } = useTranslation()
  const {
    triggerSync,
    isSyncing,
    lastSyncResult,
    refetchFiles,
  } = useDatalake()

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4 px-6 border border-border/40 bg-card/30 rounded-xl">
      {/* Left – action buttons */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="default"
          onClick={() => triggerSync({ limit: 10 })}
          disabled={isSyncing}
          className="gap-1.5"
        >
          {isSyncing ? (
            <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Zap className="h-3.5 w-3.5" />
          )}
          {isSyncing ? t('datalake.syncing') : t('datalake.sync_now')}
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={() => triggerSync({ force: true, full_scan: true, limit: 10 })}
          disabled={isSyncing}
          className="gap-1.5"
        >
          <RefreshCcw className="h-3.5 w-3.5" />
          {t('datalake.full_resync')}
        </Button>

        <Button
          size="sm"
          variant="ghost"
          onClick={refetchFiles}
          className="gap-1.5"
        >
          <RefreshCcw className="h-3.5 w-3.5" />
          {t('datalake.refresh_list')}
        </Button>
      </div>

      {/* Right – last sync result */}
      {lastSyncResult && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge variant="outline" className="gap-1 font-mono">
            <ArrowDownToLine className="h-3 w-3 text-emerald-400" />
            {lastSyncResult.ingested} {t('datalake.result_ingested')}
          </Badge>
          {lastSyncResult.updated > 0 && (
            <Badge variant="outline" className="gap-1 font-mono">
              <RefreshCcw className="h-3 w-3 text-blue-400" />
              {lastSyncResult.updated} {t('datalake.result_updated')}
            </Badge>
          )}
          <Badge variant="outline" className="gap-1 font-mono">
            <SkipForward className="h-3 w-3 text-muted-foreground" />
            {lastSyncResult.skipped} {t('datalake.result_skipped')}
          </Badge>
          {lastSyncResult.failed > 0 && (
            <Badge variant="destructive" className="gap-1 font-mono">
              <XCircle className="h-3 w-3" />
              {lastSyncResult.failed} {t('datalake.result_failed')}
            </Badge>
          )}
          {lastSyncResult.failed === 0 && lastSyncResult.ingested + lastSyncResult.updated > 0 && (
            <CheckCircle2 className={cn('h-4 w-4 text-emerald-400')} />
          )}
        </div>
      )}
    </div>
  )
}
