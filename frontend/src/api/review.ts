import { apiClient } from './client'
import type { ReviewDecision, ReviewQueue } from '../types'

export async function getReviewQueue(): Promise<ReviewQueue> {
  const { data } = await apiClient.get('/review/queue/')
  return data
}

export async function reviewRecord(
  recordId: string,
  action: 'approve' | 'reject' | 'flag' | 'unflag',
  notes?: string
) {
  const { data } = await apiClient.post(`/review/records/${recordId}/action/`, {
    action,
    notes: notes || '',
  })
  return data
}

export async function bulkReview(
  recordIds: string[],
  action: 'approve' | 'reject' | 'flag',
  notes?: string
) {
  const { data } = await apiClient.post('/review/bulk/', {
    record_ids: recordIds,
    action,
    notes: notes || '',
  })
  return data
}

export async function getAuditLog(recordId?: string): Promise<{ count: number; results: ReviewDecision[] }> {
  const params = recordId ? { record_id: recordId } : {}
  const { data } = await apiClient.get('/review/audit-log/', { params })
  return data
}
