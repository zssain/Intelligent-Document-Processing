import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsService } from '../services/documents.service'


export interface QueuedFile {
    id: string
    file: File
    status: 'pending' | 'uploading' | 'uploaded' | 'completed' | 'error' | 'duplicate'
    progress: number
    error?: string
}

export function useDocumentUpload() {
    const queryClient = useQueryClient()
    const [queue, setQueue] = useState<QueuedFile[]>([])

    // Upload mutation
    const uploadMutation = useMutation({
        mutationFn: (queuedFile: QueuedFile) =>
            documentsService.uploadDocument({
                file: queuedFile.file,
                onUploadProgress: (progressEvent) => {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                    updateFileStatus(queuedFile.id, { progress })
                },
            }),
        onSuccess: (_: any, queuedFile: QueuedFile) => {
            updateFileStatus(queuedFile.id, { status: 'uploaded', progress: 100 })
        },
        onError: (error: any, queuedFile: QueuedFile) => {
            updateFileStatus(queuedFile.id, {
                status: 'error',
                error: error.message || 'Upload failed',
            })
        },
    })

    // Start processing (Ingestion into RAG) mutation
    const processMutation = useMutation({
        mutationFn: async () => {
            const filesToProcess = queue.filter(
                (f: QueuedFile) => (f.status === 'uploaded' || f.status === 'pending')
            )

            const results = []
            for (const queuedFile of filesToProcess) {
                try {
                    updateFileStatus(queuedFile.id, { status: 'uploading', progress: 0 }) // Re-use status for processing feedback
                    const result = await documentsService.ingestDocument(queuedFile.file, (progressEvent) => {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        updateFileStatus(queuedFile.id, { progress })
                    })
                    updateFileStatus(queuedFile.id, { status: 'completed', progress: 100 })
                    results.push(result)
                } catch (error: any) {
                    updateFileStatus(queuedFile.id, {
                        status: 'error',
                        error: error.message || 'Processing failed'
                    })
                    throw error
                }
            }
            return results
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] })
        },
    })

    const updateFileStatus = useCallback((id: string, updates: Partial<QueuedFile>) => {
        setQueue((prev: QueuedFile[]) => prev.map((f: QueuedFile) => (f.id === id ? { ...f, ...updates } : f)))
    }, [])

    const addFiles = useCallback((files: File[]) => {
        const newFiles = files.map((file) => ({
            id: crypto.randomUUID(),
            file,
            status: 'pending' as const,
            progress: 0,
        }))
        setQueue((prev: QueuedFile[]) => [...prev, ...newFiles])
    }, [])

    const removeFile = useCallback((id: string) => {
        setQueue((prev: QueuedFile[]) => prev.filter((f: QueuedFile) => f.id !== id))
    }, [])

    const clearQueue = useCallback(() => {
        setQueue([])
    }, [])

    return {
        queue,
        addFiles,
        removeFile,
        clearQueue,
        updateFileStatus,
        isUploading: uploadMutation.isPending,
        isProcessing: processMutation.isPending,
        startProcessing: processMutation.mutate,
        uploadFile: uploadMutation.mutate,
    }
}
