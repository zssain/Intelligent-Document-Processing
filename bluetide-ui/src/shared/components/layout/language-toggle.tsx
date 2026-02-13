import { useLanguage } from "@/shared/components/language-provider"
import { Button } from "@/shared/components/ui/button"
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/shared/components/ui/tooltip"

export function LanguageToggle() {
    const { language, setLanguage } = useLanguage()

    const toggleLanguage = () => {
        setLanguage(language === "en" ? "ar" : "en")
    }

    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleLanguage}
                    className="h-11 w-11 rounded-xl transition-all duration-300 hover:bg-accent text-muted-foreground hover:text-foreground"
                    aria-label="Toggle language"
                >
                    <span className="text-sm font-bold tracking-tight">
                        {language === "en" ? "EN" : "ع"}
                    </span>
                </Button>
            </TooltipTrigger>
            <TooltipContent side="right" className="font-bold border-border/50">
                {language === "en" ? "Switch to Arabic" : "التبديل إلى الإنجليزية"}
            </TooltipContent>
        </Tooltip>
    )
}
