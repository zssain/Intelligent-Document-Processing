import { DatalakeProvider, useDatalake } from './context'
import { ConnectorCards } from './components/ConnectorCards'
import { FileTable } from './components/FileTable'
import { SyncToolbar } from './components/SyncToolbar'
import { ProcessBar } from './components/ProcessBar'
import { ConnectLinkDialog } from './components/ConnectLinkDialog'
import { ConnectedSources } from './components/ConnectedSources'

export const Datalake = {
  Root: DatalakeProvider,
  ConnectorCards,
  FileTable,
  SyncToolbar,
  ProcessBar,
  ConnectLinkDialog,
  ConnectedSources,
  useContext: useDatalake,
}
