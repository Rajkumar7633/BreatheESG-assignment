import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, logout } from '../api/client'
import {
  LayoutDashboard, Upload, ClipboardCheck, Database,
  ScrollText, Leaf, LogOut, Bell, ChevronRight
} from 'lucide-react'
import type { User } from '../types'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/ingestion', icon: Upload, label: 'Ingest Data' },
  { to: '/review', icon: ClipboardCheck, label: 'Review Queue' },
  { to: '/records', icon: Database, label: 'All Records' },
  { to: '/audit', icon: ScrollText, label: 'Audit Trail' },
]

export default function Layout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: user } = useQuery<User>({
    queryKey: ['me'],
    queryFn: async () => {
      const { data } = await apiClient.get('/core/me/')
      return data
    },
  })

  function handleLogout() {
    logout()
    queryClient.clear()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <Leaf className="w-4 h-4 text-white" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-white text-sm leading-none">BreatheESG</p>
              <p className="text-slate-500 text-xs mt-0.5 truncate">{user?.organization?.name || 'Loading…'}</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group ${
                  isActive
                    ? 'bg-brand-600/20 text-brand-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-brand-400' : ''}`} />
                  {label}
                  {isActive && <ChevronRight className="w-3 h-3 ml-auto text-brand-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="p-3 border-t border-slate-800">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 mb-1">
            <div className="w-7 h-7 rounded-full bg-brand-700 flex items-center justify-center text-xs font-bold text-brand-200 flex-shrink-0">
              {user?.first_name?.[0] || user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-slate-200 text-xs font-medium truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username}
              </p>
              <p className="text-slate-500 text-xs capitalize">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 w-full rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-900/20 text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
