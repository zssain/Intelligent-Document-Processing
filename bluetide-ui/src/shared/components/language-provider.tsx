import { createContext, useContext, useEffect, useState } from "react"
import i18n from "../../i18n/config"

type Language = "en" | "ar"

type LanguageProviderProps = {
    children: React.ReactNode
    defaultLanguage?: Language
    storageKey?: string
}

type LanguageProviderState = {
    language: Language
    setLanguage: (language: Language) => void
}

const initialState: LanguageProviderState = {
    language: "en",
    setLanguage: () => null,
}

const LanguageProviderContext = createContext<LanguageProviderState>(initialState)

export function LanguageProvider({
    children,
    defaultLanguage = "en",
    storageKey = "bluetide-ui-language",
    ...props
}: LanguageProviderProps) {
    const [language, setLanguage] = useState<Language>(
        () => (localStorage.getItem(storageKey) as Language) || defaultLanguage
    )

    useEffect(() => {
        const root = window.document.documentElement
        root.lang = language

        if (language === "ar") {
            root.dir = "rtl"
            root.classList.add("font-arabic")
        } else {
            root.dir = "ltr"
            root.classList.remove("font-arabic")
        }

        if (i18n.language !== language) {
            i18n.changeLanguage(language)
        }
    }, [language])

    const value = {
        language,
        setLanguage: (lang: Language) => {
            localStorage.setItem(storageKey, lang)
            i18n.changeLanguage(lang).then(() => {
                setLanguage(lang)
            })
        },
    }

    return (
        <LanguageProviderContext.Provider {...props} value={value}>
            {children}
        </LanguageProviderContext.Provider>
    )
}

export const useLanguage = () => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
