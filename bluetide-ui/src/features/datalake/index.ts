import { DatalakeProvider, useDatalake } from './context'
import { ConnectorCards } from './components/ConnectorCards'
import { FileTable } from './components/FileTable'
import { SyncToolbar } from './components/SyncToolbar'

export const Datalake = {
  Root: DatalakeProvider,
  ConnectorCards,
  FileTable,
  SyncToolbar,
  useContext: useDatalake,
}
