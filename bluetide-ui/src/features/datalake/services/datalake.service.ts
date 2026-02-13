import axios from 'axios'
import type {
  S3ListResponse,
  SharePointListResponse,
  GDriveListResponse,
  SyncResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`,
  headers: { 'Content-Type': 'application/json' },
})

/** Inject X-API-Key header when available */
function authHeaders(): Record<string, string> {
  const key = import.meta.env.VITE_API_KEY
  return key ? { 'X-API-Key': key } : {}
}

// ---------------------------------------------------------------------------
// S3 Datalake
// ---------------------------------------------------------------------------

export async function listS3Files(limit = 100): Promise<S3ListResponse> {
  const { data } = await api.get<S3ListResponse>('datalake/s3/list', {
    params: { limit },
    headers: authHeaders(),
  })
  return data
}

export async function syncS3(
  opts: { limit?: number; force?: boolean } = {},
): Promise<SyncResponse> {
  const { data } = await api.post<SyncResponse>('datalake/s3/sync', null, {
    params: { limit: opts.limit ?? 10, force: opts.force ?? false },
    headers: authHeaders(),
  })
  return data
}

// ---------------------------------------------------------------------------
// SharePoint
// ---------------------------------------------------------------------------

export async function listSharePointFiles(limit = 100): Promise<SharePointListResponse> {
  const { data } = await api.get<SharePointListResponse>('datalake/sharepoint/list', {
    params: { limit },
    headers: authHeaders(),
  })
  return data
}

export async function syncSharePoint(
  opts: { limit?: number; force?: boolean; full_scan?: boolean } = {},
): Promise<SyncResponse> {
  const { data } = await api.post<SyncResponse>('datalake/sharepoint/sync', null, {
    params: {
      limit: opts.limit ?? 10,
      force: opts.force ?? false,
      full_scan: opts.full_scan ?? false,
    },
    headers: authHeaders(),
  })
  return data
}

// ---------------------------------------------------------------------------
// Google Drive
// ---------------------------------------------------------------------------

export async function listGDriveFiles(limit = 100): Promise<GDriveListResponse> {
  const { data } = await api.get<GDriveListResponse>('datalake/gdrive/list', {
    params: { limit },
    headers: authHeaders(),
  })
  return data
}

export async function syncGDrive(
  opts: { limit?: number; force?: boolean; full_scan?: boolean } = {},
): Promise<SyncResponse> {
  const { data } = await api.post<SyncResponse>('datalake/gdrive/sync', null, {
    params: {
      limit: opts.limit ?? 10,
      force: opts.force ?? false,
      full_scan: opts.full_scan ?? false,
    },
    headers: authHeaders(),
  })
  return data
}

// ---------------------------------------------------------------------------
// Convenience map by source
// ---------------------------------------------------------------------------

export const datalakeService = {
  s3: { list: listS3Files, sync: syncS3 },
  sharepoint: { list: listSharePointFiles, sync: syncSharePoint },
  gdrive: { list: listGDriveFiles, sync: syncGDrive },
}
