import { TrendingUp, Languages, ArrowUpRight } from 'lucide-react'
import { useDocuments } from '@/features/documents/context'
import { useTranslation } from 'react-i18next'

export function ChatStartView() {
    const { t } = useTranslation()
    const { documents } = useDocuments()
    const documentCount = documents.length.toLocaleString()

    const suggestions = [
        {
            title: t('chat.suggestions.revenue'),
            desc: t('chat.suggestions.revenue_desc'),
            icon: <TrendingUp className="h-4 w-4 text-emerald-500" />
        },
        {
            title: t('chat.suggestions.translate'),
            desc: t('chat.suggestions.translate_desc'),
            icon: <Languages className="h-4 w-4 text-primary" />
        }
    ]

    return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto w-full space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-1000">
            {/* Language Icons */}
            <div className="flex items-center gap-4">
                <div className="h-12 w-16 bg-accent/50 rounded-xl border flex items-center justify-center font-bold text-lg shadow-sm hover:scale-105 transition-transform cursor-default">EN</div>
                <div className="h-12 w-16 bg-emerald-500/10 text-emerald-500 rounded-xl border border-emerald-500/20 flex items-center justify-center font-bold text-lg shadow-sm hover:scale-105 transition-transform cursor-default">ع</div>
            </div>

            {/* Main Heading */}
            <div className="text-center space-y-6">
                <h1 className="text-4xl md:text-6xl font-black tracking-tight text-foreground flex flex-col gap-2">
                    {t('chat.ask_anything')}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-primary to-emerald-400 bg-[length:200%_auto] animate-gradient-flow">
                        {documentCount} {t('chat.documents_suffix')}
                    </span>
                </h1>
                <p className="text-lg text-muted-foreground max-w-xl mx-auto font-medium">
                    {t('chat.secure_reasoning')}
                </p>
            </div>

            {/* Suggestions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        className="p-5 rounded-2xl border bg-card/50 hover:bg-card hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5 transition-all text-start group flex flex-col gap-3"
                    >
                        <div className="flex items-center justify-between w-full">
                            <div className="h-10 w-10 rounded-xl bg-accent flex items-center justify-center group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                {s.icon}
                            </div>
                            <ArrowUpRight className="h-4 w-4 text-muted-foreground/30 group-hover:text-primary transition-all opacity-0 group-hover:opacity-100" />
                        </div>
                        <div>
                            <p className="font-bold text-foreground">{s.title}</p>
                            <p className="text-sm text-muted-foreground/80 font-medium">"{s.desc}"</p>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    )
}
