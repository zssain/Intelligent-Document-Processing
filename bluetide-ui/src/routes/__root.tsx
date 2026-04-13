import { Outlet, createRootRoute, redirect, useRouterState } from '@tanstack/react-router'
import { AppShell } from '@/shared/components/layout/AppShell'
import { ThemeProvider } from '@/shared/components/theme-provider'
import { DocumentProvider } from '@/features/documents/context'
import { IngestionModeProvider } from '@/features/documents/ingestion-mode-context'
import { Chat } from '@/features/chat'
import { AnalyticsProvider } from '@/features/analytics/context'
import { LanguageProvider } from '@/shared/components/language-provider'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nextProvider } from 'react-i18next'
import i18n from '@/i18n/config'
import { AuthProvider, useAuth } from '@/shared/context/auth-context'
import { auth } from '@/shared/lib/firebase'

const queryClient = new QueryClient()

function RootComponent() {
  const authContext = useAuth()
  const routerState = useRouterState()
  const pathname = routerState.location.pathname

  // Check if current route is a public page (login/signup)
  const isPublicPage = ['/login', '/signup'].includes(pathname)

  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <LanguageProvider defaultLanguage="en" storageKey="bluetide-ui-language">
            <IngestionModeProvider>
              <DocumentProvider>
                <Chat.Root>
                  <AnalyticsProvider>
                    {isPublicPage ? (
                      // Public pages without navigation
                      <Outlet context={{ auth: authContext }} />
                    ) : (
                      // Authenticated pages with navigation
                      <div className="flex h-screen w-screen flex-col font-sans antialiased overflow-hidden bg-background">
                        <AppShell>
                          <Outlet context={{ auth: authContext }} />
                        </AppShell>
                      </div>
                    )}
                  </AnalyticsProvider>
                </Chat.Root>
              </DocumentProvider>
            </IngestionModeProvider>
          </LanguageProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </I18nextProvider>
  )
}

export const Route = createRootRoute({
  beforeLoad: async ({ location }) => {
    // Exclude login and signup from auth guard
    const publicPaths = ['/login', '/signup']
    const isPublicPath = publicPaths.some(path => location.pathname === path)

    if (isPublicPath) {
      return
    }

    // Wait for Firebase auth state to be ready (persistence restore complete)
    // Add a timeout to prevent indefinite hanging if Firebase is misconfigured
    try {
      await Promise.race([
        auth.authStateReady(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Auth state timeout')), 5000)
        ),
      ])
    } catch (err) {
      console.warn('[Auth Guard] authStateReady failed or timed out:', err)
      // On failure, redirect to login as a safety measure
      throw redirect({
        to: '/login',
        search: {
          redirect: location.href,
        },
      })
    }

    // Redirect to login if not authenticated, storing the intended path
    if (!auth.currentUser) {
      console.info('[Auth Guard] No authenticated user, redirecting to login')
      throw redirect({
        to: '/login',
        search: {
          redirect: location.href,
        },
      })
    }
    console.info('[Auth Guard] User authenticated:', auth.currentUser.email)
  },
  component: () => (
    <AuthProvider>
      <RootComponent />
    </AuthProvider>
  ),
})
