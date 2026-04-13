import { useRouterState } from '@tanstack/react-router'
import { cn } from '@/shared/lib/utils'
import { Chat } from '@/features/chat'
import { Analytics } from '@/features/analytics'
import {
    FolderOpen,
    Upload,
    ChevronLeft,
    Cloud,
    Share2,
    HardDrive,
    Layers,
    LayoutDashboard,
    Users,
    Tag,
    ScrollText,
} from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/context/auth-context'
import { useIngestionMode, type IngestionMode } from '@/features/documents/ingestion-mode-context'
import { usePermissions } from '@/shared/hooks/usePermissions'

interface SidebarProps {
    className?: string
}

export function Sidebar({ className }: SidebarProps) {
    const { t } = useTranslation()
    const routerState = useRouterState()
    const pathname = routerState.location.pathname
    const isChat = pathname.startsWith('/chat')
    const isAnalytics = pathname.startsWith('/analytics')
    const isDocuments = pathname.startsWith('/documents')
    const isAdmin = pathname.startsWith('/admin')
    const { role } = useAuth()
    const isUserAdmin = role === 'org_admin'

    // Get user permissions for source access
    const { canViewSource, isAdmin: isPermAdmin } = usePermissions()

    // Only call hook when in documents context – it's always mounted via root provider
    const { activeMode, setMode } = useIngestionMode()

    const allModeLinks: { label: string; icon: typeof Cloud; mode: IngestionMode; source: string }[] = [
        { label: t('sidebar.s3_datalake'), icon: Cloud, mode: 's3', source: 's3' },
        { label: t('sidebar.sharepoint'), icon: Share2, mode: 'sharepoint', source: 'sharepoint' },
        { label: t('sidebar.google_drive'), icon: HardDrive, mode: 'gdrive', source: 'gdrive' },
        { label: t('sidebar.direct_upload'), icon: Upload, mode: 'upload', source: 'direct_upload' },
    ]

    // Filter sources based on permissions: admin sees all, regular users only see allowed ones
    const modeLinks = isPermAdmin
        ? allModeLinks
        : allModeLinks.filter(item => canViewSource(item.source))

    const adminLinks = [
        { label: 'Overview', icon: LayoutDashboard, href: '/admin' },
        { label: 'User Management', icon: Users, href: '/admin/users' },
        { label: 'Categories', icon: Tag, href: '/admin/categories' },
        { label: 'Audit Log', icon: ScrollText, href: '/admin/audit-log' },
    ]

    return (
        <aside
            className={cn(
                'flex flex-col border-e bg-card/30 backdrop-blur-xl transition-all duration-300 py-6 overflow-hidden',
                (isChat || isAnalytics) ? 'w-80' : 'w-64',
                className
            )}
        >
            {/* Feature Label */}
            <div className="px-6 mb-8 flex items-center justify-between">
                <h2 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                    {isChat ? t('nav.chat') : isAnalytics ? t('nav.analytics') : isDocuments ? t('nav.documents') : isAdmin ? 'Admin' : t('sidebar.workspace')}
                </h2>
                <button className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground/40 hover:text-foreground transition-colors">
                    <ChevronLeft className="h-3 w-3" />
                </button>
            </div>

            <div className="flex-1 px-3 overflow-y-auto custom-scrollbar">
                {isChat ? (
                    <Chat.SidebarContent />
                ) : isAnalytics ? (
                    <Analytics.Sidebar />
                ) : isAdmin ? (
                    <nav className="space-y-1">
                        {adminLinks.map((item) => {
                            const isActive = item.href === '/admin'
                                ? pathname === '/admin' || pathname === '/admin/'
                                : pathname.startsWith(item.href)
                            return (
                                <Link
                                    key={item.href}
                                    to={item.href}
                                    className={cn(
                                        'group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-bold transition-all hover:bg-accent active:scale-[0.98]',
                                        isActive
                                            ? 'bg-primary/10 text-primary'
                                            : ''
                                    )}
                                >
                                    <item.icon className={cn(
                                        'h-4 w-4 transition-colors',
                                        isActive
                                            ? 'text-primary'
                                            : 'text-muted-foreground group-hover:text-primary'
                                    )} />
                                    <span className={cn(
                                        'transition-colors',
                                        isActive
                                            ? 'text-primary'
                                            : 'text-muted-foreground group-hover:text-foreground'
                                    )}>{item.label}</span>
                                </Link>
                            )
                        })}
                    </nav>
                ) : isDocuments ? (
                    <nav className="space-y-1">
                        {/* All Documents link */}
                        <Link
                            to="/documents"
                            className="group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-bold transition-all hover:bg-accent active:scale-[0.98] [&.active]:bg-primary/10 [&.active]:text-primary"
                        >
                            <FolderOpen className="h-4 w-4 text-muted-foreground group-hover:text-primary group-[.active]:text-primary" />
                            <span className="text-muted-foreground group-hover:text-foreground group-[.active]:text-primary">{t('sidebar.all_documents')}</span>
                        </Link>

                        {/* Ingestion Modes section — show for all users, filtered by permissions */}
                        {modeLinks.length > 0 && (
                            <>
                                <div className="pt-4 pb-1 px-4">
                                    <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/50">
                                        {t('sidebar.ingestion_sources')}
                                    </p>
                                </div>

                                {/* Mode links */}
                                {modeLinks.map((item) => {
                                    const isModeActive = activeMode === item.mode
                                    return (
                                        <button
                                            key={item.mode}
                                            onClick={() => setMode(item.mode)}
                                            className={cn(
                                                'group flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-bold transition-all hover:bg-accent active:scale-[0.98]',
                                                isModeActive
                                                    ? 'bg-primary/10 text-primary'
                                                    : ''
                                            )}
                                        >
                                            <item.icon className={cn(
                                                'h-4 w-4 transition-colors',
                                                isModeActive
                                                    ? 'text-primary'
                                                    : 'text-muted-foreground group-hover:text-primary'
                                            )} />
                                            <span className={cn(
                                                'transition-colors',
                                                isModeActive
                                                    ? 'text-primary'
                                                    : 'text-muted-foreground group-hover:text-foreground'
                                            )}>{item.label}</span>
                                            {isModeActive && (
                                                <Layers className="h-3 w-3 ml-auto text-primary/60" />
                                            )}
                                        </button>
                                    )
                                })}
                            </>
                        )}
                    </nav>
                ) : (
                    <div className="px-3">
                        <div className="rounded-xl border border-border/50 bg-accent/30 p-4">
                            <p className="text-[11px] font-bold text-muted-foreground leading-relaxed">
                                {t('sidebar.select_destination')}
                            </p>
                        </div>
                    </div>
                )}
            </div>

        </aside>
    )
}
