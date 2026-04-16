import api from '@/shared/lib/api'

export interface UploadDocumentParams {
    file: File
    onUploadProgress?: (progressEvent: any) => void
}

export interface ProcessingConfig {
    enableOCR?: boolean
    handwritingRecognition?: boolean
    languageDetection?: boolean
    extractionModel?: string
    destinationCollection?: string
}

export interface StartProcessingParams {
    file: File
}

export const documentsService = {
    /**
     * Upload a single document
     * Hits: POST /upload
     */
    uploadDocument: async ({ file, onUploadProgress }: UploadDocumentParams) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress,
        })

        return response.data
    },

    /**
     * Ingest a document for RAG
     * Hits: POST /rag/ingest
     */
    ingestDocument: async (file: File, onUploadProgress?: (progressEvent: any) => void) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('rag/ingest', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress,
        })

        return response.data
    },

    /**
     * Start processing the uploaded documents (Restored for compatibility)
     * Note: Backend currently expects a file for analysis, so this is a bridge.
     */
    startProcessing: async ({ documentIds, config }: { documentIds: string[], config: any }) => {
        // Since backend analyze currently requires a file, we might need to 
        // adjust the flow. For now, we'll keep this as a no-op or placeholder
        // to prevent UI crashes, or map it to a list check.
        console.warn('startProcessing called with IDs:', documentIds, config);
        return { status: 'success', message: 'Processing started (mocked bridge)' };
    },

    /**
     * Analyze a financial document using Azure AI Content Understanding.
     * Hits: POST /cu/analyze
     */
    analyzeDocument: async ({ file }: { file: File }) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('cu/analyze', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })

        return response.data
    },

    /**
     * List all processed financial documents.
     * Hits: GET /cu/documents
     * @param sourceType - Optional source filter (s3, sharepoint, gdrive, local)
     */
    listDocuments: async (sourceType?: string) => {
        const params: Record<string, string> = {}
        if (sourceType) {
            params.source_type = sourceType
        }
        const response = await api.get('cu/documents', { params })
        return response.data
    },

    /**
     * Resolve preview/open URLs for a single document.
     * Hits: GET /cu/documents/{id}/preview
     */
    getDocumentPreview: async (id: string) => {
        const response = await api.get(`cu/documents/${id}/preview`)
        return response.data
    },

    /**
     * Delete a single document.
     * Hits: DELETE /cu/documents/{id}
     */
    deleteDocument: async (id: string) => {
        const response = await api.delete(`cu/documents/${id}`)
        return response.data
    },

    /**
     * Delete multiple documents in batch.
     * Hits: DELETE /cu/documents/batch
     */
    deleteDocumentsBatch: async (ids: string[]) => {
        const response = await api.delete('cu/documents/batch', {
            data: { document_ids: ids }
        })
        return response.data
    },

    /**
     * Get available extraction models (Mocked as not explicitly in backend yet)
     */
    getExtractionModels: async () => {
        return [
            { id: 'gpt-4o', name: 'GPT-4o Document Vision' },
            { id: 'claude-3-5', name: 'Claude 3.5 Sonnet' },
            { id: 'form-recognizer', name: 'Azure Form Recognizer' },
        ]
    },

    /**
     * Get available collections (Mocked)
     */
    getCollections: async () => {
        return [
            { id: 'fin-2024', name: 'Financial Statements 2024' },
            { id: 'legal-docs', name: 'Legal Agreements' },
            { id: 'hr-onboarding', name: 'HR Onboarding' },
        ]
    },
}
