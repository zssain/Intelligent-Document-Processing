import { createFileRoute, redirect } from '@tanstack/react-router'
import { Dashboard } from '@/features/dashboard'
import { auth as firebaseAuth } from '@/shared/lib/firebase'

export const Route = createFileRoute('/')({
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
  component: DashboardPage,
})

function DashboardPage() {
  return <Dashboard.View />
}
