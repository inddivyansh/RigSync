export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: {
    tool_count?: number
    citations?: {
      count: number
      by_type: Record<string, number>
    }
    conflict_count?: number
  }
  isError?: boolean
}

export interface User {
  user_id: string
  name: string
  role: string
  team: string
}

export interface Well {
  well_id: string
  well_type: string
  status: string
  area: string
  latitude: number
  longitude: number
}

export interface Session {
  session_id: string
  user_id: string
  created_at: string
  message_count: number
  correction_count: number
}
