import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { ReactNode } from 'react'
import type { ChatMessage, ChatSession, Citation } from './types'
import { chatService } from './services/chat.service'

export interface SelectedDocument {
    id: string
    name: string
}

interface ChatContextValue {
    messages: ChatMessage[]
    sessions: ChatSession[]
    activeSessionId: string | null
    isSidebarOpen: boolean
    isRetrievalPanelOpen: boolean
    isTyping: boolean
    isDbConnected: boolean
    contextDocuments: SelectedDocument[]
    responseLanguage: 'english' | 'arabic'

    // Actions
    sendMessage: (content: string) => void
    setSidebarOpen: (open: boolean) => void
    setRetrievalPanelOpen: (open: boolean) => void
    setActiveSession: (id: string | null) => void
    createNewSession: () => void
    startNewSessionWithContext: (docs: SelectedDocument[]) => void
    setContextDocuments: (docs: SelectedDocument[]) => void
    removeContextDocument: (id: string) => void
    setResponseLanguage: (lang: 'english' | 'arabic') => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function useChat() {
    const context = useContext(ChatContext)
    if (!context) {
        throw new Error('useChat must be used within a ChatProvider')
    }
    return context
}

export function ChatProvider({ children }: { children: ReactNode }) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [sessions, setSessions] = useState<ChatSession[]>([])
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
    const [isSidebarOpen, setSidebarOpen] = useState(true)
    const [isRetrievalPanelOpen, setRetrievalPanelOpen] = useState(false)
    const [isTyping, setIsTyping] = useState(false)
    const [isDbConnected, setIsDbConnected] = useState(true)
    const [contextDocuments, setContextDocuments] = useState<SelectedDocument[]>([])
    const [responseLanguage, setResponseLanguage] = useState<'english' | 'arabic'>('english')

    // Poll health status with exponential backoff when backend is unreachable
    useEffect(() => {
        let timeoutId: ReturnType<typeof setTimeout>
        let cancelled = false
        let consecutiveFailures = 0
        const BASE_INTERVAL = 30_000 // 30s when healthy
        const MAX_INTERVAL = 300_000 // 5min max backoff

        const checkHealth = async () => {
            if (cancelled) return
            try {
                const health = await chatService.checkHealth()
                setIsDbConnected(health.database === 'healthy')
                consecutiveFailures = 0 // Reset on success
            } catch {
                if (consecutiveFailures === 0) {
                    console.warn('Backend health check failed — will retry with backoff')
                }
                consecutiveFailures++
                setIsDbConnected(false)
            }

            if (!cancelled) {
                // Exponential backoff: 30s, 60s, 120s, … capped at 5min
                const delay = Math.min(
                    BASE_INTERVAL * Math.pow(2, consecutiveFailures),
                    MAX_INTERVAL
                )
                timeoutId = setTimeout(checkHealth, delay)
            }
        }

        // Delay initial check to let the backend fully respond after page load
        timeoutId = setTimeout(checkHealth, 2000)
        return () => {
            cancelled = true
            clearTimeout(timeoutId)
        }
    }, [])

    const createNewSession = useCallback(() => {
        const id = Math.random().toString(36).substring(7)
        setSessions((prev: ChatSession[]) => [
            { id, title: 'New Analysis', lastModified: new Date(), status: 'running' },
            ...prev
        ])
        setActiveSessionId(id)
        setMessages([])
        setContextDocuments([])
    }, [])

    const startNewSessionWithContext = useCallback((docs: SelectedDocument[]) => {
        const id = Math.random().toString(36).substring(7)
        const title = docs.length === 1 ? `Analysis: ${docs[0].name}` : `${docs.length} Documents Analysis`
        setSessions((prev: ChatSession[]) => [
            { id, title, lastModified: new Date(), status: 'running' },
            ...prev
        ])
        setActiveSessionId(id)
        setMessages([])
        setContextDocuments(docs)
    }, [])

    const removeContextDocument = useCallback((id: string) => {
        setContextDocuments(prev => prev.filter(doc => doc.id !== id))
    }, [])

    const handleSendMessage = useCallback(async (content: string) => {
        // 1. Final content is just the user input to avoid embedding dilution
        const finalContent = content

        // 2. Add user message
        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: finalContent,
            displayContent: content, // Original content for UI
            timestamp: new Date()
        }
        setMessages((prev: ChatMessage[]) => [...prev, userMsg])

        // 2. Start typing / loading
        setIsTyping(true)

        try {
            // 3. Call RAG API with Streaming
            const assistantId = (Date.now() + 1).toString()
            const initialBotMsg: ChatMessage = {
                id: assistantId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                reasoningSteps: [
                    { id: 'r1', label: 'Analyzing request...', status: 'completed' },
                    { id: 'r2', label: 'Retrieving context...', status: 'running' },
                ]
            }
            setMessages((prev) => [...prev, initialBotMsg])
            setIsTyping(false) // Stop typing indicator since we have a message placeholder

            let fullContent = ''
            let citations: Citation[] = []

            console.log('Streaming query with params:', {
                question: finalContent,
                document_ids: contextDocuments.length > 0 ? contextDocuments.map(d => d.id) : undefined,
                language: responseLanguage
            })

            for await (const chunk of chatService.streamQuery({
                question: finalContent,
                document_ids: contextDocuments.length > 0 ? contextDocuments.map(d => d.id) : undefined,
                language: responseLanguage
            })) {
                // Handle streamed content tokens
                if (chunk.content) {
                    fullContent += chunk.content
                    setMessages((prev) => prev.map(m =>
                        m.id === assistantId ? {
                            ...m,
                            content: fullContent,
                            reasoningSteps: undefined
                        } : m
                    ))
                }

                // Handle legacy {"answer": ...} format (no-context fallback)
                if (chunk.answer) {
                    fullContent += chunk.answer
                    setMessages((prev) => prev.map(m =>
                        m.id === assistantId ? {
                            ...m,
                            content: fullContent,
                            reasoningSteps: undefined
                        } : m
                    ))
                }

                // Handle error chunks
                if (chunk.error) {
                    fullContent += `⚠️ ${chunk.error}`
                    setMessages((prev) => prev.map(m =>
                        m.id === assistantId ? {
                            ...m,
                            content: fullContent,
                            reasoningSteps: undefined
                        } : m
                    ))
                }

                if (chunk.sources) {
                    citations = chunk.sources.map((s: any, idx: number) => ({
                        id: `s-${idx}`,
                        name: s,
                        source: 'internal',
                        confidence: 90,
                        access_verified: true
                    }))
                    setMessages((prev) => prev.map(m =>
                        m.id === assistantId ? {
                            ...m,
                            citations,
                        } : m
                    ))
                }
            }
        } catch (error) {
            console.error('Failed to get AI response:', error)
            const errorMsg: ChatMessage = {
                id: (Date.now() + 2).toString(),
                role: 'assistant',
                content: "I'm sorry, I encountered an error while processing your request.",
                timestamp: new Date()
            }
            setMessages((prev: ChatMessage[]) => [...prev, errorMsg])
        } finally {
            setIsTyping(false)
        }
    }, [contextDocuments, responseLanguage])

    return (
        <ChatContext.Provider
            value={{
                messages,
                sessions,
                activeSessionId,
                isSidebarOpen,
                isRetrievalPanelOpen,
                isTyping,
                isDbConnected,
                contextDocuments,
                sendMessage: handleSendMessage,
                setSidebarOpen,
                setRetrievalPanelOpen,
                setActiveSession: setActiveSessionId,
                createNewSession,
                startNewSessionWithContext,
                setContextDocuments,
                removeContextDocument,
                responseLanguage,
                setResponseLanguage
            }}
        >
            {children}
        </ChatContext.Provider>
    )
}
