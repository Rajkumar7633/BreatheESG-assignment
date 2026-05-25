import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, ChevronUp, ChevronDown } from 'lucide-react'
import { getRecords } from '../api/emissions'
import { formatCO2e, formatDate, formatNumber, SOURCE_COLORS, SCOPE_COLORS } from '../utils/formatters'
import StatusBadge from '../components/StatusBadge'
import type { RecordFilters } from '../api/emissions'

export default function Records() {
  const [filters, setFilters] = useState<RecordFilters>({ ordering: '-period_start' })
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const queryFilters = { ...filters, search: search || undefined, page }

  const { data, isLoading } = useQuery({
    queryKey: ['records', queryFilters],
    queryFn: () => getRecords(queryFilters),
  })

  const records = data?.results || []
  const total = data?.count || 0
  const pageSize = 50

  function setFilter(key: keyof RecordFilters, value: string | number | undefined) {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }))
    setPage(1)
  }

  function toggleSort(field: string) {
    const curr = filters.ordering || ''
    const next = curr === field ? `-${field}` : field
    setFilter('ordering', next)
  }

  function SortIcon({ field }: { field: string }) {
    const curr = filters.ordering
    if (curr === field) return <ChevronUp className="w-3 h-3" />
    if (curr === `-${field}`) return <ChevronDown className="w-3 h-3" />
    return <div className="w-3 h-3" />
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">All Records</h1>
        <p className="text-slate-400 text-sm mt-1">{formatNumber(total, 0)} emission records</p>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            className="input pl-9 py-1.5 text-sm"
            placeholder="Search descriptions, facilities…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <select
          className="input w-auto text-sm py-1.5"
          value={filters.scope || ''}
          onChange={(e) => setFilter('scope', e.target.value)}
        >
          <option value="">All scopes</option>
          <option value="1">Scope 1</option>
          <option value="2">Scope 2</option>
          <option value="3">Scope 3</option>
        </select>
        <select
          className="input w-auto text-sm py-1.5"
          value={filters.source_type || ''}
          onChange={(e) => setFilter('source_type', e.target.value)}
        >
          <option value="">All sources</option>
          <option value="sap">SAP</option>
          <option value="utility">Utility</option>
          <option value="travel">Travel</option>
        </select>
        <select
          className="input w-auto text-sm py-1.5"
          value={filters.status || ''}
          onChange={(e) => setFilter('status', e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="flagged">Flagged</option>
        </select>
        <select
          className="input w-auto text-sm py-1.5"
          value={filters.is_suspicious !== undefined ? String(filters.is_suspicious) : ''}
          onChange={(e) => setFilter('is_suspicious', e.target.value === '' ? undefined : e.target.value as any)}
        >
          <option value="">All records</option>
          <option value="true">Suspicious only</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                {[
                  { label: 'Description', field: null },
                  { label: 'Scope', field: 'scope' },
                  { label: 'Source', field: 'source_type' },
                  { label: 'Period', field: 'period_start' },
                  { label: 'Activity', field: 'activity_value' },
                  { label: 'CO₂e', field: 'co2e_kg' },
                  { label: 'Status', field: 'status' },
                ].map(({ label, field }) => (
                  <th
                    key={label}
                    onClick={() => field && toggleSort(field)}
                    className={`px-4 py-3 text-left text-xs font-medium text-slate-400 ${
                      field ? 'cursor-pointer hover:text-slate-200' : ''
                    }`}
                  >
                    <div className="flex items-center gap-1">
                      {label}
                      {field && <SortIcon field={field} />}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(8)].map((_, i) => (
                  <tr key={i} className="border-b border-slate-800/50">
                    {[...Array(7)].map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-slate-800 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                    No records match your filters
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr
                    key={record.id}
                    className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${
                      record.is_suspicious ? 'bg-amber-900/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-slate-200 truncate text-xs">{record.activity_description}</p>
                      {record.facility && (
                        <p className="text-slate-500 text-xs truncate">{record.facility}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          backgroundColor: `${SCOPE_COLORS[record.scope]}20`,
                          color: SCOPE_COLORS[record.scope],
                        }}
                      >
                        S{record.scope}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="text-xs font-medium"
                        style={{ color: SOURCE_COLORS[record.source_type] }}
                      >
                        {record.source_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                      {formatDate(record.period_start)}
                    </td>
                    <td className="px-4 py-3 text-slate-300 font-mono text-xs whitespace-nowrap">
                      {parseFloat(record.activity_value).toLocaleString()} {record.activity_unit}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs whitespace-nowrap">
                      <span className="text-white font-semibold">{formatCO2e(record.co2e_kg)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <StatusBadge status={record.status} size="sm" />
                        {record.is_suspicious && (
                          <span title="Flagged for review" className="text-amber-400">⚠</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > pageSize && (
          <div className="px-4 py-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="btn-secondary py-1 px-3 text-xs disabled:opacity-30"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page * pageSize >= total}
                className="btn-secondary py-1 px-3 text-xs disabled:opacity-30"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
