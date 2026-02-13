import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** The four mutually-exclusive ingestion modes. */
export type IngestionMode = 's3' | 'sharepoint' | 'gdrive' | 'upload'

export const ALL_MODES: IngestionMode[] = ['s3', 'sharepoint', 'gdrive', 'upload']

export interface IngestionModeContextValue {
  /** Currently active ingestion mode */
  activeMode: IngestionMode
  /** Switch to another ingestion mode – updates URL + persists */
  setMode: (mode: IngestionMode) => void
  /** Whether a connector mode (non-upload) is active */
  isConnectorMode: boolean
}

const STORAGE_KEY = 'bluetide-ingestion-mode'

const IngestionModeContext = createContext<IngestionModeContextValue | null>(null)

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

function getInitialMode(): IngestionMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && ALL_MODES.includes(stored as IngestionMode)) {
      return stored as IngestionMode
    }
  } catch { /* SSR / privacy mode */ }
  return 'upload'
}

export function IngestionModeProvider({ children }: { children: ReactNode }) {
  const [activeMode, setActiveMode] = useState<IngestionMode>(getInitialMode)

  // Persist to localStorage whenever mode changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, activeMode)
    } catch { /* ignore */ }
  }, [activeMode])

  const setMode = useCallback((mode: IngestionMode) => {
    setActiveMode(mode)
  }, [])

  const isConnectorMode = activeMode !== 'upload'

  return (
    <IngestionModeContext.Provider value={{ activeMode, setMode, isConnectorMode }}>
      {children}
    </IngestionModeContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useIngestionMode() {
  const ctx = useContext(IngestionModeContext)
  if (!ctx) throw new Error('useIngestionMode must be used inside <IngestionModeProvider>')
  return ctx
}
