import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import { Badge } from '@/shared/components/ui/badge'
import { ExternalLink } from 'lucide-react'
import { useDatalake } from '../context'
import type { ConnectorSource } from '../types'
import { useTranslation } from 'react-i18next'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

const SOURCE_BADGE: Record<ConnectorSource, { label: string; cls: string }> = {
  s3: { label: 'S3', cls: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
  sharepoint: { label: 'SharePoint', cls: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
  gdrive: { label: 'Drive', cls: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' },
}

export function FileTable() {
  const { t } = useTranslation()
  const { files, isLoadingFiles, filesError, activeSource } = useDatalake()

  if (isLoadingFiles) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (filesError) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center gap-2">
        <p className="text-sm font-semibold text-destructive">{t('datalake.list_error')}</p>
        <p className="text-xs text-muted-foreground max-w-md">{String(filesError)}</p>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
        {t('datalake.no_files')}
      </div>
    )
  }

  const badge = SOURCE_BADGE[activeSource]

  return (
    <div className="rounded-xl border border-border/40 overflow-hidden bg-card/30">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent border-border/30">
            <TableHead className="font-bold text-[10px] uppercase tracking-widest">
              {t('datalake.col_name')}
            </TableHead>
            <TableHead className="font-bold text-[10px] uppercase tracking-widest">
              {t('datalake.col_source')}
            </TableHead>
            <TableHead className="font-bold text-[10px] uppercase tracking-widest">
              {t('datalake.col_size')}
            </TableHead>
            <TableHead className="font-bold text-[10px] uppercase tracking-widest">
              {t('datalake.col_modified')}
            </TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {files.map((f) => (
            <TableRow key={f.id} className="group border-border/20 hover:bg-accent/40 transition-colors">
              <TableCell className="font-medium text-sm max-w-xs truncate">
                {f.name}
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={badge.cls + ' text-[10px] font-bold'}>
                  {badge.label}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground font-mono">
                {formatBytes(f.size)}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatDate(f.modified)}
              </TableCell>
              <TableCell>
                {f.url && (
                  <a
                    href={f.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-primary"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
