import { useQuery } from '@tanstack/react-query'
import type { DashboardData } from './types'
import api from '@/shared/lib/api'

/** Silent health probe – never throws, never logs to console.
 *  Also detects connectors that respond 200 but include a _note field
 *  indicating they are not actually configured. */
async function silentProbe(url: string): Promise<{ ok: boolean }> {
    try {
        const res = await api.get(url, { timeout: 5000 })
        // If the backend returns a _note field, the connector is not configured
        if (res.data?._note) {
            return { ok: false }
        }
        return { ok: true }
    } catch {
        return { ok: false }
    }
}

export const useDashboardData = () => {
    return useQuery<DashboardData>({
        queryKey: ['dashboard-data'],
        queryFn: async () => {
            // 1. Fetch real stats and health in parallel (using authenticated api)
            const [statsRes, healthRes, mockRes, s3Probe, spProbe, gdProbe] = await Promise.all([
                api.get('dashboard/stats').then(r => r.data),
                api.get('../health').then(r => r.data).catch(() => ({ database: 'unhealthy' })),
                fetch('/data/dashboard-mock.json').then(r => r.json()),
                silentProbe('datalake/s3/list?limit=1'),
                silentProbe('datalake/sharepoint/list?limit=1'),
                silentProbe('datalake/gdrive/list?limit=1'),
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
