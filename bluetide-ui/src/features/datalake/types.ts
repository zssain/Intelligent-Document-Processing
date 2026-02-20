// ---------------------------------------------------------------------------
// Types for the Datalake connectors (S3, SharePoint, Google Drive)
// ---------------------------------------------------------------------------

/** Which connector source a file came from. */
export type ConnectorSource = 's3' | 'sharepoint' | 'gdrive'

/** Connector metadata for UI presentation */
export interface ConnectorInfo {
  id: ConnectorSource
  label: string
  description: string
  icon: string // lucide-react icon name reference (handled in component)
  color: string // tailwind color class
  syncEndpoint: string
  listEndpoint: string
}

// ---------------------------------------------------------------------------
// List response shapes (from backend)
// ---------------------------------------------------------------------------

export interface S3FileItem {
  key: string
  size: number
  last_modified: string
  etag: string
}

/** @deprecated Use S3FileItem */
export type S3PdfItem = S3FileItem

export interface S3ListResponse {
  prefix: string
  total_objects: number
  total_files: number
  files: S3FileItem[]
}

export interface SharePointFileItem {
  name: string
  item_id: string
  webUrl: string
  size: number
  lastModifiedDateTime: string
  eTag: string
}

/** @deprecated Use SharePointFileItem */
export type SharePointPdfItem = SharePointFileItem

export interface SharePointListResponse {
  folder_path: string
  drive_id: string
  total_items: number
  total_files: number
  files: SharePointFileItem[]
}

export interface GDriveFileItem {
  name: string
  file_id: string
  webViewLink: string
  size: number
  modifiedTime: string
  md5Checksum: string
  version: string
}

/** @deprecated Use GDriveFileItem */
export type GDrivePdfItem = GDriveFileItem

export interface GDriveListResponse {
  folder_id: string
  total_files: number
  files: GDriveFileItem[]
}

// ---------------------------------------------------------------------------
// Sync response shape (all three connectors share the same structure)
// ---------------------------------------------------------------------------

export interface SyncResponse {
  status: 'completed'
  total_files: number
  ingested: number
  updated: number
  skipped: number
  failed: number
  errors?: Array<{ [key: string]: string }>
  // S3-specific
  prefix?: string
  // SharePoint-specific
  folder_path?: string
  drive_id?: string
  used_delta?: boolean
  // GDrive-specific
  folder_id?: string
  used_changes?: boolean
  cursor_key?: string
}

// ---------------------------------------------------------------------------
// Normalised row shown in the UI table
// ---------------------------------------------------------------------------

export interface DatalakeFile {
  id: string        // unique key per connector (s3 key / item_id / file_id)
  name: string
  source: ConnectorSource
  size: number       // bytes
  modified: string   // ISO date string
  url?: string       // webUrl / webViewLink / S3 URL
}

// ---------------------------------------------------------------------------
// Connector health (for dashboard-level status widget)
// ---------------------------------------------------------------------------

export interface ConnectorStatus {
  source: ConnectorSource
  status: 'connected' | 'disconnected' | 'syncing' | 'error'
  lastSync?: string
  totalFiles?: number
  message?: string
}

// ---------------------------------------------------------------------------
// Source Connections (paste-a-link flow)
// ---------------------------------------------------------------------------

export interface SourceFileInfo {
  file_id: string
  name: string
  mime_type?: string | null
  size?: number | null
  modified_at?: string | null
  web_url?: string | null
}

export interface SourceConnection {
  connection_id: string
  provider: 'gdrive' | 'sharepoint'
  label: string
  folder_id?: string | null
  site_hostname?: string | null
  site_path?: string | null
  item_path?: string | null
  original_url: string
  status: 'connected' | 'error'
  error_message?: string | null
  file_count: number
  connected_at: string
}

export interface ConnectLinkResponse {
  connection: SourceConnection
  files: SourceFileInfo[]
}
