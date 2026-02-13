import { useAnalytics } from '../context'
import { Checkbox } from '@/shared/components/ui/checkbox'
import { Label } from '@/shared/components/ui/label'
import { Badge } from '@/shared/components/ui/badge'
import {
    Calendar,
    Filter,
    Globe,
    Zap,
    History
} from 'lucide-react'

export function SidebarFilters() {
    const { filters, setFilters } = useAnalytics()

    const timeRanges = ['Last 24 Hours', 'Last 7 Days', 'Last 30 Days', 'Last 90 Days']
    const docTypes = ['Invoice', 'Contract', 'Passport', 'Identity Card']
    const schemas = ['Financial Audit', 'Legal Master', 'KYC Identity']

    return (
        <div className="space-y-8 py-2">
            {/* Timeframe Section */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 text-primary">
                    <History className="h-4 w-4" />
                    <span className="text-[10px] font-black uppercase tracking-widest">Timeframe</span>
                </div>
                <div className="grid grid-cols-1 gap-2">
                    {timeRanges.map((range) => (
                        <button
                            key={range}
                            onClick={() => setFilters({ ...filters, timeRange: range as any })}
                            className={`flex flex-col items-start gap-0.5 rounded-xl border px-3 py-2 text-left transition-all hover:bg-accent ${filters.timeRange === range
                                    ? 'border-primary/50 bg-primary/10 ring-1 ring-primary/20'
                                    : 'border-border/40 bg-card/40'
                                }`}
                        >
                            <span className={`text-xs font-bold ${filters.timeRange === range ? 'text-primary' : 'text-foreground/80'}`}>
                                {range}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Smart Segments Section */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 text-primary">
                    <Globe className="h-4 w-4" />
                    <span className="text-[10px] font-black uppercase tracking-widest">Language Clusters</span>
                </div>
                <div className="space-y-3">
                    {['Latin (EN, FR, ES)', 'Arabic (AR, UR)', 'Indic (HI, BN)'].map((cluster) => (
                        <div key={cluster} className="flex items-center gap-3">
                            <Checkbox id={cluster} className="rounded-md border-border/50 data-[state=checked]:bg-primary data-[state=checked]:border-primary" />
                            <Label htmlFor={cluster} className="text-[11px] font-bold text-muted-foreground/80 cursor-pointer">
                                {cluster}
                            </Label>
                        </div>
                    ))}
                </div>
            </div>

            {/* Schema Filter */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 text-primary">
                    <Filter className="h-4 w-4" />
                    <span className="text-[10px] font-black uppercase tracking-widest">Active Schemas</span>
                </div>
                <div className="flex flex-wrap gap-2">
                    {schemas.map((s) => (
                        <Badge
                            key={s}
                            variant="secondary"
                            className="bg-card/40 border-border/40 hover:bg-primary/10 hover:border-primary/20 hover:text-primary cursor-pointer transition-all text-[9px] font-black uppercase tracking-widest py-1"
                        >
                            {s}
                        </Badge>
                    ))}
                </div>
            </div>

            {/* Performance Mode */}
            <div className="mt-8 pt-6 border-t border-border/40">
                <div className="rounded-2xl bg-gradient-to-br from-primary/10 via-accent/5 to-transparent p-4 border border-primary/10">
                    <div className="flex items-center gap-2 text-primary mb-2">
                        <Zap className="h-3.5 w-3.5 fill-current" />
                        <span className="text-[9px] font-black uppercase tracking-widest">Smart Audit</span>
                    </div>
                    <p className="text-[10px] font-medium text-foreground/60 leading-relaxed">
                        Audit mode is currently highlighting documents with &lt; 90% confidence scores.
                    </p>
                </div>
            </div>
        </div>
    )
}
