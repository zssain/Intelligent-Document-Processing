import { useChat } from '../context'
import { X, FileText, ShieldCheck, ExternalLink, Activity, Database } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { cn } from '@/shared/lib/utils'

export function ChatRetrievalPanel() {
    const { isRetrievalPanelOpen, setRetrievalPanelOpen, contextDocuments, messages } = useChat()

    // Get citations from the last assistant message
    const lastAssistantMsg = [...messages].reverse().find(m => m.role === 'assistant')
    const citations = lastAssistantMsg?.citations || []
    const isIsolated = contextDocuments.length > 0

    if (!isRetrievalPanelOpen) return null

    return (
        <aside className="w-80 border-s bg-card flex flex-col h-full overflow-hidden animate-in slide-in-from-right duration-300">
            <div className="p-4 border-b flex items-center justify-between bg-muted/20">
                <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    <h2 className="text-sm font-bold">Retrieval Panel</h2>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground"
                    onClick={() => setRetrievalPanelOpen(false)}
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
                {/* Semantic Search Status */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Retrieval Mode</span>
                        <span className="text-[10px] font-bold text-primary">{isIsolated ? 'STRICT' : 'GENERAL'}</span>
                    </div>
                    <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                        <div className={cn("h-full bg-primary", isIsolated ? "w-full" : "w-1/2")} />
                    </div>
                    <div className={cn(
                        "flex items-center gap-2 text-[10px] font-bold",
                        isIsolated ? "text-emerald-500" : "text-amber-500"
                    )}>
                        <ShieldCheck className="h-3 w-3" />
                        {isIsolated
                            ? `Strictly grounded in ${contextDocuments.length} document${contextDocuments.length > 1 ? 's' : ''}`
                            : "Searching global document library"}
                    </div>
                </div>

                {/* Active Analysis Context */}
                {isIsolated && (
                    <div className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Active Context</h3>
                        <div className="space-y-2">
                            {contextDocuments.map((doc) => (
                                <div
                                    key={doc.id}
                                    className="flex items-center gap-3 p-2 rounded-lg border bg-accent/20"
                                >
                                    <FileText className="h-4 w-4 text-primary/60" />
                                    <span className="text-xs font-medium truncate">{doc.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Latest Response Sources */}
                {citations.length > 0 && (
                    <div className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Latest Citations</h3>
                        <div className="space-y-3">
                            {citations.map((cite) => (
                                <div
                                    key={cite.id}
                                    className="group p-3 rounded-xl border bg-card hover:bg-accent/40 hover:border-primary/20 transition-all"
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="h-8 w-8 rounded-lg bg-emerald-500/5 flex items-center justify-center border border-emerald-500/10">
                                            <ShieldCheck className="h-4 w-4 text-emerald-500" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-bold truncate group-hover:text-primary transition-colors">{cite.name}</p>
                                            <p className="text-[10px] text-muted-foreground font-medium">Verified Source • Grounded</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {!isIsolated && citations.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                        <div className="h-12 w-12 rounded-2xl bg-muted/30 flex items-center justify-center">
                            <Database className="h-6 w-6 text-muted-foreground/40" />
                        </div>
                        <p className="text-xs text-muted-foreground px-4">
                            Start an analysis by selecting documents from the explorer.
                        </p>
                    </div>
                )}
            </div>

            <div className="p-4 border-t bg-muted/5">
                <Button variant="outline" className="w-full text-[11px] font-bold uppercase tracking-widest gap-2 bg-background">
                    <ExternalLink className="h-3.5 w-3.5" />
                    View Global Library
                </Button>
            </div>
        </aside>
    )
}
