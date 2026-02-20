import { createFileRoute, redirect } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { useState } from 'react'
import { Plus, Pencil, Trash2, RefreshCw } from 'lucide-react'

export const Route = createFileRoute('/admin/categories')({
  beforeLoad: ({ context }) => {
    const auth = (context as any).auth
    if (!auth || auth.role !== 'org_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminCategories,
})

interface Category {
  id: string
  name: string
  description: string
  color: string
  createdAt: string
}

function AdminCategories() {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const { data: categories, isLoading } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: async () => {
      // Mock data - replace with actual API call
      return [
        {
          id: 'general',
          name: 'General',
          description: 'General documents accessible to all users',
          color: '#3b82f6',
          createdAt: new Date().toISOString(),
        },
        {
          id: 'finance',
          name: 'Finance',
          description: 'Financial documents and reports',
          color: '#10b981',
          createdAt: new Date().toISOString(),
        },
        {
          id: 'hr',
          name: 'Human Resources',
          description: 'HR and employee-related documents',
          color: '#f59e0b',
          createdAt: new Date().toISOString(),
        },
        {
          id: 'legal',
          name: 'Legal',
          description: 'Legal contracts and agreements',
          color: '#8b5cf6',
          createdAt: new Date().toISOString(),
        },
      ]
    },
    refetchInterval: 60000,
  })

  const createMutation = useMutation({
    mutationFn: async (category: Omit<Category, 'id' | 'createdAt'>) => {
      await api.post('/admin/categories', category)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setIsCreating(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      updates,
    }: {
      id: string
      updates: Partial<Category>
    }) => {
      await api.patch(`/admin/categories/${id}`, updates)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setEditingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/admin/categories/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Category Management</h1>
          <p className="text-muted-foreground mt-1">
            Organize documents into categories
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ['categories'] })
            }
            className="flex items-center gap-2 px-4 py-2 rounded-md border hover:bg-accent"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setIsCreating(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Category
          </button>
        </div>
      </div>

      {/* Create Form */}
      {isCreating && (
        <CategoryForm
          onSubmit={(data) => createMutation.mutate(data)}
          onCancel={() => setIsCreating(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-full flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        ) : (
          categories?.map((category) =>
            editingId === category.id ? (
              <CategoryForm
                key={category.id}
                category={category}
                onSubmit={(data) =>
                  updateMutation.mutate({ id: category.id, updates: data })
                }
                onCancel={() => setEditingId(null)}
                isLoading={updateMutation.isPending}
              />
            ) : (
              <CategoryCard
                key={category.id}
                category={category}
                onEdit={() => setEditingId(category.id)}
                onDelete={() => deleteMutation.mutate(category.id)}
              />
            )
          )
        )}
      </div>
    </div>
  )
}

interface CategoryCardProps {
  category: Category
  onEdit: () => void
  onDelete: () => void
}

function CategoryCard({ category, onEdit, onDelete }: CategoryCardProps) {
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div
          className="w-12 h-12 rounded-md"
          style={{ backgroundColor: category.color }}
        />
        <div className="flex gap-1">
          <button
            onClick={onEdit}
            className="p-1.5 rounded hover:bg-accent"
            title="Edit"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 rounded hover:bg-destructive/10 text-destructive"
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div>
        <h3 className="font-semibold">{category.name}</h3>
        <p className="text-sm text-muted-foreground mt-1">
          {category.description}
        </p>
      </div>
    </div>
  )
}

interface CategoryFormProps {
  category?: Category
  onSubmit: (data: Omit<Category, 'id' | 'createdAt'>) => void
  onCancel: () => void
  isLoading: boolean
}

function CategoryForm({
  category,
  onSubmit,
  onCancel,
  isLoading,
}: CategoryFormProps) {
  const [name, setName] = useState(category?.name || '')
  const [description, setDescription] = useState(category?.description || '')
  const [color, setColor] = useState(category?.color || '#3b82f6')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ name, description, color })
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border p-4 space-y-3">
      <input
        type="text"
        placeholder="Category Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        className="w-full px-3 py-2 rounded-md border bg-background"
      />
      <textarea
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={2}
        className="w-full px-3 py-2 rounded-md border bg-background resize-none"
      />
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">Color:</label>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          className="w-12 h-8 rounded border cursor-pointer"
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isLoading}
          className="flex-1 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? 'Saving...' : category ? 'Update' : 'Create'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-md border hover:bg-accent"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
