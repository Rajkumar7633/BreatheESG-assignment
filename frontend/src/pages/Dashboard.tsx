import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line
} from 'recharts'
import { getSummary } from '../api/emissions'
import { formatCO2e, formatNumber, SCOPE_COLORS, SOURCE_COLORS } from '../utils/formatters'
import { TrendingUp, AlertTriangle, CheckCircle2, Clock, XCircle, Leaf } from 'lucide-react'

function StatCard({
  label, value, sub, icon: Icon, color
}: {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <p className="text-slate-400 text-sm font-medium">{label}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

const CUSTOM_TOOLTIP = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs">
        <p className="text-slate-300 font-medium mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: {formatCO2e(p.value)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: getSummary,
    refetchInterval: 30_000,
  })

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-800 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-28 bg-slate-800 rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-64 bg-slate-800 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!summary) return null

  const totalTonnes = summary.total_co2e_kg / 1000

  // Process monthly trend for chart
  const monthMap: Record<string, Record<string, number>> = {}
  summary.monthly_trend.forEach(({ month, scope, co2e_kg }) => {
    if (!month) return
    if (!monthMap[month]) monthMap[month] = {}
    monthMap[month][`scope${scope}`] = co2e_kg
  })
  const trendData = Object.entries(monthMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, scopes]) => ({
      month: month.slice(0, 7),
      ...scopes,
    }))

  // Source breakdown for pie
  const sourceData = Object.entries(summary.by_source).map(([key, val]) => ({
    name: key.toUpperCase(),
    value: val.co2e_kg,
    count: val.count,
  }))

  const scopeData = summary.by_scope.map((s) => ({
    name: s.label,
    value: s.co2e_kg,
    scope: s.scope,
  }))

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Emissions Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">2024 reporting year · location-based Scope 2</p>
        </div>
        <div className="flex items-center gap-2 bg-brand-900/30 border border-brand-800/50 rounded-xl px-4 py-2">
          <Leaf className="w-4 h-4 text-brand-400" />
          <span className="text-brand-300 font-semibold text-sm">
            {formatCO2e(summary.total_co2e_kg)}
          </span>
          <span className="text-brand-600 text-xs">total</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Records"
          value={formatNumber(summary.total_records, 0)}
          sub={`${formatNumber(summary.approved_count, 0)} approved`}
          icon={TrendingUp}
          color="bg-slate-800 text-slate-400"
        />
        <StatCard
          label="Pending Review"
          value={formatNumber(summary.pending_count, 0)}
          sub="awaiting analyst sign-off"
          icon={Clock}
          color="bg-slate-800 text-slate-400"
        />
        <StatCard
          label="Flagged"
          value={formatNumber(summary.flagged_count, 0)}
          sub="suspicious or anomalous"
          icon={AlertTriangle}
          color="bg-amber-900/40 text-amber-400"
        />
        <StatCard
          label="Rejected"
          value={formatNumber(summary.rejected_count, 0)}
          sub="excluded from totals"
          icon={XCircle}
          color="bg-red-900/30 text-red-400"
        />
      </div>

      {/* Scope breakdown cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {summary.by_scope.map((s) => (
          <div key={s.scope} className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-8 rounded-full"
                  style={{ backgroundColor: SCOPE_COLORS[s.scope] }}
                />
                <div>
                  <p className="text-white font-semibold">{s.label}</p>
                  <p className="text-slate-500 text-xs">
                    {s.scope === '1' && 'Direct combustion'}
                    {s.scope === '2' && 'Purchased electricity'}
                    {s.scope === '3' && 'Value chain & travel'}
                  </p>
                </div>
              </div>
              <span className="text-slate-500 text-xs">{s.count} records</span>
            </div>
            <p className="text-xl font-bold text-white">{formatCO2e(s.co2e_kg)}</p>
            <div className="mt-2 bg-slate-800 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full transition-all"
                style={{
                  width: `${Math.min(100, (s.co2e_kg / Math.max(summary.total_co2e_kg, 1)) * 100)}%`,
                  backgroundColor: SCOPE_COLORS[s.scope],
                }}
              />
            </div>
            <p className="text-slate-500 text-xs mt-1">
              {summary.total_co2e_kg > 0
                ? `${((s.co2e_kg / summary.total_co2e_kg) * 100).toFixed(1)}% of total`
                : '0%'}
            </p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Monthly trend */}
        <div className="card p-5 col-span-2">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Monthly Emissions Trend (tCO₂e)</h2>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={trendData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="month"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}t`}
                />
                <Tooltip content={<CUSTOM_TOOLTIP />} />
                <Bar dataKey="scope1" stackId="a" fill={SCOPE_COLORS['1']} name="Scope 1" radius={[0, 0, 0, 0]} />
                <Bar dataKey="scope2" stackId="a" fill={SCOPE_COLORS['2']} name="Scope 2" />
                <Bar dataKey="scope3" stackId="a" fill={SCOPE_COLORS['3']} name="Scope 3" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
              No data yet — upload files to get started
            </div>
          )}
        </div>

        {/* Source breakdown */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">By Data Source</h2>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={sourceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {sourceData.map((entry, i) => (
                    <Cell
                      key={entry.name}
                      fill={SOURCE_COLORS[entry.name.toLowerCase()] || '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => [formatCO2e(v), 'CO₂e']}
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-600 text-sm">No data</div>
          )}
          <div className="space-y-2 mt-2">
            {sourceData.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: SOURCE_COLORS[s.name.toLowerCase()] || '#64748b' }}
                  />
                  <span className="text-slate-400">{s.name}</span>
                  <span className="text-slate-600">({s.count})</span>
                </div>
                <span className="text-slate-300 font-mono">{formatCO2e(s.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Review status summary */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Review Status</h2>
        <div className="flex gap-6">
          {[
            { label: 'Pending', count: summary.pending_count, color: 'bg-slate-600' },
            { label: 'Approved', count: summary.approved_count, color: 'bg-brand-500' },
            { label: 'Flagged', count: summary.flagged_count, color: 'bg-amber-500' },
            { label: 'Rejected', count: summary.rejected_count, color: 'bg-red-500' },
          ].map(({ label, count, color }) => (
            <div key={label} className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${color}`} />
              <span className="text-slate-400">{label}:</span>
              <span className="text-white font-semibold">{count}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex h-2 rounded-full overflow-hidden gap-0.5">
          {[
            { count: summary.approved_count, color: 'bg-brand-500' },
            { count: summary.pending_count, color: 'bg-slate-600' },
            { count: summary.flagged_count, color: 'bg-amber-500' },
            { count: summary.rejected_count, color: 'bg-red-500' },
          ].map(({ count, color }, i) => {
            const pct = summary.total_records > 0
              ? (count / summary.total_records) * 100
              : 0
            return pct > 0 ? (
              <div key={i} className={`h-full ${color}`} style={{ width: `${pct}%` }} />
            ) : null
          })}
        </div>
      </div>
    </div>
  )
}
