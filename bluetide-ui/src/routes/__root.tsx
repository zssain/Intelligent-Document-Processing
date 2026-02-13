import { Outlet, createRootRoute } from '@tanstack/react-router'
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

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: () => (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <LanguageProvider defaultLanguage="en" storageKey="bluetide-ui-language">
            <IngestionModeProvider>
              <DocumentProvider>
                <Chat.Root>
                  <AnalyticsProvider>
                    <div className="flex h-screen w-screen flex-col font-sans antialiased overflow-hidden bg-background">
                      <AppShell>
                        <Outlet />
                      </AppShell>
                    </div>
                  </AnalyticsProvider>
                </Chat.Root>
              </DocumentProvider>
            </IngestionModeProvider>
          </LanguageProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </I18nextProvider>
  ),
})
