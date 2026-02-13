import { cn } from '@/shared/lib/utils'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import {
  Cloud,
  Share2,
  HardDrive,
} from 'lucide-react'
import { useDatalake } from '../context'
import type { ConnectorSource, ConnectorStatus } from '../types'
import { useTranslation } from 'react-i18next'

const CONNECTOR_META: Record<
  ConnectorSource,
  { icon: typeof Cloud; color: string; gradient: string }
> = {
  s3: {
    icon: Cloud,
    color: 'text-amber-400',
    gradient: 'from-amber-500/20 to-amber-600/5',
  },
  sharepoint: {
    icon: Share2,
    color: 'text-blue-400',
    gradient: 'from-blue-500/20 to-blue-600/5',
  },
  gdrive: {
    icon: HardDrive,
    color: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
  },
}

function statusBadge(status: ConnectorStatus['status']) {
  const map: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
    connected: { variant: 'default', label: 'Connected' },
    disconnected: { variant: 'destructive', label: 'Disconnected' },
    syncing: { variant: 'secondary', label: 'Checking…' },
    error: { variant: 'destructive', label: 'Error' },
  }
  const m = map[status] ?? map.error
  return <Badge variant={m.variant} className="text-[10px] font-bold uppercase">{m.label}</Badge>
}

export function ConnectorCards() {
  const { t } = useTranslation()
  const { activeSource, setActiveSource, connectorStatuses } = useDatalake()

  const labels: Record<ConnectorSource, string> = {
    s3: t('datalake.connectors.s3'),
    sharepoint: t('datalake.connectors.sharepoint'),
    gdrive: t('datalake.connectors.gdrive'),
  }

  const descriptions: Record<ConnectorSource, string> = {
    s3: t('datalake.connectors.s3_desc'),
    sharepoint: t('datalake.connectors.sharepoint_desc'),
    gdrive: t('datalake.connectors.gdrive_desc'),
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {connectorStatuses.map((cs) => {
        const meta = CONNECTOR_META[cs.source]
        const isActive = activeSource === cs.source
        const Icon = meta.icon

        return (
          <Card
            key={cs.source}
            role="button"
            tabIndex={0}
            onClick={() => setActiveSource(cs.source)}
            onKeyDown={(e) => e.key === 'Enter' && setActiveSource(cs.source)}
            className={cn(
              'cursor-pointer transition-all duration-200 hover:shadow-lg border-2',
              isActive
                ? 'border-primary/60 shadow-primary/10 shadow-md bg-gradient-to-br ' + meta.gradient
                : 'border-transparent hover:border-border/60 bg-card/40',
            )}
          >
            <CardContent className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className={cn('p-2 rounded-lg bg-background/60', meta.color)}>
                  <Icon className="h-5 w-5" />
                </div>
                {statusBadge(cs.status)}
              </div>

              <div>
                <h3 className="font-bold text-sm">{labels[cs.source]}</h3>
                <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">
                  {descriptions[cs.source]}
                </p>
              </div>

              {cs.totalFiles !== undefined && (
                <p className="text-xs font-mono text-muted-foreground">
                  {cs.totalFiles} {t('datalake.pdf_files')}
                </p>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
