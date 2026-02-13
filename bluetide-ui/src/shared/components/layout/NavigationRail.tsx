import { Link, useRouterState } from '@tanstack/react-router'
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    BarChart3,
    Settings,
    User
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { ThemeToggle } from '@/shared/components/layout/theme-toggle'
import { LanguageToggle } from '@/shared/components/layout/language-toggle'
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/shared/components/ui/tooltip'
import { useTranslation } from 'react-i18next'

interface NavItem {
    icon: typeof LayoutDashboard
    label: string
    href: string
}

export function NavigationRail() {
    const { t } = useTranslation()
    const routerState = useRouterState()
    const pathname = routerState.location.pathname

    const navItems: NavItem[] = [
        { icon: LayoutDashboard, label: t('nav.dashboard'), href: '/' },
        { icon: FileText, label: t('nav.documents'), href: '/documents' },
        { icon: MessageSquare, label: t('nav.chat'), href: '/chat' },
        { icon: BarChart3, label: t('nav.analytics'), href: '/analytics' },
    ]

    return (
        <aside className="fixed left-0 top-0 z-50 flex h-full w-[64px] flex-col items-center border-e bg-card py-4 shadow-sm">
            {/* App Logo */}
            <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
                <FileText className="h-6 w-6" />
            </div>

            <TooltipProvider delayDuration={0}>
                <nav className="flex flex-1 flex-col gap-4">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
                        return (
                            <Tooltip key={item.label}>
                                <TooltipTrigger asChild>
                                    <Link
                                        to={item.href}
                                        className={cn(
                                            "group flex h-11 w-11 items-center justify-center rounded-xl transition-all hover:bg-accent",
                                            isActive
                                                ? "bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(var(--primary),0.1)]"
                                                : "text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        <item.icon className={cn(
                                            "h-5 w-5 transition-transform group-hover:scale-110",
                                            isActive && "fill-current/10"
                                        )} />
                                    </Link>
                                </TooltipTrigger>
                                <TooltipContent side="right" className="font-bold border-border/50">
                                    {item.label}
                                </TooltipContent>
                            </Tooltip>
                        )
                    })}
                </nav>

                <div className="mt-auto flex flex-col items-center gap-4">
                    <LanguageToggle />
                    <ThemeToggle />

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button className="group flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition-all hover:bg-accent hover:text-foreground">
                                <Settings className="h-5 w-5 transition-transform group-hover:rotate-45" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="font-bold border-border/50">
                            {t('nav.settings')}
                        </TooltipContent>
                    </Tooltip>

                    <div className="flex h-11 w-11 items-center justify-center">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center overflow-hidden">
                            <User className="h-4 w-4 text-primary" />
                        </div>
                    </div>
                </div>
            </TooltipProvider>
        </aside>
    )
}
