import { MessageSquare, Database, FileText, TrendingUp, X, AlertTriangle } from 'lucide-react'
import { useEffect, useState } from 'react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const [stats, setStats] = useState({
    totalWells: 0,
    activeWells: 0,
    violations: 0
  })

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const response = await fetch('/api/wells?limit=200')
      const data = await response.json()
      setStats({
        totalWells: data.count || 0,
        activeWells: data.wells?.filter((w: any) => w.status === 'active').length || 0,
        violations: 0
      })
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-72 bg-white border-r border-slate-200
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Close button for mobile */}
          <div className="lg:hidden flex justify-end p-4">
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-slate-600" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            <button className="w-full flex items-center gap-3 px-4 py-3 text-left bg-primary-50 text-primary-700 rounded-lg font-medium transition-colors">
              <MessageSquare className="w-5 h-5" />
              <span>Copilot Chat</span>
            </button>

            <button className="w-full flex items-center gap-3 px-4 py-3 text-left text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
              <Database className="w-5 h-5" />
              <span>Wells Database</span>
            </button>

            <button className="w-full flex items-center gap-3 px-4 py-3 text-left text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
              <FileText className="w-5 h-5" />
              <span>Reports</span>
            </button>

            <button className="w-full flex items-center gap-3 px-4 py-3 text-left text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
              <TrendingUp className="w-5 h-5" />
              <span>Analytics</span>
            </button>

            <button className="w-full flex items-center gap-3 px-4 py-3 text-left text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
              <AlertTriangle className="w-5 h-5" />
              <span>Compliance</span>
            </button>
          </nav>

          {/* Stats Panel */}
          <div className="p-4 border-t border-slate-200">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Fleet Overview
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Total Wells</span>
                <span className="text-sm font-semibold text-slate-900">{stats.totalWells}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Active</span>
                <span className="text-sm font-semibold text-green-600">{stats.activeWells}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Violations</span>
                <span className="text-sm font-semibold text-red-600">{stats.violations}</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200">
            <div className="text-xs text-slate-500 space-y-1">
              <p>RigSync v1.0.0</p>
              <p>Asset Intelligence Platform</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
