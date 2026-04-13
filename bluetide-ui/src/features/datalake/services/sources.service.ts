import api from '@/shared/lib/api'
import type {
  SourceConnection,
  SourceFileInfo,
  ConnectLinkResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Connect via pasted link
// ---------------------------------------------------------------------------

export async function connectViaLink(
  url: string,
  label?: string,
): Promise<ConnectLinkResponse> {
  const { data } = await api.post<ConnectLinkResponse>('sources/connect-link', {
    url,
    label,
  })
  return data
}

// ---------------------------------------------------------------------------
// List saved connections
// ---------------------------------------------------------------------------

export async function listConnections(
  provider?: 'gdrive' | 'sharepoint',
): Promise<SourceConnection[]> {
  try {
    const { data } = await api.get<SourceConnection[]>('sources/connections', {
      params: provider ? { provider } : undefined,
    })
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Refresh file list for a specific connection
// ---------------------------------------------------------------------------

export async function listConnectionFiles(
  connectionId: string,
): Promise<SourceFileInfo[]> {
  const { data } = await api.get<SourceFileInfo[]>(
    `sources/${connectionId}/files`,
  )
  return data
}

// ---------------------------------------------------------------------------
// Disconnect / remove a connection
// ---------------------------------------------------------------------------

export async function disconnectSource(
  connectionId: string,
): Promise<{ status: string; connection_id: string }> {
  const { data } = await api.delete<{ status: string; connection_id: string }>(
    `sources/${connectionId}`,
  )
  return data
}

// ---------------------------------------------------------------------------
// Convenience object
// ---------------------------------------------------------------------------

export const sourcesService = {
  connectViaLink,
  listConnections,
  listConnectionFiles,
  disconnectSource,
}
