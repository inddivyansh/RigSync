import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

interface User {
  user_id: string
  name: string
  role: string
  team: string
}

interface SessionContextType {
  currentUser: User | null
  setCurrentUser: (user: User) => void
  sessionId: string | null
  users: User[]
  isLoading: boolean
}

const SessionContext = createContext<SessionContextType | undefined>(undefined)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadUsers()
  }, [])

  useEffect(() => {
    if (currentUser && !sessionId) {
      createSession()
    }
  }, [currentUser])

  const loadUsers = async () => {
    try {
      const response = await axios.get('/api/users')
      setUsers(response.data.users || [])
      
      // Set default user
      if (response.data.users && response.data.users.length > 0) {
        setCurrentUser(response.data.users[0])
      }
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const createSession = async () => {
    if (!currentUser) return
    
    try {
      const response = await axios.post('/api/sessions', {
        user_id: currentUser.user_id
      })
      setSessionId(response.data.session_id)
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  return (
    <SessionContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        sessionId,
        users,
        isLoading,
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const context = useContext(SessionContext)
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider')
  }
  return context
}
