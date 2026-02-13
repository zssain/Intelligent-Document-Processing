import { useChat } from '../context'
import { ChatStartView } from './ChatStartView'
import { ChatMessageList } from './ChatMessageList'
import { ChatInput } from './ChatInput'
import { Button } from '@/shared/components/ui/button'
import { Share2, PanelRightClose, PanelRightOpen, ShieldCheck, Database } from 'lucide-react'

export function ChatView() {
    const { messages, sessions, activeSessionId, isRetrievalPanelOpen, setRetrievalPanelOpen, contextDocuments } = useChat()
    const activeSession = sessions.find(s => s.id === activeSessionId)
    const isIsolated = contextDocuments.length > 0

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-br from-background via-background to-primary/5">
            {/* Context Header */}
            {activeSessionId && (
                <div className="h-14 border-b bg-background/50 backdrop-blur-md flex items-center justify-between px-6 z-10 shrink-0">
                    <div className="flex flex-col">
                        <h2 className="text-sm font-bold truncate">{activeSession?.title || 'New Analysis'}</h2>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">Session Active</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="h-8 gap-2 border-primary/20 hover:bg-primary/5">
                            <Share2 className="h-3.5 w-3.5" />
                            Share
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground"
                            onClick={() => setRetrievalPanelOpen(!isRetrievalPanelOpen)}
                        >
                            {isRetrievalPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
                        </Button>
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col relative">
                {/* Isolation Context Banner */}
                {isIsolated && (
                    <div className="sticky top-0 z-10 px-6 py-3 bg-emerald-500/5 border-b border-emerald-500/10 flex items-center justify-between animate-in slide-in-from-top duration-500">
                        <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                                <Database className="h-4 w-4 text-emerald-600" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700/70">Analysis Mode</span>
                                <span className="text-xs font-bold text-emerald-900">Isolated to {contextDocuments.length} document{contextDocuments.length > 1 ? 's' : ''}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                            <ShieldCheck className="h-3 w-3 text-emerald-600" />
                            <span className="text-[10px] font-bold text-emerald-700">Strict Grounding Active</span>
                        </div>
                    </div>
                )}

                {messages.length === 0 ? (
                    <ChatStartView />
                ) : (
                    <ChatMessageList />
                )}
            </div>

            <div className="pb-4 px-4 md:px-6 bg-gradient-to-t from-background via-background to-transparent">
                <ChatInput />
                <p className="text-[10px] text-center text-muted-foreground/50 mt-1.5 font-medium">
                    AI responses are generated in real-time. Please verify critical information using the provided source chips.
                </p>
            </div>
        </div>
    )
}
