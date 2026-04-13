import { createFileRoute, redirect, Link } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useQuery } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { Users, FileText, Activity, Shield, ArrowRight, Database } from 'lucide-react'
import { auth as firebaseAuth } from '@/shared/lib/firebase'

export const Route = createFileRoute('/admin/')({
  beforeLoad: async () => {
    const user = firebaseAuth.currentUser
    if (!user) {
      throw redirect({ to: '/login' })
    }
    const tokenResult = await user.getIdTokenResult()
    const role = tokenResult.claims.role as string | undefined
    if (role !== 'org_admin') {
      throw redirect({ to: '/documents' })
    }
  },
  component: AdminOverview,
})

// Types matching the backend API responses
interface DashboardStats {
  total_documents: number
  documents_today: number
  documents_this_week: number
  total_chunks: number
  unique_entities: number
  connected_files: number
  system_status: string
}

interface UserData {
  uid: string
  email: string
  display_name: string
  role: string
  clearance_level: number
  is_active: boolean
}

interface AuditEvent {
  id: string
  event_type: string
  actor_email?: string
  actor_uid?: string
  entity_type: string
  entity_id: string
  before?: Record<string, any>
  after?: Record<string, any>
  created_at: string
}

function AdminOverview() {
  const { clearance } = useAuth()

  // Fetch real dashboard stats
  const { data: dashStats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('dashboard/stats')
      return data
    },
    refetchInterval: 30000,
  })

  // Fetch real user count
  const { data: usersResp, isLoading: usersLoading } = useQuery<{ users: UserData[] }>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await api.get<{ users: UserData[] }>('admin/users')
      return data
    },
    refetchInterval: 60000,
  })

  // Fetch real audit log
  const { data: auditResp, isLoading: auditLoading } = useQuery<{ events: AuditEvent[] }>({
    queryKey: ['admin-audit-recent'],
    queryFn: async () => {
      const { data } = await api.get<{ events: AuditEvent[] }>('admin/audit-log', {
        params: { limit: 10, offset: 0 },
      })
      return data
    },
    refetchInterval: 30000,
  })

  const isLoading = statsLoading || usersLoading || auditLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  const userCount = usersResp?.users?.length || 0
  const docCount = dashStats?.total_documents || 0
  const chunkCount = dashStats?.total_chunks || 0
  const connectedFiles = dashStats?.connected_files || 0
  const auditEvents = auditResp?.events || []

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
          value={userCount}
          bgColor="bg-blue-500/10"
          iconColor="text-blue-500"
        />
        <StatCard
          icon={<FileText className="h-5 w-5" />}
          label="Total Documents"
          value={docCount}
          bgColor="bg-green-500/10"
          iconColor="text-green-500"
        />
        <StatCard
          icon={<Database className="h-5 w-5" />}
          label="Total Chunks"
          value={chunkCount}
          bgColor="bg-orange-500/10"
          iconColor="text-orange-500"
        />
        <StatCard
          icon={<Shield className="h-5 w-5" />}
          label="Connected Files"
          value={connectedFiles}
          bgColor="bg-purple-500/10"
          iconColor="text-purple-500"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/admin/users"
          className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-blue-500/10">
              <Users className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="font-semibold">Manage Users</p>
              <p className="text-xs text-muted-foreground">Roles, permissions & access</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
        <Link
          to="/admin/categories"
          className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-green-500/10">
              <FileText className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="font-semibold">Categories</p>
              <p className="text-xs text-muted-foreground">Organize documents</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
        <Link
          to="/admin/audit-log"
          className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-orange-500/10">
              <Activity className="h-5 w-5 text-orange-500" />
            </div>
            <div>
              <p className="font-semibold">Audit Log</p>
              <p className="text-xs text-muted-foreground">Security & activity trail</p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="rounded-lg border bg-card">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Audit Events</h2>
          <Link to="/admin/audit-log" className="text-xs text-primary hover:underline">
            View All →
          </Link>
        </div>
        <div className="p-4">
          {auditEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No audit events recorded yet
            </p>
          ) : (
            <div className="space-y-3">
              {auditEvents.map((event, idx) => (
                <div
                  key={event.id || idx}
                  className="flex items-start gap-3 p-3 rounded-md bg-muted/50"
                >
                  <Activity className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                        {event.event_type}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm mt-1">
                      {event.entity_type}: {event.entity_id}
                    </p>
                    {event.actor_email && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        by {event.actor_email}
                      </p>
                    )}
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
