import { createFileRoute } from '@tanstack/react-router'
import { Analytics } from '@/features/analytics'
import {
    Download,
    Share2,
    MoreHorizontal,
    Sparkles,
    ArrowUpRight,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'

export const Route = createFileRoute('/analytics')({
    component: AnalyticsPage,
})

function AnalyticsPage() {
    return (
        <div className="flex flex-col gap-8 p-6">
            {/* Local Header / Toolbar */}
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-black tracking-tighter text-foreground">Intelligence Audit</h1>
                            <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20 text-[9px] font-black uppercase tracking-widest px-2">v2.4.0</Badge>
                        </div>
                        <p className="text-xs font-medium text-muted-foreground/60 tracking-wide uppercase">Monitoring Intelligent Document Processing Sequences</p>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="h-9 px-4 rounded-xl border-border/50 font-bold text-[11px] uppercase tracking-widest hover:bg-accent/50">
                            <Download className="mr-2 h-3.5 w-3.5" />
                            Export Data
                        </Button>
                        <Button variant="outline" size="sm" className="h-9 w-9 p-0 rounded-xl border-border/50 hover:bg-accent/50">
                            <Share2 className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="outline" size="sm" className="h-9 w-9 p-0 rounded-xl border-border/50 hover:bg-accent/50">
                            <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                </div>

                {/* Smart Insights Banner */}
                <div className="rounded-2xl border border-primary/20 bg-gradient-to-r from-primary/10 via-background to-transparent p-4 flex items-center justify-between group cursor-help transition-all hover:bg-primary/[0.03]">
                    <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary shadow-[0_0_15px_rgba(var(--primary),0.1)]">
                            <Sparkles className="h-5 w-5" />
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-[10px] font-black uppercase tracking-widest text-primary/70">Top Insight</p>
                            <p className="text-sm font-bold text-foreground/90">
                                Document intelligence pipeline is active. Connect data sources and ingest files to see analytics populate.
                            </p>
                        </div>
                    </div>
                    <ArrowUpRight className="h-5 w-5 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
            </div>

            {/* Metrics Grid */}
            <Analytics.Metrics />

            {/* Main Visuals Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Column: Intelligence Matrix & Queue */}
                <div className="lg:col-span-8 space-y-6">
                    <Analytics.Matrix />
                    <Analytics.Queue />
                </div>

                {/* Right Column: Confidence & Secondary Visuals */}
                <div className="lg:col-span-4 space-y-6">
                    <Analytics.Confidence />

                    {/* System Health placeholder */}
                    <div className="rounded-2xl border border-border/50 bg-card p-6 flex flex-col gap-4">
                        <div className="flex items-center gap-2">
                            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                                <Sparkles className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                                <p className="text-xs font-black uppercase tracking-widest text-muted-foreground/60">System Health</p>
                            </div>
                        </div>
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Vector DB</span>
                                <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">Healthy</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">API Server</span>
                                <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">Running</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Firestore</span>
                                <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">Connected</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
