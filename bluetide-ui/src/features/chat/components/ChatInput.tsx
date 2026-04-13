import { useState } from 'react'
import { useChat } from '../context'
import { Send, Paperclip, Mic, X, Hash, Languages } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { useTranslation } from 'react-i18next'
import { cn } from '@/shared/lib/utils'

export function ChatInput() {
    const [input, setInput] = useState('')
    const { t } = useTranslation()
    const { sendMessage, isTyping, contextDocuments, removeContextDocument, responseLanguage, setResponseLanguage } = useChat()

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault()
        if (!input.trim() || isTyping) return
        sendMessage(input)
        setInput('')
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="max-w-4xl mx-auto w-full space-y-4"
        >
            {/* Document Context Pills */}
            {contextDocuments.length > 0 && (
                <div className="flex items-center gap-2 px-1 animate-in fade-in slide-in-from-bottom-2 duration-300 overflow-x-auto scrollbar-none">
                    <div className="flex items-center gap-2 flex-nowrap min-w-0">
                        {contextDocuments.map((doc) => (
                            <div
                                key={doc.id}
                                className="group flex items-center gap-2 bg-primary/10 border border-primary/20 text-primary px-3 py-1.5 rounded-full shadow-sm hover:bg-primary/15 transition-all shrink-0"
                            >
                                <Hash className="h-3 w-3 opacity-60" />
                                <span className="text-xs font-bold leading-none whitespace-nowrap max-w-[150px] truncate">{doc.name}</span>
                                <button
                                    type="button"
                                    onClick={() => removeContextDocument(doc.id)}
                                    className="h-4 w-4 rounded-full flex items-center justify-center hover:bg-rose-500/20 hover:text-rose-500 transition-colors shrink-0"
                                >
                                    <X className="h-3 w-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                    <div className="text-[10px] text-muted-foreground self-center italic shrink-0 ml-1 opacity-60">
                        {contextDocuments.length} docs selected
                    </div>
                </div>
            )}

            {/* Language Selection row */}
            <div className="flex items-center justify-between px-1 mb-2 animate-in fade-in slide-in-from-bottom-1 duration-500">
                <div className="flex items-center gap-2">
                    <div className="bg-primary/10 p-1.5 rounded-lg border border-primary/10">
                        <Languages className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">
                        {t('chat.response_language')}
                    </span>
                </div>
                <div className="flex bg-card/60 backdrop-blur-md p-1 rounded-xl border border-primary/10 shadow-sm gap-1">
                    <button
                        type="button"
                        onClick={() => setResponseLanguage('english')}
                        className={cn(
                            "text-[10px] px-4 py-1.5 rounded-lg font-bold transition-all active:scale-95",
                            responseLanguage === 'english'
                                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                : "text-muted-foreground hover:bg-primary/5"
                        )}
                    >
                        {t('chat.lang_en')}
                    </button>
                    <button
                        type="button"
                        onClick={() => setResponseLanguage('arabic')}
                        className={cn(
                            "text-[10px] px-4 py-1.5 rounded-lg font-bold transition-all active:scale-95",
                            responseLanguage === 'arabic'
                                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                : "text-muted-foreground hover:bg-primary/5"
                        )}
                    >
                        {t('chat.lang_ar')}
                    </button>
                </div>
            </div>

            {/* Input Box */}
            <div className="relative group transition-all">
                <div className="absolute inset-0 bg-primary/5 rounded-[22px] blur-md opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
                <div className="relative flex items-center bg-card/80 backdrop-blur-2xl border border-primary/20 shadow-2xl rounded-[22px] p-2 pr-3 ring-0 group-focus-within:ring-2 ring-primary/20 transition-all duration-300">
                    <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-xl">
                        <Paperclip className="h-5 w-5" />
                    </Button>
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                        placeholder="Ask in any language..."
                        className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-3 px-2 font-medium placeholder:text-muted-foreground/60"
                    />
                    <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-xl">
                            <Mic className="h-5 w-5" />
                        </Button>
                        <Button
                            type="submit"
                            disabled={!input.trim() || isTyping}
                            className="h-10 w-10 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl shadow-lg shadow-primary/20 transition-all active:scale-95 disabled:opacity-50"
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>
        </form>
    )
}
