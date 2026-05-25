import { apiClient } from './client'
import type { EmissionRecord, EmissionSummary, PaginatedResponse } from '../types'

export interface RecordFilters {
  scope?: string
  source_type?: string
  status?: string
  is_suspicious?: boolean
  facility?: string
  year?: number
  month?: number
  search?: string
  ordering?: string
  page?: number
}

export async function getSummary(): Promise<EmissionSummary> {
  const { data } = await apiClient.get('/emissions/records/summary/')
  return data
}

export async function getRecords(filters: RecordFilters = {}): Promise<PaginatedResponse<EmissionRecord>> {
  const params: Record<string, string | number | boolean> = {}
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) params[k] = v
  })
  const { data } = await apiClient.get('/emissions/records/', { params })
  return data
}

export async function getRecord(id: string): Promise<EmissionRecord> {
  const { data } = await apiClient.get(`/emissions/records/${id}/`)
  return data
}
