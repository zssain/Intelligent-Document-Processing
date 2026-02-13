import type { DashboardStats } from "../types"
import { Card, CardContent } from "@/shared/components/ui/card"
import { Folder, Settings, Zap, ArrowUpRight } from "lucide-react"
import { useTranslation } from "react-i18next"

interface StatsCardsProps {
    stats: DashboardStats
}

export const StatsCards = ({ stats }: StatsCardsProps) => {
    const { t } = useTranslation()
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total Intelligence Base */}
            <Card className="bg-card/40 border-border/50 backdrop-blur-sm relative overflow-hidden group">
                <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                        <div className="space-y-2">
                            <p className="text-sm font-medium text-muted-foreground">{t('dashboard.stats.total_documents')}</p>
                            <div className="flex flex-col gap-1">
                                <div className="flex items-baseline gap-2">
                                    <h2 className="text-3xl font-bold tracking-tight">
                                        {stats.totalIntelligenceBase.value.toLocaleString()}
                                    </h2>
                                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
                                        +{stats.totalIntelligenceBase.docsToday.toLocaleString()} {t('dashboard.stats.today')}
                                    </span>
                                </div>
                                <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                                    {stats.totalIntelligenceBase.docsThisWeek.toLocaleString()} {t('dashboard.stats.ingested_this_week')}
                                </p>
                            </div>
                        </div>
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Folder className="h-5 w-5" />
                        </div>
                    </div>
                    <div className="absolute top-0 right-0 p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <ArrowUpRight className="h-4 w-4 text-muted-foreground/30" />
                    </div>
                </CardContent>
            </Card>

            {/* Knowledge Fragments (replacing Active Pipelines) */}
            <Card className="bg-card/40 border-border/50 backdrop-blur-sm relative overflow-hidden group">
                <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                        <div className="space-y-2">
                            <p className="text-sm font-medium text-muted-foreground">{t('dashboard.stats.knowledge_fragments')}</p>
                            <div className="flex items-baseline gap-2">
                                <h2 className="text-3xl font-bold tracking-tight">
                                    {stats.knowledgeFragments.total.toLocaleString()}
                                </h2>
                                <span className="text-xs font-medium text-blue-400">
                                    {stats.knowledgeFragments.growth}
                                </span>
                            </div>
                            <p className="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                {t('dashboard.stats.semantic_chunks')}
                            </p>
                        </div>
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Zap className="h-5 w-5" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Intelligence Entities (replacing Compute Savings) */}
            <Card className="bg-card/40 border-border/50 backdrop-blur-sm relative overflow-hidden group">
                <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                        <div className="space-y-2">
                            <p className="text-sm font-medium text-muted-foreground">{t('dashboard.stats.intelligence_entities')}</p>
                            <div className="flex items-baseline gap-2">
                                <h2 className="text-3xl font-bold tracking-tight text-emerald-400">
                                    {stats.intelligenceEntities.total}
                                </h2>
                                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
                                    {stats.intelligenceEntities.label}
                                </span>
                            </div>
                            <p className="text-[10px] text-muted-foreground">
                                ↳ {t('dashboard.stats.extracted_across')}
                            </p>
                        </div>
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Settings className="h-5 w-5" />
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
