export function formatCO2e(kg: number | string | null | undefined): string {
  if (kg == null || kg === '') return '—'
  const n = typeof kg === 'string' ? parseFloat(kg) : kg
  if (isNaN(n)) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} MtCO₂e`
  if (n >= 1_000) return `${(n / 1_000).toFixed(2)} tCO₂e`
  return `${n.toFixed(1)} kgCO₂e`
}

export function formatNumber(n: number | string | null | undefined, decimals = 1): string {
  if (n == null || n === '') return '—'
  const num = typeof n === 'string' ? parseFloat(n) : n
  if (isNaN(num)) return '—'
  return num.toLocaleString('en-US', { maximumFractionDigits: decimals })
}

export function formatDate(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function formatDateTime(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export const SOURCE_LABELS: Record<string, string> = {
  sap: 'SAP',
  utility: 'Utility',
  travel: 'Travel',
}

export const SOURCE_COLORS: Record<string, string> = {
  sap: '#f59e0b',
  utility: '#3b82f6',
  travel: '#8b5cf6',
}

export const SCOPE_COLORS: Record<string, string> = {
  '1': '#ef4444',
  '2': '#f59e0b',
  '3': '#3b82f6',
}

export const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  pending: { label: 'Pending', color: 'text-slate-300', bg: 'bg-slate-800', dot: 'bg-slate-400' },
  approved: { label: 'Approved', color: 'text-brand-300', bg: 'bg-brand-900/40', dot: 'bg-brand-400' },
  rejected: { label: 'Rejected', color: 'text-red-300', bg: 'bg-red-900/30', dot: 'bg-red-400' },
  flagged: { label: 'Flagged', color: 'text-amber-300', bg: 'bg-amber-900/30', dot: 'bg-amber-400' },
}
