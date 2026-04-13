import { Link, useRouterState } from '@tanstack/react-router'
import {
    LayoutDashboard,
    FileText,
    MessageSquare,
    BarChart3,
    Settings,
    User,
    ShieldCheck,
    LogOut
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
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/shared/components/ui/popover'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/context/auth-context'
import { useState } from 'react'

interface NavItem {
    icon: typeof LayoutDashboard
    label: string
    href: string
}

export function NavigationRail() {
    const { t } = useTranslation()
    const { email, role, clearance, signOut } = useAuth()
    const routerState = useRouterState()
    const pathname = routerState.location.pathname
    const [isUserPopoverOpen, setIsUserPopoverOpen] = useState(false)

    const navItems: NavItem[] = [
        { icon: LayoutDashboard, label: t('nav.dashboard'), href: '/' },
        { icon: FileText, label: t('nav.documents'), href: '/documents' },
        { icon: MessageSquare, label: t('nav.chat'), href: '/chat' },
        { icon: BarChart3, label: t('nav.analytics'), href: '/analytics' },
    ]

    // Filter navigation items based on role
    const filteredNavItems = navItems.filter(item => {
        // Hide Dashboard & Analytics for non-admin users
        if (role !== 'org_admin' && (item.href === '/' || item.href === '/analytics')) {
            return false
        }
        return true
    })

    const handleSignOut = async () => {
        try {
            await signOut()
            setIsUserPopoverOpen(false)
        } catch (error) {
            console.error('Sign out error:', error)
        }
    }

    return (
        <aside className="fixed left-0 top-12 z-50 flex h-[calc(100%-48px)] w-[64px] flex-col items-center border-e bg-card py-4 shadow-sm">
            {/* App Logo */}
            <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
                <FileText className="h-6 w-6" />
            </div>

            <TooltipProvider delayDuration={0}>
                <nav className="flex flex-1 flex-col gap-4">
                    {filteredNavItems.map((item) => {
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

                    {/* Admin Link - Only for org_admin */}
                    {role === 'org_admin' && (
                        <>
                            <div className="my-2 h-px bg-border" />
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Link
                                        to="/admin"
                                        className={cn(
                                            "group flex h-11 w-11 items-center justify-center rounded-xl transition-all hover:bg-accent",
                                            pathname.startsWith('/admin')
                                                ? "bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(var(--primary),0.1)]"
                                                : "text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        <ShieldCheck className={cn(
                                            "h-5 w-5 transition-transform group-hover:scale-110",
                                            pathname.startsWith('/admin') && "fill-current/10"
                                        )} />
                                    </Link>
                                </TooltipTrigger>
                                <TooltipContent side="right" className="font-bold border-border/50">
                                    Admin
                                </TooltipContent>
                            </Tooltip>
                        </>
                    )}
                </nav>

                <div className="mt-auto flex flex-col items-center gap-4">
                    <LanguageToggle />

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Link
                                to={role === 'org_admin' ? '/admin' : '/documents'}
                                className={cn(
                                    "group flex h-11 w-11 items-center justify-center rounded-xl transition-all hover:bg-accent",
                                    pathname.startsWith('/admin')
                                        ? "bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(var(--primary),0.1)]"
                                        : "text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <Settings className={cn(
                                    "h-5 w-5 transition-transform group-hover:rotate-45",
                                    pathname.startsWith('/admin') && "fill-current/10"
                                )} />
                            </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="font-bold border-border/50">
                            {role === 'org_admin' ? 'Admin Settings' : t('nav.settings')}
                        </TooltipContent>
                    </Tooltip>

                    <div className="flex h-11 w-11 items-center justify-center">
                        <Popover open={isUserPopoverOpen} onOpenChange={setIsUserPopoverOpen}>
                            <PopoverTrigger asChild>
                                <button className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center overflow-hidden hover:scale-110 transition-transform">
                                    <User className="h-4 w-4 text-primary" />
                                </button>
                            </PopoverTrigger>
                            <PopoverContent side="right" align="end" className="w-64 p-4">
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-sm font-medium truncate">{email}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium">
                                                {role || 'user'}
                                            </span>
                                            <span className="text-xs px-2 py-1 rounded-full bg-muted text-muted-foreground font-medium">
                                                Clearance {clearance || 0}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="h-px bg-border" />
                                    <button
                                        onClick={handleSignOut}
                                        className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-destructive hover:bg-destructive/10 transition-colors"
                                    >
                                        <LogOut className="h-4 w-4" />
                                        Sign Out
                                    </button>
                                </div>
                            </PopoverContent>
                        </Popover>
                    </div>
                </div>
            </TooltipProvider>
        </aside>
    )
}
