import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import axios from 'axios'
import { useSession } from '../../contexts/SessionContext'
import MessageList from './MessageList'
import { Message } from '../../types'

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { currentUser, sessionId } = useSession()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !currentUser || !sessionId) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await axios.post('/api/chat', {
        query: userMessage.content,
        session_id: sessionId,
        user_id: currentUser.user_id,
      })

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        metadata: response.data.metadata,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                Welcome to RigSync
              </h2>
              <p className="text-slate-600 max-w-md">
                Ask me anything about your wells, production status, compliance, or maintenance history.
                I can provide detailed insights backed by your operational data.
              </p>
              <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                <ExampleQuery
                  text="Is WELL-0001 producing oil right now?"
                  onClick={() => setInput("Is WELL-0001 producing oil right now?")}
                />
                <ExampleQuery
                  text="Which wells in Northeast Block 8 are not producing?"
                  onClick={() => setInput("Which wells in Northeast Block 8 are not producing?")}
                />
                <ExampleQuery
                  text="Show me compliance violations for WELL-0001"
                  onClick={() => setInput("Show me compliance violations for WELL-0001")}
                />
                <ExampleQuery
                  text="What was WELL-0001's downtime in 2025?"
                  onClick={() => setInput("What was WELL-0001's downtime in 2025?")}
                />
              </div>
            </div>
          ) : (
            <MessageList messages={messages} />
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-200 bg-white px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about well status, production, compliance..."
              disabled={isLoading || !currentUser}
              rows={1}
              className="w-full px-4 py-3 pr-12 border border-slate-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed transition-all"
              style={{
                minHeight: '52px',
                maxHeight: '200px',
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading || !currentUser}
              className="absolute right-2 bottom-2 p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
          <p className="mt-2 text-xs text-slate-500 text-center">
            Responses are generated based on your operational data and may require verification for critical decisions.
          </p>
        </div>
      </div>
    </div>
  )
}

function ExampleQuery({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-left p-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors group"
    >
      <p className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors">
        {text}
      </p>
    </button>
  )
}

function MessageSquare({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
      />
    </svg>
  )
}
