import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from './api/client'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Ingestion from './pages/Ingestion'
import Review from './pages/Review'
import Records from './pages/Records'
import AuditTrail from './pages/AuditTrail'
import Login from './pages/Login'
import type { User } from './types'

function useCurrentUser() {
  return useQuery<User>({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await apiClient.get('/core/me/')
      return data
    },
    retry: false,
    enabled: !!localStorage.getItem('access_token'),
  })
}

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading, isError } = useCurrentUser()

  if (!localStorage.getItem('access_token')) {
    return <Navigate to="/login" replace />
  }
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          Loading…
        </div>
      </div>
    )
  }
  if (isError) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <AuthGuard>
              <Layout />
            </AuthGuard>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="ingestion" element={<Ingestion />} />
          <Route path="review" element={<Review />} />
          <Route path="records" element={<Records />} />
          <Route path="audit" element={<AuditTrail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
