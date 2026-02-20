import { createFileRoute, redirect } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { useState } from 'react'
import { Search, Filter, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'

export const Route = createFileRoute('/admin/audit-log')({
  beforeLoad: ({ context }) => {
    const auth = (context as any).auth
    if (!auth || auth.role !== 'org_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminAuditLog,
})

interface AuditEvent {
  id: string
  eventType: string
  actor: string
  actorUid: string
  resourceType: string
  resourceId: string
  action: string
  details: string
  ipAddress: string
  timestamp: string
}

const EVENT_TYPES = [
  'USER_CREATED',
  'USER_UPDATED',
  'USER_DELETED',
  'DOCUMENT_UPLOADED',
  'DOCUMENT_DELETED',
  'CATEGORY_CREATED',
  'CATEGORY_UPDATED',
  'LOGIN',
  'LOGOUT',
]

function AdminAuditLog() {
  const [page, setPage] = useState(1)
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('')
  const [actorFilter, setActorFilter] = useState('')
  const pageSize = 20

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['audit-log', page, eventTypeFilter, actorFilter],
    queryFn: async () => {
      // Mock data - replace with actual API call
      const mockEvents: AuditEvent[] = Array.from({ length: 50 }, (_, i) => ({
        id: `event-${i}`,
        eventType: EVENT_TYPES[i % EVENT_TYPES.length],
        actor: i % 2 === 0 ? 'admin@teclusion.ai' : 'user@teclusion.ai',
        actorUid: i % 2 === 0 ? 'g7MRrHIQyGX7AfmsGcscHwPVuJA2' : 'q2KvsryTWvU1uhLVrcqCC9XhE4S2',
        resourceType: 'document',
        resourceId: `doc-${i}`,
        action: 'create',
        details: `Performed action ${i}`,
        ipAddress: '192.168.1.1',
        timestamp: new Date(Date.now() - i * 3600000).toISOString(),
      }))

      // Apply filters
      let filtered = mockEvents
      if (eventTypeFilter) {
        filtered = filtered.filter((e) => e.eventType === eventTypeFilter)
      }
      if (actorFilter) {
        filtered = filtered.filter((e) =>
          e.actor.toLowerCase().includes(actorFilter.toLowerCase())
        )
      }

      // Paginate
      const start = (page - 1) * pageSize
      const end = start + pageSize
      const events = filtered.slice(start, end)

      return {
        events,
        total: filtered.length,
        page,
        pageSize,
        totalPages: Math.ceil(filtered.length / pageSize),
      }
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Audit Log</h1>
          <p className="text-muted-foreground mt-1">
            System activity and security events
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 rounded-md border hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md border bg-background">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter by actor email..."
            value={actorFilter}
            onChange={(e) => {
              setActorFilter(e.target.value)
              setPage(1)
            }}
            className="flex-1 bg-transparent outline-none text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={eventTypeFilter}
            onChange={(e) => {
              setEventTypeFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-2 rounded-md border bg-background text-sm"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Events Table */}
      <div className="rounded-lg border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="text-left p-3 text-sm font-medium">Timestamp</th>
                <th className="text-left p-3 text-sm font-medium">Event Type</th>
                <th className="text-left p-3 text-sm font-medium">Actor</th>
                <th className="text-left p-3 text-sm font-medium">Details</th>
                <th className="text-left p-3 text-sm font-medium">IP Address</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    </div>
                  </td>
                </tr>
              ) : data?.events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-sm text-muted-foreground">
                    No audit events found
                  </td>
                </tr>
              ) : (
                data?.events.map((event) => (
                  <tr key={event.id} className="border-b hover:bg-muted/50">
                    <td className="p-3 text-xs">
                      {new Date(event.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium">
                        {event.eventType}
                      </span>
                    </td>
                    <td className="p-3 text-sm">{event.actor}</td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {event.details}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {event.ipAddress}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {data && data.totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * pageSize + 1} to{' '}
            {Math.min(page * pageSize, data.total)} of {data.total} events
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-md border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, data.totalPages) }, (_, i) => {
                const pageNum = i + 1
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`px-3 py-1 rounded-md text-sm ${
                      page === pageNum
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-accent'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>
            <button
              onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
              disabled={page === data.totalPages}
              className="p-2 rounded-md border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
