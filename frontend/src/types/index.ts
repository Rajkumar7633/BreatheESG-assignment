export type Scope = '1' | '2' | '3'
export type SourceType = 'sap' | 'utility' | 'travel'
export type RecordStatus = 'pending' | 'approved' | 'rejected' | 'flagged'
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'partial'

export interface Organization {
  id: string
  name: string
  slug: string
  country: string
  reporting_year: number
  created_at: string
}

export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  role: 'admin' | 'analyst' | 'viewer'
  organization: Organization
}

export interface IngestionJob {
  id: string
  source_type: SourceType
  source_type_display: string
  status: JobStatus
  status_display: string
  filename: string
  total_rows: number
  processed_rows: number
  failed_rows: number
  flagged_rows: number
  created_by: string
  created_by_name: string
  created_at: string
  completed_at: string | null
  error_log: Array<{ row: number; errors: string[] }>
  metadata: Record<string, unknown>
}

export interface EmissionFactor {
  id: number
  name: string
  scope: Scope
  factor_value: string
  factor_unit: string
  activity_unit: string
  source_name: string
  source_year: number
  region: string
}

export interface EmissionRecord {
  id: string
  source_type: SourceType
  source_type_display: string
  scope: Scope
  scope_display: string
  category: string
  sub_category: string
  activity_description: string
  activity_value: string
  activity_unit: string
  co2e_kg: string | null
  co2_kg: string | null
  ch4_kg: string | null
  n2o_kg: string | null
  period_start: string
  period_end: string
  facility: string
  cost_center: string
  department: string
  country: string
  status: RecordStatus
  status_display: string
  is_suspicious: boolean
  suspicious_reasons: string[]
  is_locked: boolean
  locked_at: string | null
  was_edited: boolean
  original_values: Record<string, unknown>
  reviewed_by: string | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  review_notes: string
  emission_factor: number | null
  emission_factor_name: string | null
  ingestion_job_id: string
  raw_data: Record<string, string>
  created_at: string
  updated_at: string
}

export interface ReviewDecision {
  id: string
  emission_record: string
  action: string
  action_display: string
  performed_by: string
  performed_by_name: string
  notes: string
  changes: Record<string, unknown>
  performed_at: string
}

export interface EmissionSummary {
  total_records: number
  pending_count: number
  approved_count: number
  rejected_count: number
  flagged_count: number
  scope1_co2e_kg: number
  scope2_co2e_kg: number
  scope3_co2e_kg: number
  total_co2e_kg: number
  by_source: Record<string, { co2e_kg: number; count: number }>
  by_scope: Array<{ scope: string; label: string; co2e_kg: number; count: number }>
  monthly_trend: Array<{ month: string; scope: string; co2e_kg: number }>
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ReviewQueue {
  count: number
  results: EmissionRecord[]
}
