import { useAnalytics } from '../context'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { cn } from '@/shared/lib/utils'
import {
    CheckCircle2,
    AlertCircle,
    XCircle,
    Clock,
    ArrowUpRight,
    Search
} from 'lucide-react'

export function LiveProcessingQueue() {
    const { data } = useAnalytics()
    if (!data) return null

    return (
        <Card className="bg-card/30 backdrop-blur-xl border-border/50 h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-6">
                <div className="space-y-1">
                    <CardTitle className="text-sm font-black uppercase tracking-widest text-foreground">Operational Log</CardTitle>
                    <p className="text-[10px] font-medium text-muted-foreground/60 tracking-wider uppercase">Real-time status of document extraction sequences</p>
                </div>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/50 text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <Search className="h-4 w-4" />
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {data.activity.map((item) => (
                        <div
                            key={item.id}
                            className="group flex flex-col gap-3 rounded-2xl border border-border/20 bg-muted/5 p-4 transition-all hover:bg-muted/10 hover:border-primary/20"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={cn(
                                        "flex h-9 w-9 items-center justify-center rounded-xl transition-colors",
                                        item.status === 'success' ? "bg-emerald-500/10 text-emerald-500" :
                                            item.status === 'warning' ? "bg-orange-500/10 text-orange-500" :
                                                item.status === 'error' ? "bg-red-500/10 text-red-500" :
                                                    "bg-blue-500/10 text-blue-500"
                                    )}>
                                        {item.status === 'success' ? <CheckCircle2 className="h-5 w-5" /> :
                                            item.status === 'warning' ? <AlertCircle className="h-5 w-5" /> :
                                                item.status === 'error' ? <XCircle className="h-5 w-5" /> :
                                                    <Clock className="h-5 w-5" />}
                                    </div>
                                    <div className="space-y-0.5">
                                        <div className="flex items-center gap-2">
                                            <p className="text-xs font-black tracking-tight">{item.docId}</p>
                                            <span className="text-[10px] font-bold text-muted-foreground/40 tabular-nums">{item.timestamp}</span>
                                        </div>
                                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                            {item.type} • {item.language} • {item.confidence}% Conf.
                                        </p>
                                    </div>
                                </div>
                                <button className="opacity-0 group-hover:opacity-100 h-7 w-7 flex items-center justify-center rounded-lg bg-primary/10 text-primary transition-all active:scale-90">
                                    <ArrowUpRight className="h-4 w-4" />
                                </button>
                            </div>

                            <p className="text-[11px] font-medium text-muted-foreground/80 leading-relaxed px-1">
                                {item.message}
                            </p>
                        </div>
                    ))}
                </div>

                <button className="mt-6 w-full flex items-center justify-center py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest text-muted-foreground/40 border border-dashed border-border/50 hover:border-primary/30 hover:text-primary transition-all">
                    View Full System Audit
                </button>
            </CardContent>
        </Card>
    )
}
