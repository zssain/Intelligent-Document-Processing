import api from '@/shared/lib/api'
import { auth } from '@/shared/lib/firebase'

export interface QueryRequest {
    question: string
    entity?: string
    document_type?: string
    document_ids?: string[]
    language?: 'english' | 'arabic'
}

export interface QueryResponse {
    answer: string
    sources: Array<{
        id: string
        name: string
        content_snippet: string
        confidence: number
    }>
}

export interface IngestResponse {
    status: string
    document_id: string
    chunks_count: number
}

export const chatService = {
    /**
     * Ingest a document for RAG
     * Hits: POST /rag/ingest
     */
    ingestDocument: async (file: File) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('rag/ingest', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })

        return response.data as IngestResponse
    },

    /**
     * Query the RAG system with streaming
     */
    streamQuery: async function* (params: QueryRequest) {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        }
        
        // Attach auth token if user is authenticated
        const currentUser = auth.currentUser
        if (currentUser) {
            const idToken = await currentUser.getIdToken()
            headers['Authorization'] = `Bearer ${idToken}`
        }
        
        const response = await fetch(`${api.defaults.baseURL}rag/query/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify(params),
        })

        if (!response.ok) {
            throw new Error(`Failed to fetch stream: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) return

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')

            for (const line of lines) {
                if (!line.trim()) continue
                try {
                    const data = JSON.parse(line)
                    yield data
                } catch (e) {
                    console.error('Failed to parse stream chunk:', e, line)
                }
            }
        }
    },

    /**
     * Check system and database health
     * Hits: GET /health
     */
    checkHealth: async () => {
        const response = await api.get('health')
        return response.data as { status: string; database: 'healthy' | 'unhealthy' }
    }
}
