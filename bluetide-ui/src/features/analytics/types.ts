export interface SmartMetric {
    label: string
    value: string | number
    unit?: string
    change: number
    trend: 'up' | 'down' | 'stable'
    sparkline: number[]
}

export interface IntelligenceMatrixRow {
    schema: string
    languages: {
        code: string
        label: string
        accuracy: number
        latency: number
        volume: number
    }[]
}

export interface ConfidenceBucket {
    range: string
    count: number
    percentage: number
}

export interface ActivityItem {
    id: string
    timestamp: string
    docId: string
    type: string
    language: string
    confidence: number
    status: 'success' | 'warning' | 'error' | 'processing'
    message: string
}

export interface SmartInsight {
    id: string
    type: 'positive' | 'negative' | 'neutral'
    text: string
    timestamp: string
}

export interface AnalyticsData {
    metrics: SmartMetric[]
    matrix: IntelligenceMatrixRow[]
    confidenceDistribution: ConfidenceBucket[]
    activity: ActivityItem[]
    insights: SmartInsight[]
}

export type TimeRange = 'Last 24 Hours' | 'Last 7 Days' | 'Last 30 Days' | 'Last 90 Days'

export interface AnalyticsFilters {
    timeRange: TimeRange
    segments: string[]
    docTypes: string[]
}

export const ANALYTICS_SCHEMA_VERSION = "2.0.0"
