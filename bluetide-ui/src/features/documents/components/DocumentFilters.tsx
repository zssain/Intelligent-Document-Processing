import {
    Settings2,
} from 'lucide-react'
import { useDocuments } from '../context'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/shared/components/ui/popover'
import { cn } from '../../../shared/lib/utils'

export function DocumentFilters() {
    const { filters, setFilters, resetFilters } = useDocuments()
    const { t } = useTranslation()

    const sourceOptions = [
        { value: 'local', label: t('documents.library.loading_documents') === 'Loading your secure documents...' ? 'Local' : 'محلي' },
        { value: 's3', label: 'S3' },
        { value: 'sharepoint', label: 'SharePoint' },
        { value: 'gdrive', label: 'Google Drive' },
    ]

    const stageOptions = [
        { value: 'parsed', label: t('documents.table.stages.parsed') },
        { value: 'ocr_extraction', label: t('documents.table.stages.ocr_extraction') },
        { value: 'generating_embeddings', label: t('documents.table.stages.generating_embeddings') },
        { value: 'completed', label: t('documents.table.stages.completed') },
        { value: 'failed', label: t('documents.table.stages.failed') },
    ]

    const languageOptions = [
        { value: 'english', label: 'English' },
        { value: 'arabic', label: 'Arabic' },
    ]

    const categoryOptions = [
        { value: 'invoice', label: t('documents.table.categories.invoice') },
        { value: 'equipment_document', label: t('documents.table.categories.equipment_document') },
        { value: 'user_manual', label: t('documents.table.categories.user_manual') },
        { value: 'finance', label: t('documents.table.categories.finance') },
        { value: 'other', label: t('documents.table.categories.other') },
    ]

    const activeFiltersCount = Object.values(filters).filter(Boolean).length

    const toggleFilter = (key: keyof typeof filters, value: string) => {
        const newFilters = { ...filters }
        if (newFilters[key] === value) {
            delete newFilters[key]
        } else {
            newFilters[key] = value
        }
        setFilters(newFilters)
    }

    const filterGroups = [
        { key: 'source', label: t('documents.table.cols.source'), options: sourceOptions },
        { key: 'stage', label: t('documents.table.cols.stage'), options: stageOptions },
        { key: 'language', label: t('documents.table.cols.language'), options: languageOptions },
        { key: 'category', label: t('documents.table.cols.category'), options: categoryOptions },
    ] as const

    return (
        <div className="flex flex-wrap items-center gap-3">
            <Popover>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        className="h-10 gap-2 border-2 rounded-l-none hover:border-primary/50 hover:bg-primary/5 transition-all text-muted-foreground hover:text-foreground bg-background/50"
                    >
                        <Settings2 className="h-4 w-4" />
                        {t('documents.filters.title')}
                        {activeFiltersCount > 0 && (
                            <Badge
                                variant="secondary"
                                className="ml-1 px-1.5 py-0 text-[10px] bg-primary text-primary-foreground"
                            >
                                {activeFiltersCount}
                            </Badge>
                        )}
                    </Button>
                </PopoverTrigger>
                <PopoverContent
                    className="w-[400px] bg-popover p-4"
                    align="start"
                >
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h4 className="font-medium">{t('documents.filters.popover_title')}</h4>
                            {activeFiltersCount > 0 && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={resetFilters}
                                    className="h-8 px-2 text-xs text-primary hover:bg-primary/10"
                                >
                                    {t('documents.filters.reset_all')}
                                </Button>
                            )}
                        </div>

                        <div className="space-y-5">
                            {filterGroups.map((group) => (
                                <div key={group.key} className="space-y-2">
                                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                        {group.label}
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {group.options.map((opt) => {
                                            const isActive = filters[group.key] === opt.value
                                            return (
                                                <button
                                                    key={opt.value}
                                                    onClick={() => toggleFilter(group.key, opt.value)}
                                                    className={cn(
                                                        'rounded-md px-3 py-1 text-sm transition-colors',
                                                        isActive
                                                            ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20'
                                                            : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                                    )}
                                                >
                                                    {opt.label}
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </PopoverContent>
            </Popover>

        </div>
    )
}
