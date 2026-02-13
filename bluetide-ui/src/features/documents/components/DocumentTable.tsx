import * as React from 'react'
import { useState, useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import {
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    getFilteredRowModel,
    useReactTable,
} from '@tanstack/react-table'
import {
    FileText,
    FileImage,
    File,
    AlertCircle,
    Cloud,
    HardDrive,
    Loader2,
    Trash2,
    Sparkles,
    MoreHorizontal,
    Info,
} from 'lucide-react'
import { useDocuments } from '../context'
import { useChat } from '@/features/chat'
import { useTranslation } from 'react-i18next'
import type { Document as DocumentType } from '@/shared/types/document'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Checkbox } from '@/shared/components/ui/checkbox'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/shared/components/ui/table'
import { cn } from '../../../shared/lib/utils'

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatDate(date: Date): string {
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date)
}

function getDocumentIcon(type: DocumentType['type']) {
    switch (type) {
        case 'pdf':
            return <FileText className="h-5 w-5 text-rose-400" />
        case 'docx':
            return <FileText className="h-5 w-5 text-sky-400" />
        case 'image':
            return <FileImage className="h-5 w-5 text-emerald-400" />
        default:
            return <File className="h-5 w-5 text-slate-400" />
    }
}

const RowActions = ({ doc }: { doc: DocumentType }) => {
    const { setSelectedDocument, setIsPreviewOpen, deleteDocument, isDeleting } = useDocuments()
    const { startNewSessionWithContext } = useChat()
    const { t } = useTranslation()
    const navigate = useNavigate()
    const [isConfirming, setIsConfirming] = useState(false)

    return (
        <div className="flex justify-end pr-2">
            <DropdownMenu onOpenChange={(open) => !open && setIsConfirming(false)}>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0 hover:bg-muted">
                        <span className="sr-only">{t('documents.table.actions.open_menu')}</span>
                        <MoreHorizontal className="h-4 w-4" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                    <DropdownMenuLabel>{t('common.actions.actions')}</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                        onClick={() => {
                            setSelectedDocument(doc)
                            setIsPreviewOpen(true)
                        }}
                        className="gap-2"
                    >
                        <Info className="h-4 w-4" />
                        {t('common.actions.more_info')}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        onClick={() => {
                            startNewSessionWithContext([{ id: doc.id, name: doc.name }])
                            navigate({ to: '/chat' })
                        }}
                        className="gap-2 text-primary focus:text-primary focus:bg-primary/10"
                    >
                        <Sparkles className="h-4 w-4" />
                        {t('common.actions.ask_ai')}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {isConfirming ? (
                        <DropdownMenuItem
                            onClick={async () => {
                                try {
                                    await deleteDocument(doc.id)
                                    setIsConfirming(false)
                                } catch (error) {
                                    console.error('Failed to delete document:', error)
                                }
                            }}
                            disabled={isDeleting}
                            onSelect={(e) => e.preventDefault()}
                            className="gap-2 text-rose-500 font-bold focus:text-rose-600 focus:bg-rose-500/10 animate-in fade-in slide-in-from-right-1"
                        >
                            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertCircle className="h-4 w-4" />}
                            {isDeleting ? t('documents.table.actions.deleting') : t('documents.table.actions.are_you_sure')}
                        </DropdownMenuItem>
                    ) : (
                        <DropdownMenuItem
                            onSelect={(e) => {
                                e.preventDefault()
                                setIsConfirming(true)
                            }}
                            className="gap-2 text-rose-500 focus:text-rose-500 focus:bg-rose-500/10"
                        >
                            <Trash2 className="h-4 w-4" />
                            {t('common.actions.delete')}
                        </DropdownMenuItem>
                    )}
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    )
}

export function DocumentTable() {
    const { documents, isLoading, pagination, setPagination, deleteDocumentsBatch, isDeleting } = useDocuments()
    const { startNewSessionWithContext } = useChat()
    const { t } = useTranslation()
    const navigate = useNavigate()

    const columns = React.useMemo<ColumnDef<DocumentType>[]>(() => [
        {
            id: 'selection',
            header: ({ table }) => (
                <div className="px-1">
                    <Checkbox
                        checked={table.getIsAllPageRowsSelected()}
                        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
                        aria-label="Select all"
                    />
                </div>
            ),
            cell: ({ row }) => (
                <div className="px-1">
                    <Checkbox
                        checked={row.getIsSelected()}
                        onCheckedChange={(value) => row.toggleSelected(!!value)}
                        aria-label="Select row"
                    />
                </div>
            ),
            enableSorting: false,
            enableHiding: false,
        },
        {
            accessorKey: 'name',
            header: t('documents.table.cols.name'),
            cell: ({ row }) => {
                const doc = row.original
                const { setSelectedDocument, setIsPreviewOpen } = useDocuments()

                const handleOpenPreview = () => {
                    setSelectedDocument(doc)
                    setIsPreviewOpen(true)
                }

                return (
                    <div
                        className="flex items-center gap-3 group cursor-pointer"
                        onClick={handleOpenPreview}
                    >
                        <div className="transition-transform group-hover:scale-110">
                            {doc.currentStage === 'failed' ? (
                                <AlertCircle className="h-5 w-5 text-rose-400/80" />
                            ) : (
                                getDocumentIcon(doc.type)
                            )}
                        </div>
                        <div>
                            <p className="font-medium text-foreground group-hover:text-primary transition-colors">
                                {doc.name}
                            </p>
                            <p className="text-[11px] text-muted-foreground">{doc.fileSizeMb || formatBytes(doc.size)}</p>
                        </div>
                    </div>
                )
            },
        },
        {
            accessorKey: 'source',
            header: t('documents.table.cols.source'),
            cell: ({ row }) => {
                const source = row.original.source
                const isSharePoint = source === 'sharepoint' || source === 'onedrive'
                const isS3 = source === 's3'
                const isGDrive = source === 'gdrive'

                const colorClass = isSharePoint ? 'bg-sky-500/10 text-sky-400'
                    : isS3 ? 'bg-amber-500/10 text-amber-400'
                    : isGDrive ? 'bg-violet-500/10 text-violet-400'
                    : 'bg-emerald-500/10 text-emerald-400'

                const label = isSharePoint ? 'SharePoint'
                    : isS3 ? 'S3'
                    : isGDrive ? 'GDrive'
                    : 'LOCAL'

                return (
                    <Badge
                        variant="outline"
                        className={cn(
                            'gap-1.5 border-0 font-medium uppercase tracking-wider text-[10px] px-2 py-0.5',
                            colorClass
                        )}
                    >
                        {isSharePoint ? (
                            <Cloud className="h-3 w-3" />
                        ) : (
                            <HardDrive className="h-3 w-3" />
                        )}
                        {label}
                    </Badge>
                )
            },
        },
        {
            accessorKey: 'currentStage',
            header: t('documents.table.cols.stage'),
            cell: ({ row }) => {
                const stage = row.original.currentStage
                const stageColors: Record<string, string> = {
                    parsed: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
                    ocr_extraction: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
                    generating_embeddings: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
                    completed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
                    failed: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                }
                const stageLabels: Record<string, string> = {
                    parsed: t('documents.table.stages.parsed'),
                    ocr_extraction: t('documents.table.stages.ocr_extraction'),
                    generating_embeddings: t('documents.table.stages.generating_embeddings'),
                    completed: t('documents.table.stages.completed'),
                    failed: t('documents.table.stages.failed'),
                }
                return (
                    <Badge variant="outline" className={cn('font-medium border-0 px-2 py-0.5', stageColors[stage])}>
                        {stageLabels[stage]}
                    </Badge>
                )
            },
        },
        {
            accessorKey: 'confidenceStatus',
            header: t('documents.table.cols.confidence'),
            cell: ({ row }) => {
                const doc = row.original
                const status = doc.confidenceStatus
                if (status === 'running') {
                    return (
                        <div className="flex items-center gap-2 text-sky-400 text-xs animate-pulse">
                            <div className="h-1.5 w-1.5 rounded-full bg-current" />
                            {t('documents.table.stages.running')}
                        </div>
                    )
                }
                if (status === 'chunking') {
                    return <span className="text-slate-500 text-xs">{t('documents.table.stages.chunking')}</span>
                }
                const percentage = doc.confidencePercentage ?? 0
                const color =
                    percentage >= 90
                        ? 'text-emerald-400/90'
                        : percentage >= 70
                            ? 'text-amber-400/90'
                            : 'text-rose-400/90'
                return <span className={cn('font-mono font-medium', color)}>{percentage}%</span>
            },
        },
        {
            accessorKey: 'uploadedAt',
            header: t('documents.table.cols.timestamp'),
            cell: ({ row }) => {
                const doc = row.original
                return (
                    <div className="text-sm">
                        <p className="font-medium text-foreground/90">{formatDate(doc.uploadedAt)}</p>
                        <p className="text-[11px] text-muted-foreground/70 tracking-tight">
                            Modified: {formatDate(doc.lastModifiedAt)}
                        </p>
                    </div>
                )
            },
        },
        {
            accessorKey: 'language',
            header: t('documents.table.cols.language'),
            cell: ({ row }) => {
                const lang = row.original.language
                return (
                    <span className="font-medium text-muted-foreground capitalize">
                        {lang === 'arabic' ? 'عربي' : 'English'}
                    </span>
                )
            },
        },
        {
            accessorKey: 'category',
            header: t('documents.table.cols.category'),
            cell: ({ row }) => {
                const category = row.original.category
                const labels: Record<string, string> = {
                    invoice: t('documents.table.categories.invoice'),
                    equipment_document: t('documents.table.categories.equipment_document'),
                    user_manual: t('documents.table.categories.user_manual'),
                    finance: t('documents.table.categories.finance'),
                    other: t('documents.table.categories.other'),
                }
                return (
                    <Badge variant="secondary" className="bg-secondary/50 font-medium text-muted-foreground">
                        {labels[category]}
                    </Badge>
                )
            },
        },
        {
            accessorKey: 'fingerprint',
            header: t('documents.table.cols.identification'),
            cell: ({ row }) => {
                const doc = row.original
                return (
                    <div className="space-y-1.5 pe-4">
                        <div className="flex items-center gap-2">
                            <code className="rounded bg-muted px-2 py-0.5 text-[10px] font-mono font-bold tracking-tight text-foreground/80 shadow-sm ring-1 ring-border/50">
                                {doc.fingerprint}
                            </code>
                        </div>
                        <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/60">
                            UID-{doc.uid.slice(0, 8)}
                        </p>
                    </div>
                )
            },
        },
        {
            id: 'actions',
            cell: ({ row }) => <RowActions doc={row.original} />,
        },
    ], [t])

    const [rowSelection, setRowSelection] = useState({})
    const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
    const [countdown, setCountdown] = useState(0)

    useEffect(() => {
        let timer: NodeJS.Timeout
        if (isConfirmingDelete && countdown > 0) {
            timer = setTimeout(() => setCountdown(countdown - 1), 1000)
        }
        return () => clearTimeout(timer)
    }, [isConfirmingDelete, countdown])

    const startDeleteConfirmation = () => {
        setIsConfirmingDelete(true)
        setCountdown(3)
    }

    const cancelDelete = () => {
        setIsConfirmingDelete(false)
        setCountdown(0)
    }

    const table = useReactTable({
        data: documents,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        state: {
            pagination,
            rowSelection,
        },
        onRowSelectionChange: setRowSelection,
        onPaginationChange: (updater) => {
            const newPagination =
                typeof updater === 'function' ? updater(pagination) : updater
            setPagination(newPagination)
        },
    })

    const pageCount = table.getPageCount()
    const { pageIndex, pageSize } = pagination
    const totalRows = documents.length
    const startRow = pageIndex * pageSize + 1
    const endRow = Math.min((pageIndex + 1) * pageSize, totalRows)

    const selectedRows = table.getSelectedRowModel().rows
    const hasSelection = selectedRows.length > 0

    return (
        <div className="space-y-4">
            {/* Bulk Actions Toolbar */}
            <div className={cn(
                "flex items-center gap-3 py-2 px-4 rounded-lg transition-all duration-300 z-50 relative",
                hasSelection ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2 pointer-events-none h-0 py-0 overflow-hidden",
                isConfirmingDelete ? "bg-rose-500/10 border border-rose-500/20" : "bg-primary/5 border border-primary/10"
            )}>
                {isConfirmingDelete ? (
                    <>
                        <span className="text-sm font-bold text-rose-500 ps-1 animate-pulse">
                            {t('documents.table.actions.are_you_sure_countdown', { seconds: countdown })}
                        </span>
                        <div className="h-4 w-px bg-rose-500/20 mx-2" />
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={countdown > 0 || isDeleting}
                            className={cn(
                                "h-8 gap-2 font-bold transition-all",
                                (countdown > 0 || isDeleting) ? "text-muted-foreground" : "text-rose-500 hover:text-rose-600 hover:bg-rose-500/20 scale-105 shadow-sm"
                            )}
                            onClick={async () => {
                                try {
                                    const ids = selectedRows.map(r => r.original.id)
                                    await deleteDocumentsBatch(ids)
                                    table.resetRowSelection()
                                    setIsConfirmingDelete(false)
                                } catch (error: any) {
                                    console.error('Failed to delete documents:', error)
                                }
                            }}
                        >
                            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                            {isDeleting ? t('documents.table.actions.deleting') : countdown > 0 ? t('documents.table.actions.wait_s', { seconds: countdown }) : t('documents.table.actions.delete_now')}
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-muted-foreground hover:text-foreground"
                            onClick={cancelDelete}
                        >
                            {t('common.actions.cancel')}
                        </Button>
                    </>
                ) : (
                    <>
                        <span className="text-sm font-medium text-primary ps-1">
                            {selectedRows.length} {t('documents.table.actions.selected')}
                        </span>
                        <div className="h-4 w-px bg-primary/20 mx-2" />
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 gap-2 text-rose-500 hover:text-rose-600 hover:bg-rose-500/10 font-semibold"
                            onClick={startDeleteConfirmation}
                        >
                            <Trash2 className="h-4 w-4" />
                            {t('documents.table.actions.delete_selected')}
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 gap-2 text-primary hover:bg-primary/10 font-semibold"
                            onClick={() => {
                                const selectedDocs = selectedRows.map(r => ({
                                    id: r.original.id,
                                    name: r.original.name
                                }))
                                startNewSessionWithContext(selectedDocs)
                                table.resetRowSelection()
                                navigate({ to: '/chat' })
                            }}
                        >
                            <Sparkles className="h-4 w-4" />
                            {t('common.actions.ask_ai')}
                        </Button>
                        <div className="ml-auto">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 text-muted-foreground hover:text-foreground"
                                onClick={() => table.resetRowSelection()}
                            >
                                {t('common.actions.cancel')}
                            </Button>
                        </div>
                    </>
                )}
            </div>

            <div className="rounded-lg border bg-card/50">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id} className="border-border hover:bg-transparent">
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id} className="text-muted-foreground font-semibold px-4 h-12">
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    <div className="flex flex-col items-center gap-2 text-muted-foreground animate-pulse">
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                        <span>{t('documents.library.loading_documents')}</span>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ) : table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow
                                    key={row.id}
                                    className={cn(
                                        'border-border hover:bg-muted/50 transition-colors',
                                        row.original.currentStage === 'failed' && 'bg-destructive/5 hover:bg-destructive/10'
                                    )}
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center text-slate-500"
                                >
                                    {t('documents.library.no_documents')}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-2">
                <div className="text-sm text-slate-500">
                    {t('documents.library.showing_docs', { startRow, endRow, totalRows })}
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => table.previousPage()}
                        disabled={!table.getCanPreviousPage()}
                        className="h-8 transition-all hover:bg-accent"
                    >
                        {t('common.actions.save') === 'Save' ? 'Previous' : 'السابق'}
                    </Button>
                    <div className="flex items-center justify-center min-w-[100px] text-sm font-medium">
                        {t('documents.library.page_of', { page: pageIndex + 1, total: pageCount })}
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => table.nextPage()}
                        disabled={!table.getCanNextPage()}
                        className="h-8 transition-all hover:bg-accent"
                    >
                        {t('common.actions.save') === 'Save' ? 'Next' : 'التالي'}
                    </Button>
                </div>
            </div>
        </div>
    )
}
