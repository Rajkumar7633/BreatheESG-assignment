import { useQuery } from '@tanstack/react-query'
import { ScrollText, CheckCircle2, XCircle, Flag, Edit2, Lock } from 'lucide-react'
import { getAuditLog } from '../api/review'
import { formatDateTime } from '../utils/formatters'
import type { ReviewDecision } from '../types'

const ACTION_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  approve:      { icon: CheckCircle2, color: 'text-brand-400',  bg: 'bg-brand-900/40' },
  bulk_approve: { icon: CheckCircle2, color: 'text-brand-400',  bg: 'bg-brand-900/40' },
  reject:       { icon: XCircle,      color: 'text-red-400',    bg: 'bg-red-900/30' },
  flag:         { icon: Flag,         color: 'text-amber-400',  bg: 'bg-amber-900/30' },
  unflag:       { icon: Flag,         color: 'text-slate-400',  bg: 'bg-slate-800' },
  edit:         { icon: Edit2,        color: 'text-blue-400',   bg: 'bg-blue-900/30' },
  lock:         { icon: Lock,         color: 'text-purple-400', bg: 'bg-purple-900/30' },
}

function DecisionRow({ decision }: { decision: ReviewDecision }) {
  const config = ACTION_CONFIG[decision.action] || ACTION_CONFIG.flag
  const Icon = config.icon

  return (
    <div className="flex items-start gap-4 py-4 border-b border-slate-800/60 last:border-0">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${config.bg}`}>
        <Icon className={`w-4 h-4 ${config.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className={`text-sm font-medium ${config.color}`}>{decision.action_display}</span>
            <span className="text-slate-500 text-sm"> by </span>
            <span className="text-slate-300 text-sm">{decision.performed_by_name}</span>
          </div>
          <span className="text-slate-600 text-xs flex-shrink-0">{formatDateTime(decision.performed_at)}</span>
        </div>
        {decision.notes && (
          <p className="text-slate-400 text-xs mt-1 italic">"{decision.notes}"</p>
        )}
        {Object.keys(decision.changes).length > 0 && (
          <div className="mt-1.5 bg-slate-800/50 rounded px-2 py-1">
            {Object.entries(decision.changes).map(([field, change]: any) => (
              <p key={field} className="text-xs text-slate-500 font-mono">
                {field}: <span className="text-red-400">{JSON.stringify(change.from)}</span>
                {' → '}
                <span className="text-brand-400">{JSON.stringify(change.to)}</span>
              </p>
            ))}
          </div>
        )}
        <p className="text-slate-600 text-xs mt-1 font-mono">
          record: {decision.emission_record.toString().slice(0, 8)}…
        </p>
      </div>
    </div>
  )
}

export default function AuditTrail() {
  const { data, isLoading } = useQuery({
    queryKey: ['audit-log'],
    queryFn: () => getAuditLog(),
    refetchInterval: 30_000,
  })

  const decisions = data?.results || []
  const total = data?.count || 0

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-purple-900/40 rounded-xl flex items-center justify-center">
          <ScrollText className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Trail</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {total} decisions recorded · immutable chain of custody
          </p>
        </div>
      </div>

      <div className="card p-1 mb-4">
        <div className="bg-purple-900/20 border border-purple-800/30 rounded-lg px-4 py-3">
          <p className="text-purple-300 text-xs">
            Every review action creates an immutable record here. No actions are updated in place —
            auditors see the complete decision history for each emission record.
          </p>
        </div>
      </div>

      <div className="card px-6 py-2">
        {isLoading ? (
          <div className="space-y-4 py-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex gap-4 items-start">
                <div className="w-8 h-8 bg-slate-800 rounded-lg animate-pulse flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-800 rounded animate-pulse w-64" />
                  <div className="h-3 bg-slate-800 rounded animate-pulse w-48" />
                </div>
              </div>
            ))}
          </div>
        ) : decisions.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            No review decisions recorded yet
          </div>
        ) : (
          decisions.map((d) => <DecisionRow key={d.id} decision={d} />)
        )}
      </div>

      {total > 500 && (
        <p className="text-slate-600 text-xs text-center mt-4">
          Showing most recent 500 of {total} decisions
        </p>
      )}
    </div>
  )
}
