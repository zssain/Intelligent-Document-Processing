import { X, FileText, FileSpreadsheet, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Progress } from '@/shared/components/ui/progress'
import { cn } from '@/shared/lib/utils'
import { useTranslation } from 'react-i18next'
import type { QueuedFile } from '../hooks/use-document-upload'

interface FileQueueProps {
    files: QueuedFile[]
    onRemove: (id: string) => void
    onClear: () => void
}

export function FileQueue({ files, onRemove, onClear }: FileQueueProps) {
    const { t } = useTranslation()
    if (files.length === 0) return null

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

    const getFileIcon = (file: File) => {
        if (file.name.endsWith('.xlsx')) return <FileSpreadsheet className="w-5 h-5 text-emerald-500" />
        return <FileText className="w-5 h-5 text-blue-500" />
    }

    return (
        <div className="mt-12 space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                    {t('documents.upload.queue.title', { count: files.length })}
                </h3>
                <Button variant="ghost" size="sm" onClick={onClear} className="text-xs hover:text-destructive">
                    {t('documents.upload.queue.clear_all')}
                </Button>
            </div>

            <div className="space-y-3">
                {files.map((file) => (
                    <div
                        key={file.id}
                        className={cn(
                            "group flex items-center gap-4 p-4 rounded-xl border border-border/40 bg-card/30 transition-all duration-200",
                            file.status === 'duplicate' && "border-amber-500/20 bg-amber-500/5"
                        )}
                    >
                        <div className="p-2 bg-background/50 rounded-lg">
                            {getFileIcon(file.file)}
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-medium truncate">{file.file.name}</span>
                                <span className="text-[10px] text-muted-foreground shrink-0 uppercase">
                                    {formatSize(file.file.size)} • {file.file.name.split('.').pop()?.toUpperCase()}
                                </span>
                            </div>

                            {file.status === 'uploading' && (
                                <div className="mt-2 flex items-center gap-3">
                                    <Progress value={file.progress} className="h-1 flex-1" />
                                    <span className="text-[10px] font-mono text-muted-foreground">{file.progress}%</span>
                                </div>
                            )}

                            {file.status === 'duplicate' && (
                                <div className="mt-1 flex items-center gap-1.5 text-amber-500">
                                    <CheckCircle2 className="w-3 h-3" />
                                    <span className="text-xs font-semibold">{t('documents.upload.queue.duplicate')}</span>
                                </div>
                            )}

                            {file.status === 'completed' && (
                                <div className="mt-1 flex items-center gap-1.5 text-emerald-500">
                                    <CheckCircle2 className="w-3 h-3" />
                                    <span className="text-xs font-semibold">{t('documents.upload.queue.success')}</span>
                                </div>
                            )}

                            {file.status === 'error' && (
                                <div className="mt-1 flex items-center gap-1.5 text-destructive">
                                    <AlertCircle className="w-3 h-3" />
                                    <span className="text-xs font-semibold">{file.error || t('documents.upload.queue.failed')}</span>
                                </div>
                            )}
                        </div>

                        <div className="flex items-center gap-4">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full hover:bg-destructive/10 hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={() => onRemove(file.id)}
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
