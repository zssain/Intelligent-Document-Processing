import { createFileRoute, redirect } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { useState } from 'react'
import { Shield, Search, RefreshCw } from 'lucide-react'

export const Route = createFileRoute('/admin/users')({
  beforeLoad: ({ context }) => {
    const auth = (context as any).auth
    if (!auth || auth.role !== 'org_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminUsers,
})

interface User {
  uid: string
  email: string
  displayName: string
  role: string
  clearanceLevel: number
  allowedCategoryIds: string[]
  isActive: boolean
  createdAt: string
}

interface Category {
  id: string
  name: string
}

function AdminUsers() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      // Mock data - replace with actual API call
      return [
        {
          uid: 'g7MRrHIQyGX7AfmsGcscHwPVuJA2',
          email: 'admin@teclusion.ai',
          displayName: 'Admin User',
          role: 'org_admin',
          clearanceLevel: 3,
          allowedCategoryIds: [],
          isActive: true,
          createdAt: new Date().toISOString(),
        },
        {
          uid: 'q2KvsryTWvU1uhLVrcqCC9XhE4S2',
          email: 'user@teclusion.ai',
          displayName: 'Regular User',
          role: 'user',
          clearanceLevel: 1,
          allowedCategoryIds: ['general'],
          isActive: true,
          createdAt: new Date().toISOString(),
        },
      ]
    },
    refetchInterval: 60000, // Refetch every 60 seconds
  })

  const { data: categories } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: async () => {
      // Mock categories
      return [
        { id: 'general', name: 'General' },
        { id: 'finance', name: 'Finance' },
        { id: 'hr', name: 'Human Resources' },
        { id: 'legal', name: 'Legal' },
      ]
    },
  })

  const updateUserMutation = useMutation({
    mutationFn: async ({
      uid,
      updates,
    }: {
      uid: string
      updates: Partial<User>
    }) => {
      // Replace with actual API call
      await api.patch(`/admin/users/${uid}`, updates)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const filteredUsers = users?.filter(
    (user) =>
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.displayName?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground mt-1">
            Manage user roles, clearance levels, and permissions
          </p>
        </div>
        <button
          onClick={() =>
            queryClient.invalidateQueries({ queryKey: ['admin-users'] })
          }
          className="flex items-center gap-2 px-4 py-2 rounded-md border hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-md border bg-background">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 bg-transparent outline-none text-sm"
        />
      </div>

      {/* User Table */}
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50 border-b">
            <tr>
              <th className="text-left p-3 text-sm font-medium">User</th>
              <th className="text-left p-3 text-sm font-medium">Role</th>
              <th className="text-left p-3 text-sm font-medium">Clearance</th>
              <th className="text-left p-3 text-sm font-medium">Categories</th>
              <th className="text-left p-3 text-sm font-medium">Status</th>
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
            ) : filteredUsers?.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-sm text-muted-foreground">
                  No users found
                </td>
              </tr>
            ) : (
              filteredUsers?.map((user) => (
                <UserRow
                  key={user.uid}
                  user={user}
                  categories={categories || []}
                  onUpdate={(updates) =>
                    updateUserMutation.mutate({ uid: user.uid, updates })
                  }
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

interface UserRowProps {
  user: User
  categories: Category[]
  onUpdate: (updates: Partial<User>) => void
}

function UserRow({ user, categories, onUpdate }: UserRowProps) {
  return (
    <tr className="border-b hover:bg-muted/50">
      <td className="p-3">
        <div>
          <p className="text-sm font-medium">{user.displayName || 'Unknown'}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
      </td>
      <td className="p-3">
        <select
          value={user.role}
          onChange={(e) => onUpdate({ role: e.target.value })}
          className="text-sm px-2 py-1 rounded border bg-background"
        >
          <option value="user">User</option>
          <option value="org_admin">Org Admin</option>
          <option value="analyst">Analyst</option>
        </select>
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2">
          <input
            type="range"
            min="0"
            max="3"
            value={user.clearanceLevel}
            onChange={(e) =>
              onUpdate({ clearanceLevel: parseInt(e.target.value) })
            }
            className="w-24"
          />
          <span className="text-sm font-medium w-4">{user.clearanceLevel}</span>
        </div>
      </td>
      <td className="p-3">
        <select
          multiple
          value={user.allowedCategoryIds}
          onChange={(e) =>
            onUpdate({
              allowedCategoryIds: Array.from(
                e.target.selectedOptions,
                (option) => option.value
              ),
            })
          }
          className="text-xs px-2 py-1 rounded border bg-background max-h-20"
        >
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>
      </td>
      <td className="p-3">
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            user.isActive
              ? 'bg-green-500/10 text-green-500'
              : 'bg-red-500/10 text-red-500'
          }`}
        >
          {user.isActive ? 'Active' : 'Inactive'}
        </span>
      </td>
    </tr>
  )
}
