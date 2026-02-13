import { useAnalytics } from '../context'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { cn } from '@/shared/lib/utils'

export function ExtractionConfidence() {
    const { data } = useAnalytics()
    if (!data) return null

    return (
        <Card className="bg-card/30 backdrop-blur-xl border-border/50 h-full">
            <CardHeader className="pb-8">
                <CardTitle className="text-sm font-black uppercase tracking-widest text-foreground">Confidence Distribution</CardTitle>
                <p className="text-[10px] font-medium text-muted-foreground/60 tracking-wider uppercase">Statistical breakdown of AI certainty across processed tokens</p>
            </CardHeader>
            <CardContent>
                <div className="flex items-end justify-between h-[200px] gap-2 px-2">
                    {data.confidenceDistribution.map((bucket) => (
                        <div key={bucket.range} className="flex-1 flex flex-col items-center gap-3 group">
                            <div className="relative w-full flex flex-col items-center justify-end h-full">
                                <div
                                    className={cn(
                                        "w-full max-w-[40px] rounded-t-lg transition-all duration-500 group-hover:brightness-110 group-hover:shadow-[0_0_20px_rgba(var(--primary),0.2)]",
                                        bucket.percentage > 50 ? "bg-primary" :
                                            bucket.percentage > 10 ? "bg-primary/60" : "bg-primary/20"
                                    )}
                                    style={{ height: `${bucket.percentage}%` }}
                                />
                                <span className="absolute -top-6 text-[10px] font-black text-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                                    {bucket.count}
                                </span>
                            </div>
                            <span className="text-[9px] font-black text-muted-foreground/60 uppercase tracking-tighter whitespace-nowrap">
                                {bucket.range}
                            </span>
                        </div>
                    ))}
                </div>

                <div className="mt-8 grid grid-cols-2 gap-4">
                    <div className="rounded-xl bg-accent/30 p-3 border border-border/50">
                        <p className="text-[9px] font-black uppercase text-muted-foreground/40 mb-1">High Conf Rate</p>
                        <p className="text-lg font-black text-foreground leading-none">87%</p>
                    </div>
                    <div className="rounded-xl bg-emerald-500/5 p-3 border border-emerald-500/10">
                        <p className="text-[9px] font-black uppercase text-emerald-500/40 mb-1">Target</p>
                        <p className="text-lg font-black text-emerald-500 leading-none">95%</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
