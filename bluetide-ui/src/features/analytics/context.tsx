import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { AnalyticsData, AnalyticsFilters } from './types'

interface AnalyticsContextValue {
    data: AnalyticsData | undefined
    isLoading: boolean
    filters: AnalyticsFilters
    setFilters: (filters: Partial<AnalyticsFilters>) => void
}

const AnalyticsContext = createContext<AnalyticsContextValue | undefined>(undefined)

export function AnalyticsProvider({ children }: { children: ReactNode }) {
    const [filters, setFiltersState] = useState<AnalyticsFilters>({
        timeRange: 'Last 30 Days',
        segments: ['All Regions'],
        docTypes: ['Invoices', 'Contracts']
    })

    const { data, isLoading } = useQuery<AnalyticsData>({
        queryKey: ['analytics-data', filters],
        queryFn: async () => {
            const response = await fetch('/data/analytics-mock.json')
            if (!response.ok) throw new Error('Failed to fetch analytics data')
            return response.json()
        }
    })

    const setFilters = (newFilters: Partial<AnalyticsFilters>) => {
        setFiltersState(prev => ({ ...prev, ...newFilters }))
    }

    return (
        <AnalyticsContext.Provider value={{ data, isLoading, filters, setFilters }}>
            {children}
        </AnalyticsContext.Provider>
    )
}

export function useAnalytics() {
    const context = useContext(AnalyticsContext)
    if (!context) throw new Error('useAnalytics must be used within AnalyticsProvider')
    return context
}
