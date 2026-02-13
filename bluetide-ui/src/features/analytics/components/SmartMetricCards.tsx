import { useAnalytics } from '../context'
import { Card, CardContent } from '@/shared/components/ui/card'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

export function SmartMetricCards() {
    const { data } = useAnalytics()
    if (!data) return null

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {data.metrics.map((metric) => (
                <Card key={metric.label} className="bg-card/30 backdrop-blur-xl border-border/50 transition-all hover:border-primary/30 group">
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">{metric.label}</span>
                            <div className={cn(
                                "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold",
                                metric.trend === 'up' ? "bg-emerald-500/10 text-emerald-500" :
                                    metric.trend === 'down' ? "bg-red-500/10 text-red-500" :
                                        "bg-muted/50 text-muted-foreground"
                            )}>
                                {metric.trend === 'up' ? <TrendingUp className="h-3 w-3" /> :
                                    metric.trend === 'down' ? <TrendingDown className="h-3 w-3" /> :
                                        <Minus className="h-3 w-3" />}
                                {Math.abs(metric.change)}{metric.label.includes('Rate') ? '%' : ''}
                            </div>
                        </div>

                        <div className="flex items-baseline gap-1.5">
                            <span className="text-3xl font-black tracking-tighter text-foreground leading-none">
                                {metric.value}
                            </span>
                            {metric.unit && (
                                <span className="text-xs font-bold text-muted-foreground/60 uppercase tracking-widest leading-none">
                                    {metric.unit}
                                </span>
                            )}
                        </div>

                        {/* Sparkline Visual */}
                        <div className="mt-6 flex items-end gap-1 h-8 opacity-40 group-hover:opacity-100 transition-opacity">
                            {metric.sparkline.map((val, i) => {
                                const max = Math.max(...metric.sparkline)
                                const min = Math.min(...metric.sparkline)
                                const norm = max === min ? 50 : ((val - min) / (max - min)) * 100
                                return (
                                    <div
                                        key={i}
                                        className={cn(
                                            "flex-1 rounded-t-[1px] transition-all",
                                            metric.trend === 'up' ? "bg-emerald-500" : "bg-primary"
                                        )}
                                        style={{ height: `${Math.max(norm, 10)}%` }}
                                    />
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    )
}
