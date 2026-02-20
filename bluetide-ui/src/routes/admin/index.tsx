import { createFileRoute, redirect } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useQuery } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { Users, FileText, Activity, Shield } from 'lucide-react'

export const Route = createFileRoute('/admin/')({
  beforeLoad: ({ context }) => {
    const auth = (context as any).auth
    if (!auth || auth.role !== 'org_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminOverview,
})

interface AdminStats {
  userCount: number
  documentCount: number
  recentEvents: Array<{
    id: string
    eventType: string
    actor: string
    timestamp: string
    details: string
  }>
}

function AdminOverview() {
  const { email, role, clearance } = useAuth()

  const { data: stats, isLoading } = useQuery<AdminStats>({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      // Mock data for now - replace with actual API call
      return {
        userCount: 12,
        documentCount: 245,
        recentEvents: [
          {
            id: '1',
            eventType: 'USER_CREATED',
            actor: 'admin@teclusion.ai',
            timestamp: new Date().toISOString(),
            details: 'Created user user@teclusion.ai',
          },
          {
            id: '2',
            eventType: 'DOCUMENT_UPLOADED',
            actor: 'user@teclusion.ai',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            details: 'Uploaded financial_report.pdf',
          },
        ],
      }
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          System overview and recent activity
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Users className="h-5 w-5" />}
          label="Total Users"
          value={stats?.userCount || 0}
          bgColor="bg-blue-500/10"
          iconColor="text-blue-500"
        />
        <StatCard
          icon={<FileText className="h-5 w-5" />}
          label="Total Documents"
          value={stats?.documentCount || 0}
          bgColor="bg-green-500/10"
          iconColor="text-green-500"
        />
        <StatCard
          icon={<Activity className="h-5 w-5" />}
          label="Recent Events"
          value={stats?.recentEvents.length || 0}
          bgColor="bg-orange-500/10"
          iconColor="text-orange-500"
        />
        <StatCard
          icon={<Shield className="h-5 w-5" />}
          label="Your Clearance"
          value={clearance || 0}
          bgColor="bg-purple-500/10"
          iconColor="text-purple-500"
        />
      </div>

      {/* Recent Activity */}
      <div className="rounded-lg border bg-card">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Recent Audit Events</h2>
        </div>
        <div className="p-4">
          {stats?.recentEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No recent events
            </p>
          ) : (
            <div className="space-y-3">
              {stats?.recentEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 p-3 rounded-md bg-muted/50"
                >
                  <Activity className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                        {event.eventType}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm mt-1">{event.details}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      by {event.actor}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  bgColor: string
  iconColor: string
}

function StatCard({ icon, label, value, bgColor, iconColor }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className={`p-2 rounded-md ${bgColor}`}>
          <div className={iconColor}>{icon}</div>
        </div>
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-sm text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}
