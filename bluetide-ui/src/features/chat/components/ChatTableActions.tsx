import { useState } from 'react'
import { FileSpreadsheet, Copy, Check } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { exportTableToXLSX, copyTableToClipboard } from '@/shared/lib/table-utils'
import { cn } from '@/shared/lib/utils'

interface ChatTableActionsProps {
    tableRef: React.RefObject<HTMLTableElement | null>
}

export function ChatTableActions({ tableRef }: ChatTableActionsProps) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        if (!tableRef.current) return
        const success = await copyTableToClipboard(tableRef.current)
        if (success) {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    const handleExport = () => {
        if (!tableRef.current) return
        // Generate a filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        exportTableToXLSX(tableRef.current, `analysis_table_${timestamp}.xlsx`)
    }

    return (
        <div className="flex items-center gap-2 mt-2 animate-in fade-in slide-in-from-top-1 duration-300">
            <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className={cn(
                    "h-7 px-2 text-[10px] font-bold uppercase tracking-wider gap-1.5 transition-all",
                    copied ? "text-emerald-500 bg-emerald-500/10" : "text-muted-foreground hover:text-primary hover:bg-primary/5"
                )}
            >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? 'Copied' : 'Copy'}
            </Button>

            <Button
                variant="ghost"
                size="sm"
                onClick={handleExport}
                className="h-7 px-2 text-[10px] font-bold uppercase tracking-wider gap-1.5 text-muted-foreground hover:text-primary hover:bg-primary/5 transition-all"
            >
                <FileSpreadsheet className="h-3 w-3" />
                Export XLSX
            </Button>
        </div>
    )
}
