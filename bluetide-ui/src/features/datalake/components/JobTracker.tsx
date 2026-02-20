import { useQuery, useQueryClient } from '@tanstack/react-query'
import { jobsService, type Job, type JobFileStatus } from '@/features/documents/services/jobs.service'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  X,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useTranslation } from 'react-i18next'

interface JobTrackerProps {
  jobId: string
  onDismiss: () => void
}

const FILE_STATUS_ICON: Record<JobFileStatus, JSX.Element> = {
  queued: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
  processing: <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />,
  completed: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
  failed: <XCircle className="h-3.5 w-3.5 text-destructive" />,
}

export function JobTracker({ jobId, onDismiss }: JobTrackerProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: job, isLoading } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => jobsService.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Stop polling once the job is terminal
      if (status === 'completed' || status === 'failed') return false
      return 3_000 // poll every 3s
    },
    staleTime: 1_000,
  })

  // Invalidate documents list when job completes
  const isTerminal = job?.status === 'completed' || job?.status === 'failed'
  if (isTerminal) {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
  }

  if (isLoading || !job) {
    return (
      <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-border/40 bg-card/30">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading job status…</span>
      </div>
    )
  }

  const pct =
    job.summary.total > 0
      ? Math.round(((job.summary.completed + job.summary.failed) / job.summary.total) * 100)
      : 0

  return (
    <div
      className={cn(
        'rounded-xl border px-4 py-4 space-y-3 transition-colors',
        isTerminal && job.summary.failed === 0
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : isTerminal && job.summary.failed > 0
            ? 'border-amber-500/30 bg-amber-500/5'
            : 'border-blue-500/30 bg-blue-500/5',
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {isTerminal ? (
            job.summary.failed === 0 ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <XCircle className="h-4 w-4 text-amber-500" />
            )
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
          )}
          <span className="font-semibold text-sm">
            {t('documents.jobs.tracker_title')}
          </span>
          <Badge
            variant="outline"
            className={cn(
              'text-[10px] font-bold uppercase',
              job.status === 'completed' && 'text-emerald-500 border-emerald-500/30',
              job.status === 'failed' && 'text-destructive border-destructive/30',
              job.status === 'running' && 'text-blue-400 border-blue-400/30',
              job.status === 'queued' && 'text-muted-foreground',
            )}
          >
            {t(`documents.jobs.status_${job.status}`)}
          </Badge>
        </div>

        {isTerminal && (
          <Button size="sm" variant="ghost" onClick={onDismiss} className="h-7 px-2">
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            job.summary.failed > 0 ? 'bg-amber-500' : 'bg-emerald-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Stats */}
      <p className="text-xs text-muted-foreground">
        {t('documents.jobs.progress', {
          completed: job.summary.completed + job.summary.failed,
          total: job.summary.total,
        })}
        {job.summary.failed > 0 && (
          <span className="text-destructive ml-1">
            ({job.summary.failed} failed)
          </span>
        )}
      </p>

      {/* Per-file status list (collapsed by default, show all when ≤10) */}
      {job.files.length <= 10 && (
        <div className="space-y-1 pt-1">
          {job.files.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-2 text-xs text-muted-foreground"
            >
              {FILE_STATUS_ICON[f.status]}
              <span className="truncate max-w-xs">{f.name}</span>
              {f.error && (
                <span className="text-destructive truncate max-w-[200px]">
                  — {f.error}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
