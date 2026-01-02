import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
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
  }
}

export default api