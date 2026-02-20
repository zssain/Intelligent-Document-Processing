import { createFileRoute, redirect } from '@tanstack/react-router'
import { Analytics } from '@/features/analytics'
import {
    Download,
    Share2,
    MoreHorizontal,
    Sparkles,
    ArrowUpRight
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'

export const Route = createFileRoute('/analytics')({
    beforeLoad: ({ context }) => {
        const auth = (context as any).auth
        if (!auth || auth.role !== 'org_admin') {
            throw redirect({ to: '/' })
        }
    },
    component: AnalyticsPage,
})

function AnalyticsPage() {
    return (
        <div className="relative min-h-[80vh]">
            {/* Under Construction Overlay */}
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/20 backdrop-blur-[8px] rounded-3xl border border-primary/10">
                <div className="bg-card/95 border border-primary/20 p-12 rounded-[2.5rem] shadow-[0_0_50px_rgba(var(--primary),0.15)] flex flex-col items-center gap-6 text-center max-w-md transform transition-all hover:scale-105">
                    <div className="relative">
                        <div className="absolute inset-0 blur-2xl bg-primary/20 animate-pulse rounded-full" />
                        <div className="relative h-20 w-20 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                            <Sparkles className="h-10 w-10 animate-bounce" />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-3xl font-black tracking-tighter text-foreground uppercase">Advanced Analytics</h2>
                        <p className="text-xs font-black uppercase tracking-[0.3em] text-primary">System Sequence Pending</p>
                    </div>
                    <div className="h-px w-24 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
                    <p className="text-sm text-muted-foreground font-medium leading-relaxed">
                        This auditing node is currently being calibrated for deep-space document intelligence.
                        Live telemetry will be available in the next core update.
                    </p>
                    <div className="bg-primary/5 px-4 py-2 rounded-full border border-primary/10">
                        <p className="text-[10px] font-bold text-primary uppercase tracking-widest">Status: Under Construction</p>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-8 opacity-20 grayscale blur-[2px] pointer-events-none select-none">
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
                                    Extraction accuracy for <span className="text-primary underline decoration-primary/30 underline-offset-4">Arabic Legal documents</span> has increased by <span className="text-emerald-500">4.2%</span> this week.
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

                        {/* Placeholder for Throughput / System Health */}
                        <div className="rounded-2xl border border-dashed border-border/50 bg-accent/10 p-8 flex flex-col items-center justify-center text-center gap-4 grayscale opacity-40 hover:grayscale-0 hover:opacity-100 transition-all">
                            <div className="h-12 w-12 rounded-full border-2 border-border/50 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-muted-foreground/40" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs font-black uppercase tracking-widest text-muted-foreground/60">Node Health Insights</p>
                                <p className="text-[11px] font-medium text-muted-foreground/40">Coming in next sequence update.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
