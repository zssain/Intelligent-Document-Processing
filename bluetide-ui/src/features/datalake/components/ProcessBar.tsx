import { useDatalake } from '../context'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Play, X, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { jobsService, type ProcessRequest } from '@/features/documents/services/jobs.service'
import { useIngestionMode } from '@/features/documents/ingestion-mode-context'
import { useState, useCallback } from 'react'

interface ProcessBarProps {
  /** Called when a job is created, with the new job_id for tracking */
  onJobCreated?: (jobId: string) => void
}

export function ProcessBar({ onJobCreated }: ProcessBarProps) {
  const { t } = useTranslation()
  const { selectedFiles, clearSelection, activeSource } = useDatalake()
  const { activeMode } = useIngestionMode()

  const processMutation = useMutation({
    mutationFn: (req: ProcessRequest) => jobsService.processFiles(req),
    onSuccess: (data) => {
      clearSelection()
      onJobCreated?.(data.job_id)
    },
  })

  const handleProcess = useCallback(() => {
    if (selectedFiles.length === 0) return

    processMutation.mutate({
      source_type: activeSource,
      files: selectedFiles.map((f) => ({ id: f.id, name: f.name })),
    })
  }, [selectedFiles, activeSource, processMutation])

  if (selectedFiles.length === 0) return null

  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 rounded-xl border border-primary/30 bg-primary/5 animate-in slide-in-from-bottom-2 duration-200">
      {/* Left: selection count */}
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="font-mono text-xs">
          {selectedFiles.length}
        </Badge>
        <span className="text-sm text-muted-foreground">
          {selectedFiles.length === 1
            ? 'file selected'
            : 'files selected'}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={clearSelection}
          className="h-7 px-2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Right: process button */}
      <Button
        size="sm"
        onClick={handleProcess}
        disabled={processMutation.isPending}
        className="gap-1.5"
      >
        {processMutation.isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Play className="h-3.5 w-3.5" />
        )}
        {t('documents.jobs.process_selected', { count: selectedFiles.length })}
      </Button>
    </div>
  )
}
