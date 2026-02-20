import { createFileRoute, useNavigate, useRouter } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useState, useEffect } from 'react'
import { getIdTokenResult } from 'firebase/auth'

export const Route = createFileRoute('/signup')({
  component: SignupPage,
})

type PollingState = 'idle' | 'polling' | 'success' | 'timeout' | 'error'

function SignupPage() {
  const navigate = useNavigate()
  const router = useRouter()
  const { signUp, signOut, user: currentUser, loading } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pollingState, setPollingState] = useState<PollingState>('idle')
  const [pollingMessage, setPollingMessage] = useState('')

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && currentUser) {
      const redirectTo = (router.state.location.state as any)?.redirect || '/'
      navigate({ to: redirectTo })
    }
  }, [loading, currentUser, navigate, router.state.location.state])

  const pollForClaims = async (user: any) => {
    setPollingState('polling')
    setPollingMessage('Setting up your account...')

    const startTime = Date.now()
    const maxTimeout = 60000 // 60 seconds
    const pollInterval = 2000 // 2 seconds

    return new Promise<boolean>((resolve) => {
      const poll = async () => {
        try {
          const elapsed = Date.now() - startTime

          if (elapsed >= maxTimeout) {
            setPollingState('timeout')
            setPollingMessage('Account setup is taking longer than expected')
            resolve(false)
            return
          }

          // Force refresh token to get latest claims
          const tokenResult = await getIdTokenResult(user, true)
          const claims = tokenResult.claims

          // Check if tenant_id claim is present
          if (claims.tenant_id) {
            setPollingState('success')
            setPollingMessage('Account setup complete!')
            resolve(true)
            return
          }

          // Continue polling
          setTimeout(poll, pollInterval)
        } catch (err) {
          console.error('Error polling for claims:', err)
          setPollingState('error')
          setPollingMessage('Error checking account status')
          resolve(false)
        }
      }

      poll()
    })
  }

  const handleRetry = async () => {
    if (currentUser) {
      const success = await pollForClaims(currentUser)
      if (success) {
        const redirectTo = (router.state.location.state as any)?.redirect || '/'
        navigate({ to: redirectTo })
      }
    }
  }

  const handleSignOutAndSignIn = async () => {
    try {
      await signOut()
      navigate({ to: '/login' })
    } catch (err) {
      console.error('Error signing out:', err)
      setError('Failed to sign out')
    }
  }

  const handleContactSupport = () => {
    // Navigate to a support page or show contact info
    window.location.href = 'mailto:support@bluetide.com?subject=Account Setup Issue'
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setIsSubmitting(true)

    try {
      const user = await signUp(email, password)
      
      // Start polling for claims
      const success = await pollForClaims(user)

      if (success) {
        const redirectTo = (router.state.location.state as any)?.redirect || '/'
        navigate({ to: redirectTo })
      }
    } catch (err: any) {
      console.error('Signup error:', err)
      setError(err.message || 'Failed to create account')
      setIsSubmitting(false)
      setPollingState('idle')
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // Show polling UI
  if (pollingState === 'polling') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md text-center space-y-6">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mx-auto"></div>
          <div>
            <h2 className="text-2xl font-bold">{pollingMessage}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              This may take up to a minute. Please don't close this page.
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Show timeout/error UI
  if (pollingState === 'timeout' || pollingState === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-destructive/15">
              <svg
                className="h-8 w-8 text-destructive"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="mt-4 text-2xl font-bold">{pollingMessage}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Your account was created, but we're still setting up your access.
            </p>
          </div>

          <div className="space-y-3">
            <button
              onClick={handleRetry}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              Retry
            </button>
            <button
              onClick={handleSignOutAndSignIn}
              className="w-full rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              Sign out & sign in
            </button>
            <button
              onClick={handleContactSupport}
              className="w-full rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              Contact support
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight">Create Account</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Join BlueTide to get started
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-4 rounded-md">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="••••••••"
              />
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium mb-2">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Creating account...' : 'Sign Up'}
          </button>

          <div className="text-center text-sm">
            <span className="text-muted-foreground">Already have an account? </span>
            <button
              type="button"
              onClick={() => navigate({ to: '/login' })}
              className="font-medium text-primary hover:underline"
            >
              Sign in
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
