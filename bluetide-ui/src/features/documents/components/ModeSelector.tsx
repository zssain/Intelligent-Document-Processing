import { cn } from '@/shared/lib/utils'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import {
  Cloud,
  Share2,
  HardDrive,
  Upload,
} from 'lucide-react'
import { useIngestionMode, type IngestionMode } from '../ingestion-mode-context'
import { useTranslation } from 'react-i18next'
import { usePermissions } from '@/shared/hooks/usePermissions'

// ---------------------------------------------------------------------------
// Mode metadata
// ---------------------------------------------------------------------------

const MODE_META: Record<
  IngestionMode,
  {
    icon: typeof Cloud
    color: string
    gradient: string
    labelKey: string
    descKey: string
  }
> = {
  s3: {
    icon: Cloud,
    color: 'text-amber-400',
    gradient: 'from-amber-500/20 to-amber-600/5',
    labelKey: 'documents.modes.s3',
    descKey: 'documents.modes.s3_desc',
  },
  sharepoint: {
    icon: Share2,
    color: 'text-blue-400',
    gradient: 'from-blue-500/20 to-blue-600/5',
    labelKey: 'documents.modes.sharepoint',
    descKey: 'documents.modes.sharepoint_desc',
  },
  gdrive: {
    icon: HardDrive,
    color: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
    labelKey: 'documents.modes.gdrive',
    descKey: 'documents.modes.gdrive_desc',
  },
  upload: {
    icon: Upload,
    color: 'text-violet-400',
    gradient: 'from-violet-500/20 to-violet-600/5',
    labelKey: 'documents.modes.upload',
    descKey: 'documents.modes.upload_desc',
  },
}

export function ModeSelector() {
  const { t } = useTranslation()
  const { activeMode, setMode } = useIngestionMode()
  const { canViewSource, isAdmin } = usePermissions()

  // Source key mapping: ingestion mode -> permission source name
  const modeToSource: Record<IngestionMode, string> = {
    s3: 's3',
    sharepoint: 'sharepoint',
    gdrive: 'gdrive',
    upload: 'direct_upload',
  }

  // Filter modes based on permissions
  const allowedModes = (['s3', 'sharepoint', 'gdrive', 'upload'] as IngestionMode[]).filter(
    (mode) => isAdmin || canViewSource(modeToSource[mode])
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-1">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
          {t('documents.modes.title')}
        </h3>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {allowedModes.map((mode) => {
          const meta = MODE_META[mode]
          const isActive = activeMode === mode
          const Icon = meta.icon

          return (
            <Card
              key={mode}
              role="button"
              tabIndex={0}
              onClick={() => setMode(mode)}
              onKeyDown={(e) => e.key === 'Enter' && setMode(mode)}
              className={cn(
                'cursor-pointer transition-all duration-200 hover:shadow-lg border-2 relative overflow-hidden',
                isActive
                  ? 'border-primary/60 shadow-primary/10 shadow-md bg-gradient-to-br ' + meta.gradient
                  : 'border-transparent hover:border-border/60 bg-card/40 opacity-60 hover:opacity-100',
              )}
            >
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className={cn('p-2 rounded-lg bg-background/60', meta.color)}>
                    <Icon className="h-5 w-5" />
                  </div>
                  {isActive && (
                    <Badge variant="default" className="text-[9px] font-black uppercase">
                      {t('documents.modes.active')}
                    </Badge>
                  )}
                </div>

                <div>
                  <h4 className="font-bold text-sm">{t(meta.labelKey)}</h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">
                    {t(meta.descKey)}
                  </p>
                </div>
              </CardContent>

              {/* Disabled overlay for non-active modes */}
              {!isActive && (
                <div className="absolute inset-0 bg-background/5 pointer-events-none" />
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
