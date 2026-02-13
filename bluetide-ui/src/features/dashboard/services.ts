import { useQuery } from '@tanstack/react-query'
import type { DashboardData } from './types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/** Silent health probe – never throws, never logs to console */
async function silentProbe(url: string): Promise<{ ok: boolean }> {
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 5000)
        const res = await fetch(url, { signal: controller.signal })
        clearTimeout(timeout)
        // Consume the body so the browser doesn't flag it as an unhandled error response
        await res.text().catch(() => {})
        return { ok: res.ok }
    } catch {
        return { ok: false }
    }
}

export const useDashboardData = () => {
    return useQuery<DashboardData>({
        queryKey: ['dashboard-data'],
        queryFn: async () => {
            // 1. Fetch real stats and health in parallel
            const [statsRes, healthRes, mockRes, s3Probe, spProbe, gdProbe] = await Promise.all([
                fetch(`${API_BASE_URL}/dashboard/stats`).then(r => r.json()),
                fetch(`${API_BASE_URL}/health`).then(r => r.json()),
                fetch('/data/dashboard-mock.json').then(r => r.json()),
                silentProbe(`${API_BASE_URL}/datalake/s3/list?limit=1`),
                silentProbe(`${API_BASE_URL}/datalake/sharepoint/list?limit=1`),
                silentProbe(`${API_BASE_URL}/datalake/gdrive/list?limit=1`),
            ])

            return {
                ...mockRes,
                stats: {
                    ...mockRes.stats,
                    totalIntelligenceBase: {
                        value: statsRes.total_documents,
                        docsToday: statsRes.documents_today,
                        docsThisWeek: statsRes.documents_this_week,
                        label: 'Total Intelligence Base'
                    },
                    knowledgeFragments: {
                        total: statsRes.total_chunks || 0,
                        growth: '+12% this week' // Mocked growth for now
                    },
                    intelligenceEntities: {
                        total: statsRes.unique_entities || 0,
                        label: 'Unique Entities'
                    }
                },
                systemHealth: {
                    ...mockRes.systemHealth,
                    connectors: [
                        { name: 'Vector Database', status: healthRes.database === 'healthy' ? 'active' : 'failed' },
                        { name: 'S3 Datalake', status: s3Probe.ok ? 'active' : 'idle' },
                        { name: 'SharePoint', status: spProbe.ok ? 'active' : 'idle' },
                        { name: 'Google Drive', status: gdProbe.ok ? 'active' : 'idle' },
                    ]
                }
            }
        },
    })
}
