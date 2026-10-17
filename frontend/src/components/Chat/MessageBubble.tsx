import { Message } from '../../types'
import { User, Bot, Database, FileText, GitBranch, Calculator, Shield, Brain, AlertTriangle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
        </div>
      )}

      <div className={`flex-1 max-w-3xl ${isUser ? 'flex justify-end' : ''}`}>
        <div
          className={`
            rounded-2xl px-5 py-4 
            ${isUser 
              ? 'bg-primary-600 text-white' 
              : message.isError
                ? 'bg-red-50 border border-red-200 text-red-900'
                : 'bg-white border border-slate-200 text-slate-900'
            }
            ${isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'}
          `}
        >
          <div className="prose prose-sm max-w-none">
            {isUser ? (
              <p className="text-white whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-slate-700">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
                  code: ({ children }) => (
                    <code className="px-1.5 py-0.5 bg-slate-100 text-slate-800 rounded text-xs font-mono">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-slate-100 p-3 rounded-lg overflow-x-auto mb-3">
                      {children}
                    </pre>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Metadata */}
          {!isUser && message.metadata && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              {/* Tools Used */}
              {(message.metadata.tool_count ?? 0) > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                    <Brain className="w-3.5 h-3.5" />
                    <span className="font-medium">Analysis</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <ToolBadge icon={Database} label={`${message.metadata.tool_count} tools`} />
                  </div>
                </div>
              )}

              {/* Citations */}
              {message.metadata.citations && message.metadata.citations.count > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                    <FileText className="w-3.5 h-3.5" />
                    <span className="font-medium">Sources</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {message.metadata.citations.by_type && Object.entries(message.metadata.citations.by_type).map(([type, count]) => {
                      if (count === 0) return null
                      return (
                        <SourceBadge
                          key={type}
                          type={type}
                          count={count as number}
                        />
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Conflicts */}
              {(message.metadata.conflict_count ?? 0) > 0 && (
                <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span className="text-xs text-amber-800 font-medium">
                    {message.metadata.conflict_count} data conflict(s) detected
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          <div className={`mt-2 text-xs ${isUser ? 'text-primary-200' : 'text-slate-400'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
            <User className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
    </div>
  )
}

function ToolBadge({ icon: Icon, label }: { icon: any; label: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-md">
      <Icon className="w-3.5 h-3.5 text-slate-600" />
      <span className="text-xs text-slate-700 font-medium">{label}</span>
    </div>
  )
}

function SourceBadge({ type, count }: { type: string; count: number }) {
  const icons: Record<string, any> = {
    database: Database,
    vector: FileText,
    graph: GitBranch,
    calculation: Calculator,
    rules: Shield,
    memory: Brain,
    conflict: AlertTriangle,
  }

  const Icon = icons[type] || FileText

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 border border-blue-200 rounded-md">
      <Icon className="w-3.5 h-3.5 text-blue-600" />
      <span className="text-xs text-blue-700 font-medium">
        {type} ({count})
      </span>
    </div>
  )
}
