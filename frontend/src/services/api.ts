import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000,  // 10 minutes for long-running operations
})

// Request interceptor
axiosInstance.interceptors.request.use((config) => {
  // Add auth headers if needed
  return config
})

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface ScrapeRequest {
  url: string
  collection?: string
  interactive?: boolean
  dynamic?: boolean
}

export interface ScrapeResponse {
  success: boolean
  title: string
  text_elements: Array<{
    id: number
    content: string
    tag: string
    preview: string
    word_count: number
    char_count: number
  }>
  total_text_length: number
  error_message?: string
}

export interface QueryRequest {
  question: string
  collection?: string
  n_results?: number
}

export interface QueryResponse {
  answer: string
  sources: Array<{
    content: string
    metadata: any
    similarity: number
  }>
  success: boolean
  error_message?: string
}

export interface ChatRequest {
  message: string
  collection?: string
  collections?: string[]
  n_results?: number
  use_memory?: boolean
  session_id?: string
}

export interface ChatResponse {
  response: string
  sources: Array<{
    content: string
    metadata: any
    similarity: number
  }>
  session_id: string
  success: boolean
  collections_used?: string[]
  results_per_collection?: { [key: string]: number }
  error_message?: string
}

export interface Collection {
  name: string
  id: string
  document_count: number
  metadata?: any
}

export interface CollectionStats {
  collection_name: string
  document_count: number
  persist_directory: string
}

export interface ChatSession {
  session_id: string
  total_messages: number
  last_updated?: string
}

export interface ScrapeResultSummary {
  id: number
  name: string
  url: string
  title: string | null
  char_count: number
  saved_at: string
  vector_collection: string | null
  preview: string
}

export interface ScrapeResultFull {
  id: number
  name: string
  url: string
  title: string | null
  content: string
  char_count: number
  saved_at: string
  vector_collection: string | null
}

export const api = {
  // Health check
  async healthCheck() {
    const response = await axiosInstance.get('/health')
    return response.data
  },

  // Collections
  async getCollections(): Promise<{ success: boolean; collections: Collection[] }> {
    const response = await axiosInstance.get('/collections')
    return response.data
  },

  async getCollectionStats(collectionName: string): Promise<{
    success: boolean
    stats: CollectionStats
    sources: Array<{ url: string; title: string; chunk_count: number }>
  }> {
    const response = await axiosInstance.get(`/collections/${collectionName}/stats`)
    return response.data
  },

  async clearCollection(collectionName: string): Promise<{ success: boolean; operation: string }> {
    const response = await axiosInstance.delete(`/collections/${collectionName}`)
    return response.data
  },

  async dropCollection(collectionName: string): Promise<{ success: boolean; operation: string }> {
    const response = await axiosInstance.delete(`/collections/${collectionName}/drop`)
    return response.data
  },

  async getCollectionContent(
    collectionName: string,
    limit: number = 100,
    offset: number = 0,
    url?: string
  ): Promise<{
    success: boolean
    content: Array<{
      id: string
      document: string
      metadata: any
    }>
  }> {
    const params: any = { limit, offset }
    if (url) params.url = url
    const response = await axiosInstance.get(`/collections/${collectionName}/content`, { params })
    return response.data
  },

  // Backward compatibility
  async deleteCollection(collectionName: string): Promise<{ success: boolean }> {
    const response = await axiosInstance.delete(`/collections/${collectionName}`)
    return response.data
  },

  // Scraping
  async scrapeUrl(request: ScrapeRequest): Promise<ScrapeResponse> {
    const response = await axiosInstance.post('/scrape', request)
    return response.data
  },

  async addToCollection(data: {
    url: string
    title: string
    selected_elements: any[]
    collection?: string
  }): Promise<{
    success: boolean
    chunks_created?: number
    collection_stats?: CollectionStats
    error?: string
  }> {
    const response = await axiosInstance.post('/scrape/add-to-collection', data)
    return response.data
  },

  // Querying
  async queryCollection(request: QueryRequest): Promise<QueryResponse> {
    const response = await axiosInstance.post('/query', request)
    return response.data
  },

  // Chat
  async chatWithCollection(request: ChatRequest): Promise<ChatResponse> {
    const response = await axiosInstance.post('/chat', request)
    return response.data
  },

  async getChatSessions(): Promise<{ success: boolean; sessions: ChatSession[] }> {
    const response = await axiosInstance.get('/chat/sessions')
    return response.data
  },

  async getChatSession(sessionId: string): Promise<{
    success: boolean
    session_id: string
    messages: Array<{
      role: string
      content: string
      timestamp: string
      message_id: string
    }>
    stats: any
  }> {
    const response = await axiosInstance.get(`/chat/sessions/${sessionId}`)
    return response.data
  },

  async deleteChatSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    const response = await axiosInstance.delete(`/chat/sessions/${sessionId}`)
    return response.data
  },

  // Analysis
  async runAnalysisStep(data: {
    step: string
    url?: string
    text?: string
    previous_data?: any
  }): Promise<{ success: boolean; data?: any; error?: string }> {
    const response = await axiosInstance.post('/analysis/step', data)
    return response.data
  },

  // Analysis with SSE streaming for progress updates
  async runAnalysisStepWithProgress(
    data: {
      step: string
      url?: string
      text?: string
      previous_data?: any
    },
    onProgress: (message: string, progress: number) => void
  ): Promise<{ success: boolean; data?: any; error?: string }> {
    const response = await fetch(`${API_BASE_URL}/analysis/step/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      return { success: false, error: `HTTP error: ${response.status}` }
    }

    const reader = response.body?.getReader()
    if (!reader) {
      return { success: false, error: 'No response body' }
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''  // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'progress') {
              onProgress(event.message, event.progress)
            } else if (event.type === 'complete') {
              return { success: true, data: event.data }
            } else if (event.type === 'error') {
              return { success: false, error: event.error }
            }
            // Ignore heartbeat events
          } catch (e) {
            console.warn('Failed to parse SSE event:', line)
          }
        }
      }
    }

    return { success: false, error: 'Stream ended unexpectedly' }
  },

  // Saved Results
  async saveResult(data: {
    name: string
    url: string
    title?: string
    content: string
  }): Promise<{ success: boolean; result_id?: number; error_message?: string }> {
    const response = await axiosInstance.post('/results/save', data)
    return response.data
  },

  async getResults(): Promise<{ success: boolean; results: ScrapeResultSummary[] }> {
    const response = await axiosInstance.get('/results')
    return response.data
  },

  async getResult(resultId: number): Promise<{ success: boolean; result: ScrapeResultFull }> {
    const response = await axiosInstance.get(`/results/${resultId}`)
    return response.data
  },

  async deleteResult(resultId: number): Promise<{ success: boolean; message: string }> {
    const response = await axiosInstance.delete(`/results/${resultId}`)
    return response.data
  },

  async createVectorDB(
    resultId: number,
    collectionName?: string
  ): Promise<{
    success: boolean
    collection_name?: string
    chunks_created?: number
    stats?: any
    error?: string
  }> {
    const response = await axiosInstance.post(`/results/${resultId}/create-vector-db`, {
      collection_name: collectionName
    })
    return response.data
  },

  async deleteVectorDB(resultId: number): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await axiosInstance.delete(`/results/${resultId}/vector-db`)
    return response.data
  }
}

export default api