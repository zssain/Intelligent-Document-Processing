import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Document } from '@/features/documents'
import { Datalake } from '@/features/datalake'
import { JobTracker } from '@/features/datalake/components/JobTracker'
import { Hero } from '@/shared/components/layout/Hero'
import { Files } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useIngestionMode } from '@/features/documents/ingestion-mode-context'
import { useAuth } from '@/shared/context/auth-context'
import type { ConnectorSource } from '@/features/datalake/types'

export const Route = createFileRoute('/documents/')({
  component: DocumentsPage,
})

function DocumentsPage() {
  const { t } = useTranslation()
  const { isConnectorMode } = useIngestionMode()
  const { role } = useAuth()
  const isAdmin = role === 'org_admin'

  return (
    <Document.Root>
      <div className="space-y-6 max-w-[1600px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
        {/* 1. Page Header */}
        <Hero
          variant="minimal"
          title={t('documents.library.title')}
          subtitle={t('documents.library.subtitle')}
          icon={<Files className="h-6 w-6" />}
        />

        {/* 2. Ingestion Mode Selector */}
        <Document.ModeSelector />

        {/* 2b. OAuth Connection Status (Google Drive / SharePoint) */}
        <Document.ConnectionStatus />

        {/* 3. Mode-specific content */}
        {isConnectorMode ? (
          /* S3 / SharePoint / Google Drive mode → show connector sync UI */
          <Datalake.Root>
            <ConnectorModeContent />
          </Datalake.Root>
        ) : (
          /* Direct Upload mode → show upload form (admin only) */
          isAdmin && (
            <div className="space-y-6">
              <Document.Upload />
            </div>
          )
        )}

        {/* 4. Universal Document Library (always visible below) */}
        <div className="pt-2 border-t border-border/30">
          <div className="flex flex-col gap-2 py-4 px-6 border border-border/40 bg-card/30 rounded-xl">
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-1 items-center gap-0 max-w-xl">
                <Document.Search />
                <Document.Filters />
              </div>
            </div>
            <Document.ActiveFilters />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6">
          <main className="w-full">
            <Document.Table />
          </main>
        </div>

        {/* 5. Overlays & Modals */}
        <Document.Preview />
      </div>
    </Document.Root>
  )
}

/** Sub-component that lives inside <Datalake.Root> so it can use useDatalake() */
function ConnectorModeContent() {
  const { activeMode } = useIngestionMode()
  const { setActiveSource } = Datalake.useContext()
  const [activeJobId, setActiveJobId] = useState<string | null>(null)

  // Keep Datalake context's activeSource in sync with the ingestion mode
  useEffect(() => {
    const sourceMap: Record<string, ConnectorSource> = {
      s3: 's3',
      sharepoint: 'sharepoint',
      gdrive: 'gdrive',
    }
    const source = sourceMap[activeMode]
    if (source) {
      setActiveSource(source)
    }
  }, [activeMode, setActiveSource])

  return (
    <div className="space-y-4">
      <Datalake.ConnectLinkDialog />
      <Datalake.ConnectedSources />
      <Datalake.SyncToolbar />
      <Datalake.FileTable />
      <Datalake.ProcessBar onJobCreated={setActiveJobId} />
      {activeJobId && (
        <JobTracker jobId={activeJobId} onDismiss={() => setActiveJobId(null)} />
      )}
    </div>
  )
}
