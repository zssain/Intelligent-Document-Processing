import api from '@/shared/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type JobFileStatus = 'queued' | 'processing' | 'completed' | 'failed'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface JobFile {
  id: string
  name: string
  status: JobFileStatus
  error?: string
}

export interface JobSummary {
  total: number
  completed: number
  failed: number
}

export interface Job {
  job_id: string
  status: JobStatus
  source_type: string
  created_by: string
  created_at: string
  started_at?: string
  completed_at?: string
  files: JobFile[]
  summary: JobSummary
}

export interface ProcessRequest {
  source_type: string
  files: Array<{ id: string; name: string }>
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const jobsService = {
  /**
   * Start processing selected files.
   * Hits: POST /jobs/process
   */
  processFiles: async (req: ProcessRequest): Promise<{ job_id: string }> => {
    const { data } = await api.post<{ job_id: string }>('jobs/process', req)
    return data
  },

  /**
   * Get job status with per-file progress.
   * Hits: GET /jobs/{jobId}
   */
  getJob: async (jobId: string): Promise<Job> => {
    const { data } = await api.get<Job>(`jobs/${jobId}`)
    return data
  },
}
