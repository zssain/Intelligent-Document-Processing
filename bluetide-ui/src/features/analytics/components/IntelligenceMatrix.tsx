import { useAnalytics } from '../context'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/components/ui/badge'

export function IntelligenceMatrix() {
    const { data } = useAnalytics()
    if (!data) return null

    const languages = data.matrix[0].languages

    return (
        <Card className="bg-card/30 backdrop-blur-xl border-border/50 h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-6">
                <div className="space-y-1">
                    <CardTitle className="text-sm font-black uppercase tracking-widest text-foreground">Intelligence Matrix</CardTitle>
                    <p className="text-[10px] font-medium text-muted-foreground/60 tracking-wider uppercase">Accuracy and volume mapping across active schemas</p>
                </div>
                <Badge variant="outline" className="text-[9px] font-black uppercase tracking-widest border-border/50">Live Sync</Badge>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto pb-4">
                    <table className="w-full min-w-[600px] border-separate border-spacing-y-2">
                        <thead>
                            <tr className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40 text-left">
                                <th className="px-4 pb-2">Business Schema</th>
                                {languages.map(lang => (
                                    <th key={lang.code} className="px-4 pb-2 text-center">{lang.label}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {data.matrix.map((row) => (
                                <tr key={row.schema} className="group transition-colors">
                                    <td className="bg-muted/10 rounded-l-xl px-4 py-3 text-xs font-bold whitespace-nowrap border-y border-l border-border/20">
                                        {row.schema}
                                    </td>
                                    {row.languages.map((lang) => (
                                        <td key={lang.code} className="px-2 py-3 bg-muted/5 border-y border-border/10 last:border-r last:rounded-r-xl">
                                            <div className="flex flex-col items-center gap-1.5 min-w-[100px]">
                                                <div className={cn(
                                                    "px-2 py-1 rounded-md text-[11px] font-black border",
                                                    lang.accuracy > 95 ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                                                        lang.accuracy > 90 ? "bg-blue-500/10 text-blue-500 border-blue-500/20" :
                                                            "bg-orange-500/10 text-orange-500 border-orange-500/20"
                                                )}>
                                                    {lang.accuracy}%
                                                </div>
                                                <span className="text-[9px] font-bold text-muted-foreground/40 uppercase tracking-tighter">
                                                    {(lang.volume / 1000).toFixed(1)}k Docs
                                                </span>
                                            </div>
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    )
}
