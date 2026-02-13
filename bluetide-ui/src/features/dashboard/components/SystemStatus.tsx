import type { SystemHealth } from "../types"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Progress } from "@/shared/components/ui/progress"
import { Database, Activity } from "lucide-react"
import { cn } from "@/shared/lib/utils"

interface SystemStatusProps {
    health: SystemHealth
}

export const SystemStatus = ({ health }: SystemStatusProps) => {
    return (
        <div className="space-y-8">
            {/* System Health */}
            <Card className="bg-card/40 border-border/50 backdrop-blur-sm">
                <CardHeader className="pb-4">
                    <CardTitle className="text-sm font-bold uppercase tracking-widest flex items-center gap-2">
                        <Activity className="h-4 w-4 text-primary" />
                        System Health
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-4">
                        {health.connectors.map((connector) => (
                            <div key={connector.name} className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-1.5 rounded-md bg-muted/50">
                                        <Database className="h-4 w-4 text-emerald-400" />
                                    </div>
                                    <span className="text-sm font-medium">{connector.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={cn(
                                        "text-[10px] font-bold uppercase",
                                        connector.status === 'active' ? "text-emerald-400" : "text-muted-foreground"
                                    )}>
                                        {connector.status}
                                    </span>
                                    <div className={cn(
                                        "h-1.5 w-1.5 rounded-full",
                                        connector.status === 'active' ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-muted-foreground/30"
                                    )} />
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="pt-4 border-t border-border/30 space-y-3">
                        <div className="flex justify-between text-[10px] font-mono uppercase tracking-tight text-muted-foreground">
                            <span>Vector DB Latency</span>
                            <span className="text-emerald-400">{health.vectorDbLatency}ms</span>
                        </div>
                        <Progress value={health.vectorDbLatency * 2} className="h-1.5 bg-emerald-500/10" />
                    </div>
                </CardContent>
            </Card>

        </div>
    )
}
