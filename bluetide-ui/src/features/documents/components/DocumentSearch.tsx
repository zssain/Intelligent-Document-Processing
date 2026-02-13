import { Search, X } from 'lucide-react'
import { useDocuments } from '../context'
import { useTranslation } from 'react-i18next'
import { Input } from '@/shared/components/ui/input'
import { Button } from '@/shared/components/ui/button'
import { useEffect, useState } from 'react'
import { useDebounce } from '@/shared/hooks/use-debounce'

export function DocumentSearch() {
    const { t } = useTranslation()
    const { filters, setFilters } = useDocuments()
    const [searchValue, setSearchValue] = useState(filters.search || '')
    const debouncedSearch = useDebounce(searchValue, 300)

    useEffect(() => {
        setFilters({ ...filters, search: debouncedSearch })
    }, [debouncedSearch])

    const handleClear = () => {
        setSearchValue('')
    }

    return (
        <div className="relative flex-1 group">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
                placeholder={t('documents.library.search_placeholder')}
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                className="pl-9 pr-9 h-10 border-2 rounded-r-none border-r-0 focus-visible:ring-primary/20 transition-all bg-background/50"
            />
            {searchValue && (
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleClear}
                    className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 hover:bg-transparent text-muted-foreground hover:text-foreground"
                >
                    <X className="h-4 w-4" />
                </Button>
            )}
        </div>
    )
}
