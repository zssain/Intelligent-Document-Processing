import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { NavigationRail } from './NavigationRail'
import { cn } from '@/shared/lib/utils'
import { useRouterState } from '@tanstack/react-router'
import { ThemeToggle } from './theme-toggle'

interface AppShellProps {
    children: ReactNode
    showSidebar?: boolean
    fullBleed?: boolean
}

export function AppShell({ children, showSidebar = true, fullBleed }: AppShellProps) {
    const routerState = useRouterState()
    const pathname = routerState.location.pathname
    const isFullBleed = fullBleed ?? pathname.startsWith('/chat')

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            {/* Top Header Bar */}
            <header className="h-12 min-h-[48px] flex items-center justify-between px-4 border-b bg-card/80 backdrop-blur-xl z-50 pl-[72px]">
                {/* Left: Logo + App Name */}
                <div className="flex items-center gap-2.5">
                    <img
                        src="/logo.png"
                        alt="Teclusion AI"
                        className="h-8 w-8 object-contain"
                    />
                    <div className="flex flex-col leading-none">
                        <span className="text-sm font-bold tracking-tight">Teclusion AI</span>
                        <span className="text-[9px] uppercase tracking-widest text-muted-foreground font-medium">Intelligent Document Processing</span>
                    </div>
                </div>

                {/* Right: Theme Toggle */}
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                </div>
            </header>

            {/* Main Content with NavRail + Sidebar + Main */}
            <div className="flex flex-1 overflow-hidden">
                {/* Global Navigation Rail */}
                <NavigationRail />

                {/* Content Area */}
                <div className="flex flex-1 pl-[64px] overflow-hidden">
                    {/* Secondary Sidebar */}
                    {showSidebar && <Sidebar className="hidden lg:flex" />}

                    {/* Phase 3: Main Page Content */}
                    <main className={cn(
                        "flex-1 overflow-auto bg-background",
                        !isFullBleed && "p-8"
                    )}>
                        {children}
                    </main>
                </div>
            </div>
        </div>
    )
}
