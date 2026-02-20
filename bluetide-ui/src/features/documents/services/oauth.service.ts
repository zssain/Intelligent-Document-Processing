import api from '@/shared/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OAuthProvider = 'gdrive' | 'sharepoint'

export interface ConnectionInfo {
  provider: OAuthProvider
  connected: boolean
  email?: string
  connected_at?: string
  error_reason?: string
  oauth_configured?: boolean
}

export interface ConnectionsResponse {
  gdrive: ConnectionInfo
  sharepoint: ConnectionInfo
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const oauthService = {
  /**
   * Fetch connection status for all providers.
   * Hits: GET /auth/connections
   */
  getConnections: async (): Promise<ConnectionsResponse> => {
    const { data } = await api.get<ConnectionsResponse>('auth/connections')
    return data
  },

  /**
   * Start OAuth connect flow – returns the authorization URL.
   * Hits: GET /auth/{provider}/connect
   */
  getConnectUrl: async (provider: OAuthProvider): Promise<string> => {
    const { data } = await api.get<{ authorization_url: string }>(
      `auth/${provider}/connect`,
    )
    return data.authorization_url
  },

  /**
   * Disconnect a linked account.
   * Hits: DELETE /auth/{provider}/disconnect
   */
  disconnect: async (provider: OAuthProvider): Promise<void> => {
    await api.delete(`auth/${provider}/disconnect`)
  },
}
