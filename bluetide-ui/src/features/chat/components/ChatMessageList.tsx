import { useChat } from '../context'
import { Bot, User, CheckCircle2, Search, ShieldCheck, Info, FileWarning } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/components/ui/badge'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useRef } from 'react'
import { ChatTableActions } from './ChatTableActions'

const isArabic = (text: string) => {
    const arabicPattern = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return arabicPattern.test(text);
};

const formatMessageTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    }).format(new Date(date))
}

export function ChatMessageList() {
    const { messages, contextDocuments } = useChat()
    const isIsolated = contextDocuments.length > 0

    return (
        <div className="flex-1 space-y-8 p-6 max-w-4xl mx-auto w-full font-sans">
            {messages.map((msg) => {
                const arabic = isArabic(msg.content)
                const isOutOfScope = msg.content.includes('Financial bot can only help with the uploaded documents') ||
                    msg.content.includes('يمكن لمساعد التقارير المالية المساعدة فقط')

                return (
                    <div
                        key={msg.id}
                        className={cn(
                            "flex gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500",
                            msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                        )}
                    >
                        {/* Avatar */}
                        <div className={cn(
                            "h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm",
                            msg.role === 'user' ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                        )}>
                            {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                        </div>

                        {/* Content Area */}
                        <div className={cn(
                            "flex flex-col gap-2 max-w-[85%]",
                            msg.role === 'user' ? "items-end" : "items-start"
                        )}>
                            {/* Header info */}
                            {msg.role === 'assistant' && (
                                <div className={cn("flex items-center gap-3", arabic && "flex-row-reverse")}>
                                    <div className="flex flex-col">
                                        <div className={cn("flex items-center gap-2", arabic && "flex-row-reverse")}>
                                            <span className="text-xs font-bold text-foreground">Enterprise AI Assistant</span>
                                            <span className="text-[10px] text-muted-foreground/60 font-medium">{formatMessageTime(msg.timestamp)}</span>
                                        </div>
                                        {isIsolated && !isOutOfScope && (
                                            <div className={cn("flex items-center gap-1 mt-0.5", arabic && "flex-row-reverse")}>
                                                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                                <span className="text-[9px] font-black uppercase tracking-widest text-emerald-600/80">Grounded Analysis</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Bubble */}
                            <div
                                dir={arabic ? "rtl" : "ltr"}
                                className={cn(
                                    "p-4 rounded-2xl text-sm leading-relaxed shadow-sm relative overflow-hidden",
                                    arabic ? "text-right" : "text-left",
                                    msg.role === 'user'
                                        ? "bg-primary text-primary-foreground font-medium rounded-tr-none"
                                        : isOutOfScope
                                            ? "bg-amber-50/50 border-amber-200/50 text-amber-900 border rounded-tl-none font-medium"
                                            : "bg-card border rounded-tl-none text-foreground font-medium prose prose-slate max-w-none prose-sm prose-p:leading-relaxed prose-pre:bg-muted prose-pre:text-muted-foreground prose-table:border-collapse prose-th:border prose-th:px-2 prose-th:py-1 prose-td:border prose-td:px-2 prose-td:py-1"
                                )}
                            >
                                {msg.role === 'user' ? (
                                    msg.displayContent ?? msg.content
                                ) : isOutOfScope ? (
                                    <div className="flex flex-col gap-3 py-2">
                                        <div className="flex items-center gap-2 text-amber-600">
                                            <FileWarning className="h-5 w-5" />
                                            <span className="font-bold text-sm">Scope Limitation</span>
                                        </div>
                                        <p className="text-sm leading-relaxed opacity-90">
                                            {msg.content}
                                        </p>
                                        <div className="mt-2 p-3 bg-amber-100/50 rounded-xl border border-amber-200/50">
                                            <p className="text-[11px] font-bold text-amber-800 flex items-center gap-1.5">
                                                <Info className="h-3 w-3" />
                                                Recommendation:
                                            </p>
                                            <p className="text-[11px] text-amber-700/80 mt-1 leading-normal">
                                                This session is strictly isolated to your selected documents. Try selecting additional documents from the table if you believe the information is elsewhere.
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            table: ({ children }) => {
                                                const tableRef = useRef<HTMLTableElement>(null)
                                                return (
                                                    <div className="flex flex-col group/table mb-6">
                                                        <div className="overflow-x-auto my-2">
                                                            <table ref={tableRef} className="min-w-full divide-y divide-border border">
                                                                {children}
                                                            </table>
                                                        </div>
                                                        <ChatTableActions tableRef={tableRef} />
                                                    </div>
                                                )
                                            },
                                            thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
                                            th: ({ children }) => <th className={cn("px-3 py-2 text-xs font-bold uppercase tracking-wider border", arabic ? "text-right" : "text-left")}>{children}</th>,
                                            td: ({ children }) => <td className={cn("px-3 py-2 text-xs border whitespace-nowrap", arabic ? "text-right" : "text-left")}>{children}</td>,
                                            ul: ({ children }) => <ul className={cn("list-disc space-y-1 my-2", arabic ? "pr-4" : "pl-4")}>{children}</ul>,
                                            ol: ({ children }) => <ol className={cn("list-decimal space-y-1 my-2", arabic ? "pr-4" : "pl-4")}>{children}</ol>,
                                            li: ({ children }) => <li className="text-xs">{children}</li>,
                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                            strong: ({ children }) => <span className="font-bold text-primary">{children}</span>
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                )}

                                {/* Reasoning Process Card (Assistant Only) */}
                                {msg.role === 'assistant' && msg.reasoningSteps && (
                                    <div className="mt-4 p-4 rounded-xl bg-accent/30 border border-primary/10 space-y-4">
                                        <div className={cn("flex items-center justify-between", arabic && "flex-row-reverse")}>
                                            <div className={cn("flex items-center gap-2", arabic && "flex-row-reverse")}>
                                                <Search className="h-3.5 w-3.5 text-primary" />
                                                <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Reasoning Process</span>
                                            </div>
                                            <div className="h-5 w-5 rounded-full bg-primary/10 flex items-center justify-center">
                                                <span className="text-[10px] font-bold text-primary">?</span>
                                            </div>
                                        </div>

                                        <div className="space-y-3">
                                            {msg.reasoningSteps.map((step) => (
                                                <div key={step.id} className={cn("flex items-center gap-3", arabic && "flex-row-reverse")}>
                                                    <div className={cn(
                                                        "h-5 w-5 rounded-full flex items-center justify-center transition-colors",
                                                        step.status === 'completed' ? "bg-emerald-500/10 text-emerald-500" : "bg-primary/10 text-primary animate-pulse"
                                                    )}>
                                                        {step.status === 'completed' ? <CheckCircle2 className="h-3 w-3" /> : <Search className="h-3 w-3" />}
                                                    </div>
                                                    <span className={cn(
                                                        "text-[11px] font-semibold",
                                                        step.status === 'completed' ? "text-foreground" : "text-muted-foreground"
                                                    )}>
                                                        {step.label}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Citations / Sources */}
                            {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                                <div className={cn("flex flex-wrap gap-2 mt-2 px-1", arabic && "flex-row-reverse")}>
                                    {msg.citations.map((cite) => (
                                        <Badge
                                            key={cite.id}
                                            variant="outline"
                                            className="bg-primary/5 border-primary/10 text-[10px] font-bold hover:bg-primary/10 transition-colors gap-1.5 cursor-pointer py-1"
                                        >
                                            <ShieldCheck className="h-3 w-3 text-emerald-500" />
                                            {cite.name}
                                        </Badge>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
