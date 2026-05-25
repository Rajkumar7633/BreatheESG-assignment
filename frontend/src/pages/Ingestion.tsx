import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Upload, FileText, CheckCircle2, XCircle, AlertTriangle, Clock, ChevronDown } from 'lucide-react'
import { getJobs, uploadFile } from '../api/ingestion'
import { formatDateTime } from '../utils/formatters'
import type { IngestionJob } from '../types'

const SOURCE_OPTIONS = [
  {
    value: 'sap',
    label: 'SAP Fuel & Procurement',
    description: 'SAP MM flat-file export (SE16N/MB51). Tab or comma separated.',
    accept: '.csv,.txt,.tsv',
    example: 'sap_mm_fuel.csv',
  },
  {
    value: 'utility',
    label: 'Utility Electricity',
    description: 'Green Button Alliance CSV export from utility portal.',
    accept: '.csv',
    example: 'utility_greenbtn.csv',
  },
  {
    value: 'travel',
    label: 'Corporate Travel',
    description: 'Concur expense report CSV export.',
    accept: '.csv',
    example: 'concur_travel_export.csv',
  },
]

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 className="w-4 h-4 text-brand-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
  partial: <AlertTriangle className="w-4 h-4 text-amber-400" />,
  processing: <Clock className="w-4 h-4 text-blue-400 animate-pulse" />,
  pending: <Clock className="w-4 h-4 text-slate-400" />,
}

export default function Ingestion() {
  const [sourceType, setSourceType] = useState('sap')
  const [region, setRegion] = useState('US')
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    refetchInterval: 10_000,
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file }: { file: File }) =>
      uploadFile(file, sourceType, sourceType === 'utility' ? region : undefined),
    onSuccess: (job) => {
      toast.success(`Upload complete: ${job.processed_rows} records processed`)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['records'] })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.error || 'Upload failed')
    },
  })

  function handleFile(file: File) {
    if (!file) return
    uploadMutation.mutate({ file })
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const selected = SOURCE_OPTIONS.find((s) => s.value === sourceType)!

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Ingest Data</h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload files from SAP, utility portals, or corporate travel platforms.
          Records are normalized and queued for analyst review.
        </p>
      </div>

      <div className="grid grid-cols-5 gap-6 mb-8">
        {/* Upload form */}
        <div className="col-span-3 space-y-4">
          {/* Source type selector */}
          <div>
            <label className="label">Data source</label>
            <div className="grid grid-cols-3 gap-2">
              {SOURCE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSourceType(opt.value)}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    sourceType === opt.value
                      ? 'border-brand-500 bg-brand-900/30 text-brand-300'
                      : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <p className="text-xs font-semibold">{opt.label}</p>
                </button>
              ))}
            </div>
          </div>

          {sourceType === 'utility' && (
            <div>
              <label className="label">Grid region (for emission factor)</label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="input"
              >
                <option value="US">US Average (EPA eGRID 2023)</option>
                <option value="UK">UK (DEFRA 2024)</option>
                <option value="EU">EU Average (EEA 2023)</option>
              </select>
            </div>
          )}

          {/* Drop zone */}
          <div>
            <label className="label">File</label>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-brand-500 bg-brand-900/20'
                  : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
              } ${uploadMutation.isPending ? 'opacity-50 pointer-events-none' : ''}`}
            >
              {uploadMutation.isPending ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-slate-400 text-sm">Processing…</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Upload className="w-8 h-8 text-slate-600" />
                  <div>
                    <p className="text-slate-300 text-sm font-medium">
                      Drop file here or click to browse
                    </p>
                    <p className="text-slate-500 text-xs mt-1">
                      Expected: <span className="font-mono">{selected.example}</span>
                    </p>
                  </div>
                </div>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept={selected.accept}
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </div>
        </div>

        {/* Source info */}
        <div className="col-span-2 card p-5 self-start">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">About this source</h3>
          <p className="text-slate-400 text-sm leading-relaxed mb-4">{selected.description}</p>
          <div className="space-y-2">
            {[
              sourceType === 'sap' && { label: 'Format', value: 'SE16N / MB51 flat file' },
              sourceType === 'sap' && { label: 'Scope', value: 'Scope 1 (fuel)' },
              sourceType === 'utility' && { label: 'Format', value: 'Green Button CSV' },
              sourceType === 'utility' && { label: 'Scope', value: 'Scope 2 (electricity)' },
              sourceType === 'travel' && { label: 'Format', value: 'Concur expense export' },
              sourceType === 'travel' && { label: 'Scope', value: 'Scope 3 (travel)' },
            ].filter(Boolean).map((item: any) => (
              <div key={item.label} className="flex justify-between text-xs">
                <span className="text-slate-500">{item.label}</span>
                <span className="text-slate-300">{item.value}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800">
            <p className="text-slate-500 text-xs">
              Sample files in <span className="font-mono text-slate-400">sample_data/</span>
            </p>
          </div>
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Recent uploads</h2>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-slate-800 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : !jobsData?.results?.length ? (
          <div className="card p-6 text-center text-slate-500 text-sm">
            No uploads yet. Upload a file to get started.
          </div>
        ) : (
          <div className="space-y-2">
            {jobsData.results.map((job: IngestionJob) => (
              <div key={job.id} className="card p-4 flex items-center gap-4">
                <div className="flex-shrink-0">
                  {STATUS_ICON[job.status]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-slate-200 text-sm font-medium truncate">{job.filename}</p>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 flex-shrink-0">
                      {job.source_type_display}
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs mt-0.5">
                    {formatDateTime(job.created_at)} · by {job.created_by_name}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="flex gap-3 text-xs">
                    <span className="text-brand-400">{job.processed_rows} ok</span>
                    {job.failed_rows > 0 && <span className="text-red-400">{job.failed_rows} failed</span>}
                    {job.flagged_rows > 0 && <span className="text-amber-400">{job.flagged_rows} flagged</span>}
                  </div>
                  <p className="text-slate-600 text-xs mt-0.5">{job.total_rows} total rows</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
