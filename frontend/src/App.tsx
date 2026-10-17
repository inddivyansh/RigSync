import { useState } from 'react'
import Chat from './components/Chat/Chat'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import { SessionProvider } from './contexts/SessionContext'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <SessionProvider>
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

          {/* Chat Area */}
          <main className="flex-1 overflow-hidden">
            <Chat />
          </main>
        </div>
      </div>
    </SessionProvider>
  )
}

export default App
