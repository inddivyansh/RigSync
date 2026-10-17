import { Menu, Settings, User } from 'lucide-react'
import { useSession } from '../../contexts/SessionContext'

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { currentUser, users, setCurrentUser } = useSession()

  return (
    <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="p-2 hover:bg-slate-100 rounded-lg transition-colors lg:hidden"
          aria-label="Toggle menu"
        >
          <Menu className="w-5 h-5 text-slate-600" />
        </button>

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
            <span className="text-white font-semibold text-sm">RS</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-900">RigSync</h1>
            <p className="text-xs text-slate-500">Asset Intelligence Platform</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* User Selector */}
        <div className="relative">
          <select
            value={currentUser?.user_id || ''}
            onChange={(e) => {
              const user = users.find(u => u.user_id === e.target.value)
              if (user) setCurrentUser(user)
            }}
            className="appearance-none bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all cursor-pointer"
          >
            {users.map((user) => (
              <option key={user.user_id} value={user.user_id}>
                {user.name} ({user.role})
              </option>
            ))}
          </select>
          <User className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>

        {/* Settings Button */}
        <button
          className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          aria-label="Settings"
        >
          <Settings className="w-5 h-5 text-slate-600" />
        </button>
      </div>
    </header>
  )
}
