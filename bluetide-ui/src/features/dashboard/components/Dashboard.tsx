import { useDashboardData } from "../services"
import { StatsCards } from "./StatsCards"
import { AIInsights } from "./AIInsights"
import { SystemStatus } from "./SystemStatus"
import { SearchChatBar } from "./SearchChatBar"
import { Hero } from "@/shared/components/layout/Hero"
import { LayoutDashboard } from "lucide-react"
import { useTranslation } from "react-i18next"

export const Dashboard = () => {
    const { t } = useTranslation()
    const { data, isLoading, error } = useDashboardData()

    if (isLoading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
                <h2 className="text-2xl font-semibold text-destructive">{t('dashboard.error_title')}</h2>
                <p className="text-muted-foreground">{t('dashboard.error_subtitle')}</p>
            </div>
        )
    }

    return (
        <div className="mx-auto max-w-[1400px] space-y-8 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <Hero
                    variant="minimal"
                    title={t('dashboard.intelligence_overview')}
                    subtitle={t('dashboard.real_time_processing')}
                    icon={<LayoutDashboard className="h-6 w-6" />}
                />
                <div className="text-xs font-mono text-muted-foreground bg-card/50 px-3 py-1 rounded-full border border-border/50 uppercase">
                    {t('common.system_status')}: <span className="text-emerald-400">{t('common.optimal')}</span>
                </div>
            </div>

            {/* Stats Section */}
            <StatsCards stats={data.stats} />

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column - Insights */}
                <div className="lg:col-span-2 space-y-6">
                    <AIInsights insights={data.recentAIInsights} />
                </div>

                {/* Right Column - Health & Queries */}
                <div className="space-y-8">
                    <SystemStatus health={data.systemHealth} />
                </div>
            </div>

            {/* Footer / Search Bar */}
            <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6">
                <SearchChatBar />
            </div>

            {/* Spacer for fixed footer */}
            <div className="h-24" />
        </div>
    )
}
