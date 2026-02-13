import * as React from "react"
import { useNavigate } from "@tanstack/react-router"
import { Sparkles, Send } from "lucide-react"
import { useChat } from "@/features/chat"
import { useTranslation } from "react-i18next"

export const SearchChatBar = () => {
    const { t } = useTranslation()
    const [query, setQuery] = React.useState("")
    const navigate = useNavigate()
    const { createNewSession, sendMessage } = useChat()

    const handleSearch = (e?: React.FormEvent) => {
        e?.preventDefault()
        const trimmedQuery = query.trim()
        if (trimmedQuery) {
            createNewSession()
            sendMessage(trimmedQuery)
            navigate({ to: "/chat" })
        }
    }

    return (
        <form
            onSubmit={handleSearch}
            className="relative flex items-center gap-3 p-2 pl-4 pr-2 rounded-2xl bg-background/80 border border-border/50 backdrop-blur-xl shadow-2xl focus-within:border-primary/50 transition-all group lg:min-w-[600px]"
        >
            <Sparkles className="h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors" />

            <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('dashboard.search_placeholder')}
                className="flex-1 bg-transparent border-none outline-none text-sm text-foreground placeholder:text-muted-foreground/50 py-2"
            />

            <div className="flex items-center gap-2">
                <button
                    type="submit"
                    disabled={!query.trim()}
                    className="p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
                >
                    <Send className="h-5 w-5" />
                </button>
            </div>
        </form>
    )
}
