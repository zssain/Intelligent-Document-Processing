import { Link } from '@tanstack/react-router'
import { FileText, Activity } from 'lucide-react'
import { ThemeToggle } from '@/shared/components/layout/theme-toggle'
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from '@/shared/components/ui/avatar'
import {
    NavigationMenu,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    navigationMenuTriggerStyle,
} from '@/shared/components/ui/navigation-menu'
import { cn } from '../../lib/utils'
import { useQuery } from '@tanstack/react-query'
import api from '@/shared/lib/api'

export function Header() {
    const { data: health, status } = useQuery({
        queryKey: ['api-health'],
        queryFn: async () => {
            // Use the shared api instance which resolves VITE_API_URL correctly
            const response = await api.get('health')
            return response.data
        },
        refetchInterval: 10000,
        retry: 3
    })

    const isHealthy = status === 'success' && health?.status === 'healthy'

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container mx-auto flex h-16 items-center justify-between px-4">
                {/* Left: Logo */}
                <div className="flex items-center gap-6">
                    <Link to="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-90">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-sm shadow-primary/20">
                            <FileText className="h-5 w-5 text-primary-foreground" />
                        </div>
                        <span className="text-xl font-bold tracking-tight">
                            Bluetide
                        </span>
                    </Link>

                    {/* Center: Navigation */}
                    <NavigationMenu className="hidden md:flex">
                        <NavigationMenuList className="gap-2">
                            <NavigationMenuItem>
                                <Link to="/documents">
                                    {({ isActive }: { isActive: boolean }) => (
                                        <NavigationMenuLink
                                            className={cn(
                                                navigationMenuTriggerStyle(),
                                                'h-10 px-4 transition-all duration-200 rounded-lg',
                                                isActive
                                                    ? 'bg-primary/10 text-primary font-bold shadow-sm ring-1 ring-primary/20'
                                                    : 'bg-transparent text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                                            )}
                                        >
                                            Documents
                                        </NavigationMenuLink>
                                    )}
                                </Link>
                            </NavigationMenuItem>
                            <NavigationMenuItem>
                                <Link to="/chat">
                                    {({ isActive }: { isActive: boolean }) => (
                                        <NavigationMenuLink
                                            className={cn(
                                                navigationMenuTriggerStyle(),
                                                'h-10 px-4 transition-all duration-200 rounded-lg',
                                                isActive
                                                    ? 'bg-primary/10 text-primary font-bold shadow-sm ring-1 ring-primary/20'
                                                    : 'bg-transparent text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                                            )}
                                        >
                                            Chat
                                        </NavigationMenuLink>
                                    )}
                                </Link>
                            </NavigationMenuItem>
                            <NavigationMenuItem>
                                <Link to="/analytics">
                                    {({ isActive }: { isActive: boolean }) => (
                                        <NavigationMenuLink
                                            className={cn(
                                                navigationMenuTriggerStyle(),
                                                'h-10 px-4 transition-all duration-200 rounded-lg',
                                                isActive
                                                    ? 'bg-primary/10 text-primary font-bold shadow-sm ring-1 ring-primary/20'
                                                    : 'bg-transparent text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                                            )}
                                        >
                                            Analytics
                                        </NavigationMenuLink>
                                    )}
                                </Link>
                            </NavigationMenuItem>
                        </NavigationMenuList>
                    </NavigationMenu>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-wider transition-all duration-300",
                        isHealthy
                            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-500 border-rose-500/20 shadow-[0_0_12px_rgba(244,63,94,0.15)]"
                    )}>
                        <Activity className={cn("w-3 h-3", isHealthy && "animate-pulse")} />
                        {isHealthy ? "API Online" : "API Offline"}
                    </div>

                    <ThemeToggle />
                    <div className="h-6 w-px bg-border mx-1" />
                    <Avatar className="h-9 w-9 border-2 border-background ring-1 ring-border">
                        <AvatarImage
                            src="/home/kanke/.gemini/antigravity/brain/c3ef0c47-d757-45c6-8352-84664b6a2a30/professional_avatar_1768295702051.png"
                            alt="User"
                        />
                        <AvatarFallback className="bg-primary/10 text-primary text-xs font-bold">JD</AvatarFallback>
                    </Avatar>
                </div>
            </div>
        </header>
    )
}
