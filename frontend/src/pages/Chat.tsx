import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, MessageCircle, Database, Settings, Trash2, Clock, User, Bot, ExternalLink } from 'lucide-react'
import { api, Collection, ChatResponse } from '../services/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    content: string
    metadata: any
    similarity: number
  }>
  timestamp: Date
}

const Chat = () => {
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollections, setSelectedCollections] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [useMemory, setUseMemory] = useState(true)
  const [sessionId, setSessionId] = useState<string>('')
  const [nResults, setNResults] = useState(5)
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchCollections()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('.collection-dropdown')) {
        setShowCollectionDropdown(false)
      }
    }

    if (showCollectionDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showCollectionDropdown])

  const fetchCollections = async () => {
    try {
      const response = await api.getCollections()
      if (response.success) {
        setCollections(response.collections)
        if (response.collections.length > 0) {
          setSelectedCollections([response.collections[0].name])
        }
      }
    } catch (error) {
      console.error('Failed to fetch collections:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(true)

    try {
      const response: ChatResponse = await api.chatWithCollection({
        message: userMessage.content,
        collections: selectedCollections.length > 0 ? selectedCollections : undefined,
        n_results: nResults,
        use_memory: useMemory,
        session_id: sessionId || undefined
      })

      if (response.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          sources: response.sources,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, assistantMessage])

        // Update session ID for memory
        if (useMemory && response.session_id) {
          setSessionId(response.session_id)
        }
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${response.error_message}`,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const clearMessages = () => {
    setMessages([])
    setSessionId('')
  }

  const toggleCollection = (collectionName: string) => {
    setSelectedCollections(prev => {
      if (prev.includes(collectionName)) {
        return prev.filter(name => name !== collectionName)
      } else {
        return [...prev, collectionName]
      }
    })
  }

  const selectAllCollections = () => {
    setSelectedCollections(collections.map(c => c.name))
  }

  const clearAllCollections = () => {
    setSelectedCollections([])
  }

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Chat</h1>
            <p className="text-gray-600">Ask questions about your scraped content</p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Collection Selector */}
            <div className="relative collection-dropdown">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-gray-400" />
                <button
                  onClick={() => setShowCollectionDropdown(!showCollectionDropdown)}
                  className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px] text-left"
                >
                  {selectedCollections.length === 0
                    ? "Select collections..."
                    : selectedCollections.length === 1
                      ? `${selectedCollections[0]} (${collections.find(c => c.name === selectedCollections[0])?.document_count || 0} docs)`
                      : `${selectedCollections.length} collections selected`
                  }
                </button>
              </div>

              {/* Dropdown */}
              {showCollectionDropdown && (
                <div className="absolute top-full left-0 mt-1 w-80 bg-white rounded-md shadow-lg border border-gray-200 z-10 max-h-64 overflow-y-auto">
                  <div className="p-2 border-b border-gray-200">
                    <div className="flex space-x-2">
                      <button
                        onClick={selectAllCollections}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        Select All
                      </button>
                      <button
                        onClick={clearAllCollections}
                        className="text-xs text-gray-600 hover:text-gray-800"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>
                  <div className="py-1">
                    {collections.map((collection) => (
                      <label
                        key={collection.id}
                        className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCollections.includes(collection.name)}
                          onChange={() => toggleCollection(collection.name)}
                          className="mr-2"
                        />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900">
                            {collection.name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {collection.document_count} documents
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Settings */}
            <div className="flex items-center space-x-2">
              <Settings className="h-5 w-5 text-gray-400" />
              <div className="flex items-center space-x-2 text-sm">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={useMemory}
                    onChange={(e) => setUseMemory(e.target.checked)}
                    className="mr-1"
                  />
                  Memory
                </label>
                <span className="text-gray-300">|</span>
                <label className="flex items-center">
                  Results:
                  <select
                    value={nResults}
                    onChange={(e) => setNResults(Number(e.target.value))}
                    className="ml-1 border border-gray-300 rounded px-2 py-0.5"
                  >
                    <option value={3}>3</option>
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                  </select>
                </label>
              </div>
            </div>

            {/* Clear Chat */}
            <button
              onClick={clearMessages}
              className="flex items-center space-x-1 text-sm text-gray-600 hover:text-red-600"
              title="Clear chat"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <MessageCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Start a Conversation</h3>
              <p className="text-gray-600 mb-4">
                {selectedCollections.length > 0
                  ? selectedCollections.length === 1
                    ? `Ask questions about the content in "${selectedCollections[0]}"`
                    : `Ask questions about content from ${selectedCollections.length} collections`
                  : 'Select one or more collections and start asking questions'}
              </p>
              {selectedCollections.length === 0 && (
                <p className="text-sm text-red-600">
                  Please select at least one collection to start chatting
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3xl rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-900 shadow border'
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    <div className={`p-1 rounded-full ${
                      message.role === 'user' ? 'bg-blue-500' : 'bg-gray-100'
                    }`}>
                      {message.role === 'user' ? (
                        <User className="h-4 w-4 text-white" />
                      ) : (
                        <Bot className="h-4 w-4 text-gray-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {message.content}
                      </div>

                      {/* Sources */}
                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-xs font-medium text-gray-600 mb-2">
                            Sources ({message.sources.length}):
                          </p>
                          <div className="space-y-2">
                            {message.sources.map((source, index) => (
                              <div key={index} className="text-xs bg-gray-50 rounded p-2">
                                <div className="flex items-center justify-between mb-1">
                                  <div className="flex items-center space-x-2">
                                    <span className="font-medium text-gray-700">
                                      Source {index + 1}
                                    </span>
                                    {source.metadata?.source_collection && (
                                      <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-medium">
                                        {source.metadata.source_collection}
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center space-x-2">
                                    <span className="text-gray-500">
                                      {Math.round(source.similarity * 100)}% match
                                    </span>
                                    {source.metadata?.source_url && (
                                      <a
                                        href={source.metadata.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800"
                                      >
                                        <ExternalLink className="h-3 w-3" />
                                      </a>
                                    )}
                                  </div>
                                </div>
                                <p className="text-gray-600 leading-relaxed">
                                  {source.content}
                                </p>
                                {source.metadata?.source_title && (
                                  <p className="text-gray-500 mt-1 font-medium">
                                    From: {source.metadata.source_title}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className={`text-xs mt-2 ${
                        message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                      }`}>
                        <Clock className="h-3 w-3 inline mr-1" />
                        {formatTimestamp(message.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                selectedCollections.length > 0
                  ? "Ask a question about your content..."
                  : "Please select collections first"
              }
              disabled={selectedCollections.length === 0 || loading}
              rows={1}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              style={{ minHeight: '38px', maxHeight: '120px' }}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || selectedCollections.length === 0 || loading}
              className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>

          {useMemory && sessionId && (
            <p className="text-xs text-gray-500 mt-2">
              Session: {sessionId} (memory enabled)
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default Chat