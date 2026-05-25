import { apiClient } from './client'
import type { IngestionJob, PaginatedResponse } from '../types'

export async function getJobs(): Promise<PaginatedResponse<IngestionJob>> {
  const { data } = await apiClient.get('/ingestion/jobs/')
  return data
}

export async function uploadFile(
  file: File,
  sourceType: string,
  region?: string
): Promise<IngestionJob> {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  if (region) form.append('region', region)

  const { data } = await apiClient.post('/ingestion/jobs/upload/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
