import { createContext, useContext, useState, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { Document as DocumentType, DocumentSource } from '@/shared/types/document'
import { documentsService } from './services/documents.service'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useIngestionMode } from './ingestion-mode-context'

interface DocumentFilters {
    source?: string
    stage?: string
    language?: string
    category?: string
    search?: string
}

interface DocumentContextValue {
    documents: DocumentType[]
    isLoading: boolean
    filters: DocumentFilters
    setFilters: (filters: DocumentFilters) => void
    resetFilters: () => void
    pagination: {
        pageIndex: number
        pageSize: number
    }
    setPagination: (pagination: { pageIndex: number; pageSize: number }) => void
    selectedDocument: DocumentType | null
    setSelectedDocument: (doc: DocumentType | null) => void
    isPreviewOpen: boolean
    setIsPreviewOpen: (open: boolean) => void
    deleteDocument: (id: string) => Promise<void>
    deleteDocumentsBatch: (ids: string[]) => Promise<void>
    isDeleting: boolean
}

const DocumentContext = createContext<DocumentContextValue | null>(null)

export function useDocuments() {
    const context = useContext(DocumentContext)
    if (!context) {
        throw new Error('useDocuments must be used within a DocumentProvider')
    }
    return context
}

interface DocumentProviderProps {
    children: ReactNode
}

export function DocumentProvider({ children }: DocumentProviderProps) {
    const { activeMode, isConnectorMode } = useIngestionMode()

    // Map ingestion mode to the source_type query param the backend expects
    const sourceType = isConnectorMode ? activeMode : 'local'

    const { data: backendData, isLoading } = useQuery({
        queryKey: ['documents', sourceType],
        queryFn: () => documentsService.listDocuments(sourceType),
    })

    const [filters, setFilters] = useState<DocumentFilters>({})
    const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 })
    const [selectedDocument, setSelectedDocument] = useState<DocumentType | null>(null)
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)
    const queryClient = useQueryClient()

    const deleteMutation = useMutation({
        mutationFn: (id: string) => documentsService.deleteDocument(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] })
        }
    })

    const bulkDeleteMutation = useMutation({
        mutationFn: (ids: string[]) => documentsService.deleteDocumentsBatch(ids),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] })
        }
    })

    const deleteDocument = async (id: string) => {
        await deleteMutation.mutateAsync(id)
    }

    const deleteDocumentsBatch = async (ids: string[]) => {
        await bulkDeleteMutation.mutateAsync(ids)
    }

    const documents = useMemo(() => {
        if (!backendData?.documents) return []

        /** Normalise the raw source string from the backend into a clean DocumentSource. */
        function normaliseSource(raw: string | undefined | null): DocumentSource {
            if (!raw) return 'local'
            const lower = raw.toLowerCase()
            if (lower.startsWith('s3:')) return 's3'
            if (lower.startsWith('sharepoint:')) return 'sharepoint'
            if (lower.startsWith('gdrive:') || lower.startsWith('google')) return 'gdrive'
            if (lower === 's3') return 's3'
            if (lower === 'sharepoint' || lower === 'onedrive') return 'sharepoint'
            if (lower === 'gdrive') return 'gdrive'
            return 'local'
        }

        /** Normalise the raw document_type string into a clean DocumentCategory. */
        function normaliseCategory(raw: string | undefined | null): string {
            if (!raw) return 'other'
            const lower = raw.toLowerCase().trim()
            // Exact matches
            if (lower === 'invoice') return 'invoice'
            if (lower === 'finance' || lower === 'financial statement' || lower === 'financial report') return 'finance'
            if (lower === 'equipment_document' || lower === 'equipment document') return 'equipment_document'
            if (lower === 'user_manual' || lower === 'user manual' || lower === 'manual') return 'user_manual'
            if (lower === 'contract' || lower === 'agreement') return 'other'
            if (lower === 'document') return 'other'
            // Partial matches
            if (lower.includes('invoice') || lower.includes('tax')) return 'invoice'
            if (lower.includes('financial') || lower.includes('statement') || lower.includes('report')) return 'finance'
            if (lower.includes('equipment') || lower.includes('machine')) return 'equipment_document'
            if (lower.includes('manual') || lower.includes('guide')) return 'user_manual'
            return 'other'
        }

        let filtered = backendData.documents.map((doc: any): DocumentType => ({
            id: doc.id,
            name: doc.filename || 'Untitled Document',
            size: doc.file_size_bytes || 0,
            type: (doc.filename?.split('.').pop() as any) || 'other',
            source: normaliseSource(doc.source),
            currentStage: 'completed',
            confidenceStatus: 'completed',
            confidencePercentage: doc.confidence_percentage ?? 0,
            uploadedAt: new Date(doc.processed_at),
            lastModifiedAt: new Date(doc.processed_at),
            language: (doc.document_language || 'English').toLowerCase() as any,
            category: normaliseCategory(doc.document_type) as any,
            fingerprint: doc.id.slice(0, 8),
            uid: doc.id,
            s3Url: doc.s3_url,
            fileSizeMb: doc.file_size_mb,
            classificationLevel: doc.classification_level ?? 0,
            categoryIds: doc.category_ids ?? [],
            deletedAt: null,
            createdByUid: '',
        }))

        // Source filtering is now handled server-side via source_type query param.
        // Only client-side text/field filters remain below.

        // Apply Search
        if (filters.search) {
            const searchLower = filters.search.toLowerCase()
            filtered = filtered.filter((doc: DocumentType) =>
                doc.name.toLowerCase().includes(searchLower) ||
                doc.uid.toLowerCase().includes(searchLower) ||
                doc.category.toLowerCase().includes(searchLower)
            )
        }

        // Apply Filters
        if (filters.source) {
            filtered = filtered.filter((doc: DocumentType) => doc.source === filters.source)
        }
        if (filters.stage) {
            filtered = filtered.filter((doc: DocumentType) => doc.currentStage === filters.stage)
        }
        if (filters.language) {
            filtered = filtered.filter((doc: DocumentType) => doc.language === filters.language)
        }
        if (filters.category) {
            filtered = filtered.filter((doc: DocumentType) => doc.category === filters.category)
        }

        return filtered
    }, [backendData, filters])

    const resetFilters = () => setFilters({})

    return (
        <DocumentContext.Provider
            value={{
                documents,
                isLoading,
                filters,
                setFilters,
                resetFilters,
                pagination,
                setPagination,
                selectedDocument,
                setSelectedDocument,
                isPreviewOpen,
                setIsPreviewOpen,
                deleteDocument,
                deleteDocumentsBatch,
                isDeleting: deleteMutation.isPending || bulkDeleteMutation.isPending,
            }}
        >
            {children}
        </DocumentContext.Provider>
    )
}
