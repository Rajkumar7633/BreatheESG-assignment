import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  CheckCircle2, XCircle, Flag, AlertTriangle, ChevronDown,
  ChevronUp, Eye, CheckSquare, Square, Loader2
} from 'lucide-react'
import { getReviewQueue, reviewRecord, bulkReview } from '../api/review'
import { formatCO2e, formatDate, SOURCE_COLORS, SCOPE_COLORS } from '../utils/formatters'
import StatusBadge from '../components/StatusBadge'
import type { EmissionRecord } from '../types'

function SuspicionAlert({ reasons }: { reasons: string[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-amber-900/20 border border-amber-800/40 rounded-lg p-3 mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-amber-400 text-xs font-medium w-full text-left"
      >
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
        {reasons.length} suspicion flag{reasons.length > 1 ? 's' : ''}
        {open ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />}
      </button>
      {open && (
        <ul className="mt-2 space-y-1">
          {reasons.map((r, i) => (
            <li key={i} className="text-amber-300 text-xs pl-5 relative before:absolute before:left-2 before:content-['·']">
              {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RawDataDrawer({ record, onClose }: { record: EmissionRecord; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/50" onClick={onClose} />
      <div className="w-96 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Raw source data</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-lg leading-none">×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-all">
            {JSON.stringify(record.raw_data, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}

function ReviewCard({
  record,
  selected,
  onToggleSelect,
  onAction,
}: {
  record: EmissionRecord
  selected: boolean
  onToggleSelect: () => void
  onAction: (action: 'approve' | 'reject' | 'flag' | 'unflag', notes?: string) => void
}) {
  const [showRaw, setShowRaw] = useState(false)
  const [notes, setNotes] = useState('')
  const [showNotesFor, setShowNotesFor] = useState<string | null>(null)

  function handleAction(action: 'approve' | 'reject' | 'flag' | 'unflag') {
    onAction(action, notes)
    setNotes('')
    setShowNotesFor(null)
  }

  return (
    <>
      {showRaw && <RawDataDrawer record={record} onClose={() => setShowRaw(false)} />}
      <div className={`card p-4 transition-colors ${
        record.is_suspicious ? 'border-amber-800/40' : ''
      } ${selected ? 'ring-1 ring-brand-500' : ''}`}>
        <div className="flex items-start gap-3">
          <button onClick={onToggleSelect} className="mt-0.5 flex-shrink-0">
            {selected ? (
              <CheckSquare className="w-4 h-4 text-brand-400" />
            ) : (
              <Square className="w-4 h-4 text-slate-600" />
            )}
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-slate-200 text-sm font-medium leading-tight truncate">
                  {record.activity_description}
                </p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `${SCOPE_COLORS[record.scope]}20`,
                      color: SCOPE_COLORS[record.scope],
                    }}
                  >
                    Scope {record.scope}
                  </span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `${SOURCE_COLORS[record.source_type]}20`,
                      color: SOURCE_COLORS[record.source_type],
                    }}
                  >
                    {record.source_type.toUpperCase()}
                  </span>
                  {record.facility && (
                    <span className="text-slate-500 text-xs">{record.facility}</span>
                  )}
                  <span className="text-slate-600 text-xs">
                    {formatDate(record.period_start)}
                    {record.period_end && record.period_end !== record.period_start
                      ? ` – ${formatDate(record.period_end)}`
                      : ''}
                  </span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-white font-bold font-mono text-sm">
                  {formatCO2e(record.co2e_kg)}
                </p>
                <p className="text-slate-500 text-xs">
                  {parseFloat(record.activity_value).toLocaleString()} {record.activity_unit}
                </p>
              </div>
            </div>

            {record.is_suspicious && record.suspicious_reasons.length > 0 && (
              <SuspicionAlert reasons={record.suspicious_reasons} />
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 mt-3">
              <button
                onClick={() => handleAction('approve')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-900/40 hover:bg-brand-900/70 text-brand-400 text-xs font-medium transition-colors border border-brand-800/40"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Approve
              </button>
              <button
                onClick={() => handleAction('reject')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-xs font-medium transition-colors border border-red-800/40"
              >
                <XCircle className="w-3.5 h-3.5" /> Reject
              </button>
              <button
                onClick={() =>
                  setShowNotesFor(showNotesFor === 'flag' ? null : 'flag')
                }
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-900/30 hover:bg-amber-900/50 text-amber-400 text-xs font-medium transition-colors border border-amber-800/40"
              >
                <Flag className="w-3.5 h-3.5" />
                {record.status === 'flagged' ? 'Unflag' : 'Flag'}
              </button>
              <button
                onClick={() => setShowRaw(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs font-medium transition-colors ml-auto"
              >
                <Eye className="w-3.5 h-3.5" /> Raw data
              </button>
            </div>

            {showNotesFor && (
              <div className="mt-2 flex gap-2">
                <input
                  className="input text-xs py-1.5 flex-1"
                  placeholder="Add a note (optional)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  autoFocus
                />
                <button
                  onClick={() => handleAction(record.status === 'flagged' ? 'unflag' : 'flag')}
                  className="btn-secondary text-xs py-1.5"
                >
                  Submit
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default function Review() {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['review-queue'],
    queryFn: getReviewQueue,
    refetchInterval: 15_000,
  })

  const actionMutation = useMutation({
    mutationFn: ({ id, action, notes }: { id: string; action: any; notes?: string }) =>
      reviewRecord(id, action, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
    onError: () => toast.error('Action failed'),
  })

  const bulkMutation = useMutation({
    mutationFn: ({ action, notes }: { action: 'approve' | 'reject' | 'flag'; notes?: string }) =>
      bulkReview([...selected], action, notes),
    onSuccess: (data) => {
      toast.success(data.message)
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
    onError: () => toast.error('Bulk action failed'),
  })

  const records = data?.results || []
  const total = data?.count || 0
  const flaggedCount = records.filter((r) => r.is_suspicious).length

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === records.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(records.map((r) => r.id)))
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Queue</h1>
          <p className="text-slate-400 text-sm mt-1">
            {total} records pending · {flaggedCount} flagged
          </p>
        </div>
        {flaggedCount > 0 && (
          <div className="flex items-center gap-2 bg-amber-900/30 border border-amber-800/40 rounded-xl px-3 py-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-amber-300 text-sm font-medium">{flaggedCount} need attention</span>
          </div>
        )}
      </div>

      {/* Bulk toolbar */}
      {selected.size > 0 && (
        <div className="card p-3 mb-4 flex items-center gap-3 border-brand-800/50 bg-brand-900/20">
          <span className="text-brand-300 text-sm font-medium">{selected.size} selected</span>
          <button
            onClick={() => bulkMutation.mutate({ action: 'approve' })}
            disabled={bulkMutation.isPending}
            className="btn-primary py-1.5 text-xs flex items-center gap-1.5"
          >
            {bulkMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            Approve all
          </button>
          <button
            onClick={() => bulkMutation.mutate({ action: 'reject' })}
            disabled={bulkMutation.isPending}
            className="btn-danger py-1.5 text-xs"
          >
            Reject all
          </button>
          <button onClick={() => setSelected(new Set())} className="text-slate-500 text-xs ml-auto hover:text-slate-300">
            Clear
          </button>
        </div>
      )}

      {/* Select all */}
      {records.length > 0 && (
        <div className="flex items-center gap-2 mb-3 px-1">
          <button onClick={toggleAll} className="flex items-center gap-2 text-slate-500 hover:text-slate-300 text-xs">
            {selected.size === records.length ? (
              <CheckSquare className="w-4 h-4 text-brand-400" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            {selected.size === records.length ? 'Deselect all' : 'Select all'}
          </button>
          <span className="text-slate-700 text-xs">·</span>
          <span className="text-slate-600 text-xs">Flagged shown first</span>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="card p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-brand-600 mx-auto mb-3 opacity-50" />
          <p className="text-slate-300 font-medium">Queue is empty</p>
          <p className="text-slate-500 text-sm mt-1">All records have been reviewed</p>
        </div>
      ) : (
        <div className="space-y-3">
          {records.map((record) => (
            <ReviewCard
              key={record.id}
              record={record}
              selected={selected.has(record.id)}
              onToggleSelect={() => toggleSelect(record.id)}
              onAction={(action, notes) => {
                actionMutation.mutate({ id: record.id, action, notes })
                toast.success(`Record ${action}d`)
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
