import { createFileRoute, redirect } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { useState, useCallback } from 'react'
import {
  Shield,
  Search,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Database,
  Cloud,
  HardDrive,
  Upload,
  Check,
  X,
  Loader2,
  Save,
  Users,
} from 'lucide-react'
import { auth as firebaseAuth } from '@/shared/lib/firebase'

export const Route = createFileRoute('/admin/users')({
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
  component: AdminUsers,
})

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface SourceActionPerms {
  can_view: boolean
  can_download: boolean
  can_filter: boolean
  can_sync: boolean
  can_preview: boolean
}

interface UserData {
  uid: string
  email: string
  display_name: string
  role: string
  clearance_level: number
  allowed_category_ids: string[]
  source_permissions: Record<string, SourceActionPerms>
  is_active: boolean
  created_at: string
}

interface Category {
  id: string
  name: string
}

// Source metadata for rendering
const SOURCES = [
  { key: 's3', label: 'Amazon S3', icon: Database, color: '#ff9900' },
  { key: 'gdrive', label: 'Google Drive', icon: Cloud, color: '#4285f4' },
  { key: 'sharepoint', label: 'SharePoint', icon: HardDrive, color: '#0078d4' },
  { key: 'direct_upload', label: 'Direct Upload', icon: Upload, color: '#10b981' },
] as const

const ACTIONS = [
  { key: 'can_view', label: 'View' },
  { key: 'can_download', label: 'Download' },
  { key: 'can_filter', label: 'Filter' },
  { key: 'can_sync', label: 'Sync' },
  { key: 'can_preview', label: 'Preview' },
] as const

const DEFAULT_SOURCE_PERMS: SourceActionPerms = {
  can_view: false,
  can_download: false,
  can_filter: false,
  can_sync: false,
  can_preview: false,
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
function AdminUsers() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch real users from API
  const { data: usersResp, isLoading } = useQuery<{ users: UserData[] }>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await api.get('/admin/users')
      return data
    },
    refetchInterval: 60_000,
  })

  // Fetch categories
  const { data: catsResp } = useQuery<{ categories: Category[] }>({
    queryKey: ['admin-categories'],
    queryFn: async () => {
      const { data } = await api.get('/admin/categories')
      return data
    },
  })

  const users = usersResp?.users ?? []
  const categories = catsResp?.categories ?? []

  const filteredUsers = users.filter(
    (u) =>
      u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.display_name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
            <p className="text-sm text-muted-foreground">
              Manage roles, clearance levels, categories & source permissions
            </p>
          </div>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['admin-users'] })}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border/60 hover:bg-accent/60 transition-colors text-sm font-medium"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Search bar */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border border-border/60 bg-card shadow-sm">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search users by name or email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground/60"
        />
        {searchQuery && (
          <button onClick={() => setSearchQuery('')} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Users list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground text-sm">
          {searchQuery ? 'No users match your search' : 'No users found'}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredUsers.map((user) => (
            <UserCard
              key={user.uid}
              user={user}
              categories={categories}
              queryClient={queryClient}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// User Card Component
// ---------------------------------------------------------------------------
interface UserCardProps {
  user: UserData
  categories: Category[]
  queryClient: ReturnType<typeof useQueryClient>
}

function UserCard({ user, categories, queryClient }: UserCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [localPerms, setLocalPerms] = useState<Record<string, SourceActionPerms>>(
    () => user.source_permissions || {}
  )
  const [dirty, setDirty] = useState(false)

  // ---- Mutations ----
  const roleMutation = useMutation({
    mutationFn: async (role: string) => {
      await api.post(`/admin/users/${user.uid}/role`, { role })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const clearanceMutation = useMutation({
    mutationFn: async (clearance_level: number) => {
      await api.put(`/admin/users/${user.uid}/clearance`, { clearance_level })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const catMutation = useMutation({
    mutationFn: async (allowed_category_ids: string[]) => {
      await api.put(`/admin/users/${user.uid}/categories`, { allowed_category_ids })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const permsMutation = useMutation({
    mutationFn: async (source_permissions: Record<string, SourceActionPerms>) => {
      await api.put(`/admin/users/${user.uid}/source-permissions`, { source_permissions })
    },
    onSuccess: () => {
      setDirty(false)
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const togglePerm = useCallback(
    (source: string, action: keyof SourceActionPerms) => {
      setLocalPerms((prev) => {
        const curr = prev[source] || { ...DEFAULT_SOURCE_PERMS }
        return {
          ...prev,
          [source]: { ...curr, [action]: !curr[action] },
        }
      })
      setDirty(true)
    },
    []
  )

  const toggleAllForSource = useCallback(
    (source: string, value: boolean) => {
      setLocalPerms((prev) => ({
        ...prev,
        [source]: {
          can_view: value,
          can_download: value,
          can_filter: value,
          can_sync: value,
          can_preview: value,
        },
      }))
      setDirty(true)
    },
    []
  )

  const isAdmin = user.role === 'org_admin'

  return (
    <div className="rounded-xl border border-border/60 bg-card shadow-sm overflow-hidden transition-all">
      {/* Collapsed Header Row */}
      <div
        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-accent/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand chevron */}
        <div className="text-muted-foreground">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>

        {/* Avatar */}
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
          {(user.display_name || user.email || '?')[0].toUpperCase()}
        </div>

        {/* Name + email */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{user.display_name || 'Unknown'}</p>
          <p className="text-xs text-muted-foreground truncate">{user.email}</p>
        </div>

        {/* Role pill */}
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${isAdmin
            ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
            : 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
            }`}
        >
          {user.role}
        </span>

        {/* Clearance badge */}
        <span className="text-xs px-2 py-1 rounded-md bg-muted font-mono shrink-0">
          CL {user.clearance_level}
        </span>

        {/* Active status */}
        <span
          className={`text-xs px-2.5 py-1 rounded-full shrink-0 ${user.is_active
            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
            : 'bg-red-500/15 text-red-600 dark:text-red-400'
            }`}
        >
          {user.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>

      {/* Expanded Panel */}
      {expanded && (
        <div className="border-t border-border/40 bg-muted/20 px-5 py-5 space-y-6">
          {/* Row 1: Role + Clearance + Categories */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Role */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Role</label>
              <select
                value={user.role}
                onChange={(e) => roleMutation.mutate(e.target.value)}
                disabled={roleMutation.isPending}
                className="w-full text-sm px-3 py-2 rounded-lg border border-border/60 bg-background focus:ring-2 focus:ring-indigo-500/40 focus:outline-none transition-all"
              >
                <option value="user">User</option>
                <option value="org_admin">Org Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>

            {/* Clearance */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Clearance Level
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={user.clearance_level}
                  onChange={(e) => clearanceMutation.mutate(parseInt(e.target.value))}
                  disabled={clearanceMutation.isPending}
                  className="flex-1 accent-indigo-500"
                />
                <span className="text-sm font-bold w-6 text-center">{user.clearance_level}</span>
              </div>
            </div>

            {/* Categories */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Categories
              </label>
              <select
                multiple
                value={user.allowed_category_ids || []}
                onChange={(e) =>
                  catMutation.mutate(
                    Array.from(e.target.selectedOptions, (o) => o.value)
                  )
                }
                disabled={catMutation.isPending}
                className="w-full text-xs px-3 py-2 rounded-lg border border-border/60 bg-background max-h-20 focus:ring-2 focus:ring-indigo-500/40 focus:outline-none"
              >
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Source Permissions */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-indigo-500" />
                <h3 className="text-sm font-semibold">Source Permissions</h3>
              </div>
              {dirty && (
                <button
                  onClick={() => permsMutation.mutate(localPerms)}
                  disabled={permsMutation.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {permsMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Save className="h-3 w-3" />
                  )}
                  Save Permissions
                </button>
              )}
            </div>

            {isAdmin && (
              <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 px-3 py-2 rounded-lg">
                ⚡ Org admins have full access to all sources and actions.
              </p>
            )}

            {/* Permission grid */}
            <div className="rounded-lg border border-border/40 overflow-hidden">
              {/* Header */}
              <div className="grid grid-cols-[200px_repeat(5,1fr)_80px] bg-muted/60 px-4 py-2.5 gap-2">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Source</div>
                {ACTIONS.map((a) => (
                  <div key={a.key} className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-center">
                    {a.label}
                  </div>
                ))}
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-center">All</div>
              </div>

              {/* Source rows */}
              {SOURCES.map((src) => {
                const perms = localPerms[src.key] || { ...DEFAULT_SOURCE_PERMS }
                const allOn = ACTIONS.every((a) => perms[a.key])
                const Icon = src.icon

                return (
                  <div
                    key={src.key}
                    className="grid grid-cols-[200px_repeat(5,1fr)_80px] px-4 py-3 gap-2 border-t border-border/30 hover:bg-accent/20 transition-colors items-center"
                  >
                    {/* Source name */}
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${src.color}20` }}
                      >
                        <Icon className="h-3.5 w-3.5" style={{ color: src.color }} />
                      </div>
                      <span className="text-sm font-medium">{src.label}</span>
                    </div>

                    {/* Action toggles */}
                    {ACTIONS.map((action) => (
                      <div key={action.key} className="flex justify-center">
                        <ToggleSwitch
                          checked={isAdmin ? true : perms[action.key]}
                          onChange={() => togglePerm(src.key, action.key)}
                          disabled={isAdmin}
                        />
                      </div>
                    ))}

                    {/* All toggle */}
                    <div className="flex justify-center">
                      <ToggleSwitch
                        checked={isAdmin ? true : allOn}
                        onChange={() => toggleAllForSource(src.key, !allOn)}
                        disabled={isAdmin}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Toggle Switch
// ---------------------------------------------------------------------------
interface ToggleSwitchProps {
  checked: boolean
  onChange: () => void
  disabled?: boolean
}

function ToggleSwitch({ checked, onChange, disabled }: ToggleSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
      className={`
        relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors 
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500
        ${disabled ? 'opacity-60 cursor-not-allowed' : ''}
        ${checked ? 'bg-indigo-600' : 'bg-zinc-300 dark:bg-zinc-700'}
      `}
    >
      <span
        className={`
          pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition-transform
          ${checked ? 'translate-x-4' : 'translate-x-0'}
        `}
      />
    </button>
  )
}
