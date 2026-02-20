import api from '@/shared/lib/api'
import type {
  S3ListResponse,
  SharePointListResponse,
  GDriveListResponse,
  SyncResponse,
} from '../types'

// ---------------------------------------------------------------------------
// S3 Datalake
// ---------------------------------------------------------------------------

export async function listS3Files(limit = 100): Promise<S3ListResponse> {
  const { data } = await api.get<S3ListResponse>('datalake/s3/list', {
    params: { limit },
  })
  return data
}

export async function syncS3(
  opts: { limit?: number; force?: boolean } = {},
): Promise<SyncResponse> {
  const { data } = await api.post<SyncResponse>('datalake/s3/sync', null, {
    params: { limit: opts.limit ?? 10, force: opts.force ?? false },
  })
  return data
}

// ---------------------------------------------------------------------------
// SharePoint
// ---------------------------------------------------------------------------

export async function listSharePointFiles(limit = 100): Promise<SharePointListResponse> {
  const { data } = await api.get<SharePointListResponse>('datalake/sharepoint/list', {
    params: { limit },
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
  })
  return data
}

// ---------------------------------------------------------------------------
// Google Drive
// ---------------------------------------------------------------------------

export async function listGDriveFiles(limit = 100): Promise<GDriveListResponse> {
  const { data } = await api.get<GDriveListResponse>('datalake/gdrive/list', {
    params: { limit },
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
