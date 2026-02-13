import { AnalyticsProvider, useAnalytics } from './context'
import { SmartMetricCards } from './components/SmartMetricCards'
import { IntelligenceMatrix } from './components/IntelligenceMatrix'
import { ExtractionConfidence } from './components/ExtractionConfidence'
import { LiveProcessingQueue } from './components/LiveProcessingQueue'
import { SidebarFilters } from './components/SidebarFilters'

export const Analytics = {
    Root: AnalyticsProvider,
    Metrics: SmartMetricCards,
    Matrix: IntelligenceMatrix,
    Confidence: ExtractionConfidence,
    Queue: LiveProcessingQueue,
    Sidebar: SidebarFilters,
    useAnalytics,
}
