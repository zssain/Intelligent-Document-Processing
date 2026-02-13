import { X } from 'lucide-react'
import { useDocuments } from '../context'
import { Badge } from '@/shared/components/ui/badge'

const sourceOptions = [
    { value: 'local', label: 'Local' },
    { value: 's3', label: 'S3' },
    { value: 'sharepoint', label: 'SharePoint' },
    { value: 'gdrive', label: 'Google Drive' },
]

const stageOptions = [
    { value: 'parsed', label: 'Parsed' },
    { value: 'ocr_extraction', label: 'OCR Extraction' },
    { value: 'generating_embeddings', label: 'Generating Embeddings' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
]

const languageOptions = [
    { value: 'english', label: 'English' },
    { value: 'arabic', label: 'Arabic' },
]

const categoryOptions = [
    { value: 'invoice', label: 'Invoice' },
    { value: 'equipment_document', label: 'Equipment' },
    { value: 'user_manual', label: 'Manual' },
    { value: 'finance', label: 'Finance' },
    { value: 'other', label: 'Other' },
]

const filterGroups = [
    { key: 'source', label: 'Source', options: sourceOptions },
    { key: 'stage', label: 'Stage', options: stageOptions },
    { key: 'language', label: 'Language', options: languageOptions },
    { key: 'category', label: 'Category', options: categoryOptions },
] as const

export function DocumentActiveFilters() {
    const { filters, setFilters } = useDocuments()

    const toggleFilter = (key: keyof typeof filters, value: string) => {
        const newFilters = { ...filters }
        if (newFilters[key] === value) {
            delete newFilters[key]
        } else {
            newFilters[key] = value
        }
        setFilters(newFilters)
    }

    const activeFilters = Object.entries(filters).filter(([key, value]) => value && key !== 'search')

    if (activeFilters.length === 0) return null

    return (
        <div className="flex flex-wrap items-center gap-2 pt-2 px-1">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mr-1">
                Active Filters:
            </span>
            {activeFilters.map(([key, value]) => {
                if (!value) return null
                const group = filterGroups.find((g) => g.key === key)
                const option = group?.options.find((o) => o.value === value)
                return (
                    <Badge
                        key={key}
                        variant="secondary"
                        className="gap-1 border border-border/50 bg-secondary/50 hover:bg-secondary/80 text-foreground px-2 py-1 text-[11px] font-medium transition-colors"
                    >
                        <span className="text-muted-foreground capitalize">{key}:</span>
                        {option?.label}
                        <button
                            onClick={() => toggleFilter(key as any, value)}
                            className="ml-1 rounded-full hover:bg-primary/20 p-0.5 transition-colors"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </Badge>
                )
            })}
        </div>
    )
}
