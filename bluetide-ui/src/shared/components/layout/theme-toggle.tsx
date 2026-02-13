import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/shared/components/theme-provider"
import { Button } from "@/shared/components/ui/button"

export function ThemeToggle() {
    const { theme, setTheme } = useTheme()

    return (
        <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            className="h-9 w-9 rounded-md transition-all duration-300 hover:bg-accent relative flex items-center justify-center"
            aria-label="Toggle theme"
        >
            {theme === "dark" ? (
                <Moon className="h-4 w-4 animate-in zoom-in duration-500 fill-current/10" />
            ) : (
                <Sun className="h-4 w-4 animate-in zoom-in duration-500 fill-current/10 text-amber-500" />
            )}
        </Button>
    )
}
