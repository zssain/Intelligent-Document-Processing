import { createFileRoute, redirect } from '@tanstack/react-router'
import { Dashboard } from '@/features/dashboard'

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    const auth = (context as any).auth
    if (!auth || auth.role !== 'org_admin') {
      throw redirect({ to: '/documents' })
    }
  },
  component: DashboardPage,
})

function DashboardPage() {
  return <Dashboard.View />
}
