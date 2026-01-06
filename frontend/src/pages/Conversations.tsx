import { useState, useEffect } from 'react'
import { History, Trash2, Eye, MessageCircle, Calendar, User, Bot } from 'lucide-react'
import { api, ChatSession } from '../services/api'

interface ConversationDetails {
  session_id: string
  messages: Array<{
    role: string
    content: string
    timestamp: string
    message_id: string
  }>
  stats: any
}

const Conversations = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [selectedSession, setSelectedSession] = useState<ConversationDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetails, setLoadingDetails] = useState(false)

  useEffect(() => {
    fetchSessions()
  }, [])

  const fetchSessions = async () => {
    try {
      const response = await api.getChatSessions()
      if (response.success) {
        setSessions(response.sessions)
      }
    } catch (error) {
      console.error('Failed to fetch chat sessions:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSessionDetails = async (sessionId: string) => {
    setLoadingDetails(true)
    try {
      const response = await api.getChatSession(sessionId)
      if (response.success) {
        setSelectedSession(response)
      }
    } catch (error) {
      console.error('Failed to fetch session details:', error)
    } finally {
      setLoadingDetails(false)
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    if (!window.confirm('Are you sure you want to delete this chat? This action cannot be undone.')) {
      return
    }

    try {
      const response = await api.deleteChatSession(sessionId)
      if (response.success) {
        // Refresh sessions list
        await fetchSessions()
        // Close details panel if showing deleted session
        if (selectedSession?.session_id === sessionId) {
          setSelectedSession(null)
        }
        alert('Chat deleted successfully!')
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
      alert('Failed to delete chat. Please try again.')
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Chat history</h1>
        <p className="mt-2 text-gray-600">
          View and manage your saved chat conversations
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions List */}
        <div className="lg:col-span-1">
          {sessions.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <History className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No chat history</h3>
              <p className="text-gray-600">
                Start a chat session to see your conversations here.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">
                  Saved chats ({sessions.length})
                </h2>
              </div>

              <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                {sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                      selectedSession?.session_id === session.session_id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                    }`}
                    onClick={() => fetchSessionDetails(session.session_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <MessageCircle className="h-6 w-6 text-blue-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {session.session_id}
                          </p>
                          <div className="flex items-center space-x-2 text-xs text-gray-600">
                            <span>{session.total_messages} messages</span>
                            {session.last_updated && (
                              <>
                                <span>•</span>
                                <span>{formatDate(session.last_updated)}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            fetchSessionDetails(session.session_id)
                          }}
                          className="p-1 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50"
                          title="View chat"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteSession(session.session_id)
                          }}
                          className="p-1 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                          title="Delete chat"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Conversation Details */}
        <div className="lg:col-span-2">
          {selectedSession ? (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              {loadingDetails ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <div>
                  {/* Header */}
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-gray-900">
                          Chat: {selectedSession.session_id}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {selectedSession.messages.length} messages
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteSession(selectedSession.session_id)}
                        className="flex items-center space-x-2 px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="p-6">
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {selectedSession.messages.map((message) => (
                        <div
                          key={message.message_id}
                          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-md rounded-lg px-4 py-2 ${
                              message.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-900'
                            }`}
                          >
                            <div className="flex items-start space-x-2">
                              <div className={`p-1 rounded-full ${
                                message.role === 'user' ? 'bg-blue-500' : 'bg-gray-200'
                              }`}>
                                {message.role === 'user' ? (
                                  <User className="h-3 w-3 text-white" />
                                ) : (
                                  <Bot className="h-3 w-3 text-gray-600" />
                                )}
                              </div>
                              <div className="flex-1">
                                <div className="text-sm leading-relaxed">
                                  {message.content}
                                </div>
                                <div className={`text-xs mt-1 ${
                                  message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                                }`}>
                                  <Calendar className="h-3 w-3 inline mr-1" />
                                  {formatTimestamp(message.timestamp)}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <MessageCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Chat details</h3>
              <p className="text-gray-600">
                Select a chat from the list to view its messages and details.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Conversations