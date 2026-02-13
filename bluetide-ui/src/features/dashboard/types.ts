export interface DashboardStats {
    totalIntelligenceBase: {
        value: number
        docsToday: number
        docsThisWeek: number
        label: string
    }
    knowledgeFragments: {
        total: number
        growth: string
    }
    intelligenceEntities: {
        total: number
        label: string
    }
}

export interface AIInsight {
    id: string
    type: 'pattern' | 'anomaly'
    title: string
    timestamp: string
    pipeline: string
    content: string
    status: string
    actions: string[]
}

export interface SystemHealth {
    connectors: Array<{
        name: string
        status: 'active' | 'idle' | 'failed'
    }>
    vectorDbLatency: number
}

export interface DashboardData {
    stats: DashboardStats
    recentAIInsights: AIInsight[]
    systemHealth: SystemHealth
}

// Dummy constant to ensure this is treated as a module with runtime exports if needed
export const DASHBOARD_SCHEMA_VERSION = "1.0.0";
