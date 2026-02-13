export type MessageRole = 'user' | 'assistant' | 'system'

export interface ReasoningStep {
    id: string
    label: string
    status: 'idle' | 'running' | 'completed' | 'failed'
}

export interface Citation {
    id: string
    name: string
    source: 'sharepoint' | 's3' | 'internal'
    confidence: number
    access_verified: boolean
    snippet?: string
}

export interface ChatMessage {
    id: string
    role: MessageRole
    content: string
    displayContent?: string
    timestamp: Date
    reasoningSteps?: ReasoningStep[]
    citations?: Citation[]
    confidence?: number
}

export interface ChatSession {
    id: string
    title: string
    lastModified: Date
    status: 'completed' | 'running'
}
