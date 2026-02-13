import { Rocket, Loader2, FileUp } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { useTranslation } from 'react-i18next'
import { useDocumentUpload } from '../hooks/use-document-upload'
import { UploadHero } from './UploadHero'
import { UploadDropzone } from './UploadDropzone'
import { FileQueue } from './FileQueue'

export function DocumentUploadForm() {
    const { t } = useTranslation()
    const {
        queue,
        addFiles,
        removeFile,
        clearQueue,
        isProcessing,
        startProcessing,
    } = useDocumentUpload()

    const readyFilesCount = queue.filter(f => f.status !== 'duplicate').length
    const skippedFilesCount = queue.filter(f => f.status === 'duplicate').length

    return (
        <div className="relative pb-24">
            <UploadHero
                title={t('documents.upload.title')}
                subtitle={t('documents.upload.subtitle')}
                icon={FileUp}
            />

            <div className="max-w-4xl mx-auto space-y-12">
                <div>
                    <UploadDropzone onFilesSelected={addFiles} />
                    <FileQueue
                        files={queue}
                        onRemove={removeFile}
                        onClear={clearQueue}
                    />
                </div>
            </div>

            {/* Bottom Sticky Action Bar */}
            {queue.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 lg:left-24 bg-background/80 backdrop-blur-md border-t border-border/40 p-4 z-10 transition-all duration-300">
                    <div className="container max-w-7xl mx-auto flex items-center justify-between">
                        <div className="hidden sm:block">
                            <p className="text-xs text-muted-foreground font-medium">
                                {t('documents.upload.actions.ready', { count: readyFilesCount })}
                                {skippedFilesCount > 0 && <span> {t('documents.upload.actions.skipped', { count: skippedFilesCount })}</span>}
                            </p>
                        </div>

                        <div className="flex gap-4">
                            <Button variant="ghost" onClick={clearQueue} disabled={isProcessing}>
                                {t('common.actions.cancel')}
                            </Button>
                            <Button
                                size="lg"
                                className="rounded-xl px-12 shadow-xl shadow-primary/20"
                                onClick={() => startProcessing()}
                                disabled={isProcessing || readyFilesCount === 0}
                            >
                                {isProcessing ? (
                                    <Loader2 className="w-4 h-4 me-2 animate-spin" />
                                ) : (
                                    <Rocket className="w-4 h-4 me-2" />
                                )}
                                {t('documents.upload.actions.process')}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
