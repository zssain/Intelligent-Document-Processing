import { useRef } from 'react'
import { Upload, FileText, FileSpreadsheet, FileCode } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { useTranslation } from 'react-i18next'
import { cn } from '@/shared/lib/utils'

interface UploadDropzoneProps {
    onFilesSelected: (files: File[]) => void
}

export function UploadDropzone({ onFilesSelected }: UploadDropzoneProps) {
    const { t } = useTranslation()
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        const files = Array.from(e.dataTransfer.files)
        if (files.length > 0) {
            onFilesSelected(files)
        }
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            onFilesSelected(Array.from(e.target.files))
        }
    }

    return (
        <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className={cn(
                "relative group border-2 border-dashed border-border/60 rounded-2xl p-12 transition-all duration-200",
                "hover:border-primary/40 hover:bg-primary/5 cursor-pointer flex flex-col items-center justify-center text-center"
            )}
            onClick={() => fileInputRef.current?.click()}
        >
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                multiple
                className="hidden"
            />

            <div className="flex gap-4 mb-6">
                <div className="p-3 bg-muted rounded-lg group-hover:bg-primary/10 transition-colors">
                    <FileText className="w-6 h-6 text-muted-foreground group-hover:text-primary" />
                </div>
                <div className="p-3 bg-muted rounded-lg group-hover:bg-primary/10 transition-colors">
                    <FileSpreadsheet className="w-6 h-6 text-muted-foreground group-hover:text-primary" />
                </div>
                <div className="p-3 bg-muted rounded-lg group-hover:bg-primary/10 transition-colors">
                    <FileCode className="w-6 h-6 text-muted-foreground group-hover:text-primary" />
                </div>
            </div>

            <h3 className="text-xl font-semibold mb-2">{t('documents.upload.dropzone.title')}</h3>
            <p className="text-sm text-muted-foreground mb-8 max-w-xs">
                {t('documents.upload.dropzone.subtitle')}
            </p>

            <Button variant="default" size="lg" className="rounded-xl px-8 shadow-lg shadow-primary/20">
                <Upload className="w-4 h-4 me-2" />
                {t('documents.upload.dropzone.select_files')}
            </Button>
        </div>
    )
}
