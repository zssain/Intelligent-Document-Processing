import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/shared/context/auth-context'
import { useState, useEffect } from 'react'
import { User, Lock, Moon, Sun } from 'lucide-react'
import { useTheme } from '@/shared/components/theme-provider'
import { useLanguage } from '@/shared/components/language-provider'
import { useTranslation } from 'react-i18next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const { signIn, user, loading } = useAuth()
  const { theme, setTheme } = useTheme()
  const { language, setLanguage } = useLanguage()
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated (e.g., user navigates to /login while already signed in)
  useEffect(() => {
    if (!loading && user && !isSubmitting) {
      navigate({ to: '/documents' })
    }
  }, [loading, user, navigate, isSubmitting])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await signIn(email, password)
      // Full page reload so the router re-evaluates beforeLoad with the now-persisted user
      window.location.href = '/documents'
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.message || 'Failed to sign in. Please check your credentials.')
      setIsSubmitting(false)
    }
  }

  const handleDemoLogin = async (demoEmail: string, demoPassword: string) => {
    setEmail(demoEmail)
    setPassword(demoPassword)
    setError(null)
    setIsSubmitting(true)

    try {
      await signIn(demoEmail, demoPassword)
      // Full page reload so the router re-evaluates beforeLoad with the now-persisted user
      window.location.href = '/documents'
    } catch (err: any) {
      console.error('Demo login error:', err)
      setError(err.message || 'Failed to sign in with demo account.')
      setIsSubmitting(false)
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

  return (
    <div className="flex min-h-screen flex-col bg-background relative">
      {/* Top Horizontal Bar with Logo */}
      <header className="w-full border-b bg-card/80 backdrop-blur-xl px-6 py-3">
        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="Teclusion AI"
            className="h-9 w-9 object-contain"
          />
          <span className="text-lg font-bold tracking-tight">Teclusion AI</span>
        </div>
      </header>

      {/* Theme and Language Controls - Fixed Position */}
      <div className="fixed bottom-6 left-6 flex flex-col gap-3 z-50">
        {/* Theme Toggle */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex h-10 w-10 items-center justify-center rounded-lg border bg-card hover:bg-accent transition-colors"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>

        {/* Language Selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg border bg-card hover:bg-accent transition-colors"
              title="Change language"
            >
              <span className="text-xs font-semibold">{language.toUpperCase()}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="right">
            <DropdownMenuItem onClick={() => setLanguage('en')}>
              <span className={language === 'en' ? 'font-semibold' : ''}>EN - English</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setLanguage('ar')}>
              <span className={language === 'ar' ? 'font-semibold' : ''}>AR - العربية</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Main content area — vertically centered */}
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-md">
          {/* Title area */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Intelligent Document Processing</h1>
          </div>

          {/* Login Card */}
          <div className="rounded-xl border bg-card p-8 shadow-lg">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold tracking-tight">{t('login.welcome_back')}</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('login.subtitle')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2">
                    {t('login.username')}
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full rounded-md border border-input bg-background pl-10 pr-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="admin"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium mb-2">
                    {t('login.password')}
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full rounded-md border border-input bg-background pl-10 pr-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? t('login.signing_in') : t('login.sign_in')}
              </button>

              {/* Demo Access Section */}
              <div className="pt-4 border-t">
                <p className="text-center text-xs text-muted-foreground mb-3">
                  {t('login.demo_access')}
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDemoLogin('admin@teclusion.ai', 'qwerty123')}
                    disabled={isSubmitting}
                    className="flex-1 rounded-md border border-orange-500/50 bg-orange-500/10 px-3 py-2 text-xs font-medium text-orange-600 dark:text-orange-400 hover:bg-orange-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {t('login.admin_demo')}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDemoLogin('user@teclusion.ai', 'qwerty123')}
                    disabled={isSubmitting}
                    className="flex-1 rounded-md border border-blue-500/50 bg-blue-500/10 px-3 py-2 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {t('login.viewer_demo')}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-muted-foreground mt-8">
            © 2026 Teclusion AI. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  )
}
