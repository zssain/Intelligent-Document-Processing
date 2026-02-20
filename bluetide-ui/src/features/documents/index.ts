import { DocumentProvider } from './context'
import { DocumentTable } from './components/DocumentTable'
import { DocumentFilters } from './components/DocumentFilters'
import { DocumentSearch } from './components/DocumentSearch'
import { DocumentPreviewSheet } from './components/DocumentPreviewSheet'
import { DocumentUploadForm } from './components/DocumentUploadForm'
import { DocumentActiveFilters } from './components/DocumentActiveFilters'
import { ModeSelector } from './components/ModeSelector'
import { ConnectionStatus } from './components/ConnectionStatus'

export const Document = {
    Root: DocumentProvider,
    Table: DocumentTable,
    Filters: DocumentFilters,
    Search: DocumentSearch,
    Preview: DocumentPreviewSheet,
    Upload: DocumentUploadForm,
    ActiveFilters: DocumentActiveFilters,
    ModeSelector: ModeSelector,
    ConnectionStatus: ConnectionStatus,
}
