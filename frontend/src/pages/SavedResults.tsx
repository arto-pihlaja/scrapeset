import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Database, Trash2, ExternalLink, Clock, FileText, Loader2, Plus, Search, Eye, Download, X } from 'lucide-react'
import { api, ScrapeResultSummary } from '../services/api'

const MAX_ANALYSIS_LENGTH = 80000

const SavedResults = () => {
  const navigate = useNavigate()
  const [results, setResults] = useState<ScrapeResultSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [processingId, setProcessingId] = useState<number | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [viewModalData, setViewModalData] = useState<{ name: string; content: string } | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [loadingViewId, setLoadingViewId] = useState<number | null>(null)
  const [loadingDownloadId, setLoadingDownloadId] = useState<number | null>(null)

  useEffect(() => {
    fetchResults()
  }, [])

  const fetchResults = async () => {
    try {
      const response = await api.getResults()
      if (response.success) {
        setResults(response.results)
      }
    } catch (error) {
      console.error('Failed to fetch results:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateVectorDB = async (resultId: number) => {
    setProcessingId(resultId)
    try {
      const response = await api.createVectorDB(resultId)
      if (response.success) {
        alert(`Vector database created: ${response.collection_name} (${response.chunks_created} chunks)`)
        await fetchResults()
      } else {
        alert('Failed to create vector database: ' + response.error)
      }
    } catch (error) {
      console.error('Failed to create vector DB:', error)
      alert('Failed to create vector database. Please try again.')
    } finally {
      setProcessingId(null)
    }
  }

  const handleDeleteVectorDB = async (resultId: number) => {
    setProcessingId(resultId)
    try {
      const response = await api.deleteVectorDB(resultId)
      if (response.success) {
        alert('Vector database deleted')
        await fetchResults()
      } else {
        alert('Failed to delete vector database: ' + response.error)
      }
    } catch (error) {
      console.error('Failed to delete vector DB:', error)
    } finally {
      setProcessingId(null)
    }
  }

  const handleDelete = async (resultId: number) => {
    setProcessingId(resultId)
    try {
      const response = await api.deleteResult(resultId)
      if (response.success) {
        await fetchResults()
      }
    } catch (error) {
      console.error('Failed to delete result:', error)
    } finally {
      setProcessingId(null)
      setDeleteConfirmId(null)
    }
  }

  const handleAnalyze = async (resultId: number, charCount: number) => {
    if (charCount > MAX_ANALYSIS_LENGTH) {
      setAnalysisError('The text is over 80000 characters long. Select and save a smaller set for analysis.')
      setTimeout(() => setAnalysisError(null), 5000)
      return
    }
    setAnalysisError(null)

    try {
      const response = await api.getResult(resultId)
      if (response.success) {
        navigate('/analysis', {
          state: {
            savedResultData: {
              name: response.result.name,
              saved_at: response.result.saved_at,
              source_type: 'webpage',
              url: response.result.url,
              title: response.result.title || response.result.name,
              content: response.result.content,
              metadata: {}
            }
          }
        })
      }
    } catch (error) {
      console.error('Failed to get result for analysis:', error)
    }
  }

  const handleViewFullText = async (resultId: number, name: string) => {
    setLoadingViewId(resultId)
    try {
      const response = await api.getResult(resultId)
      if (response.success) {
        setViewModalData({ name, content: response.result.content })
      } else {
        setAnalysisError('Failed to load full text. Please try again.')
        setTimeout(() => setAnalysisError(null), 5000)
      }
    } catch (error) {
      console.error('Failed to load full text:', error)
      setAnalysisError('Failed to load full text. Please try again.')
      setTimeout(() => setAnalysisError(null), 5000)
    } finally {
      setLoadingViewId(null)
    }
  }

  const handleDownload = async (resultId: number, name: string) => {
    setLoadingDownloadId(resultId)
    try {
      const response = await api.getResult(resultId)
      if (response.success) {
        const blob = new Blob([response.result.content], { type: 'text/plain' })
        const downloadUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = downloadUrl
        a.download = `${name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(downloadUrl)
      } else {
        setAnalysisError('Failed to download. Please try again.')
        setTimeout(() => setAnalysisError(null), 5000)
      }
    } catch (error) {
      console.error('Failed to download:', error)
      setAnalysisError('Failed to download. Please try again.')
      setTimeout(() => setAnalysisError(null), 5000)
    } finally {
      setLoadingDownloadId(null)
    }
  }

  const handleEscapeKey = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape' && viewModalData) {
      setViewModalData(null)
    }
  }, [viewModalData])

  useEffect(() => {
    document.addEventListener('keydown', handleEscapeKey)
    return () => document.removeEventListener('keydown', handleEscapeKey)
  }, [handleEscapeKey])

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Saved Results</h1>
        <p className="mt-2 text-gray-600">
          Manage your saved scraping results and create vector databases
        </p>
      </div>

      {/* Error Message */}
      {analysisError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
          {analysisError}
        </div>
      )}

      {results.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Saved Results</h3>
          <p className="text-gray-600 mb-4">
            You haven't saved any scraping results yet. Start by scraping a website.
          </p>
          <button
            onClick={() => navigate('/scrape')}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Scrape a Website
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">
              All Results ({results.length})
            </h2>
          </div>

          <div className="divide-y divide-gray-200">
            {results.map((result) => (
              <div key={result.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-medium text-gray-900 truncate">
                        {result.name}
                      </h3>
                      {result.vector_collection ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                          <Database className="h-3 w-3 mr-1" />
                          Vector DB
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                          No Vector DB
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-500 mb-2">
                      <span className="flex items-center">
                        <ExternalLink className="h-4 w-4 mr-1" />
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-blue-600 truncate max-w-md"
                        >
                          {result.url}
                        </a>
                      </span>
                      <span className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {formatDate(result.saved_at)}
                      </span>
                      <span>{result.char_count.toLocaleString()} chars</span>
                    </div>

                    <p className="text-sm text-gray-600 line-clamp-2">
                      {result.preview}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    {/* View Full Text Button */}
                    <button
                      onClick={() => handleViewFullText(result.id, result.name)}
                      disabled={loadingViewId === result.id}
                      className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      {loadingViewId === result.id ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Eye className="h-4 w-4 mr-1" />
                      )}
                      View
                    </button>

                    {/* Download Button */}
                    <button
                      onClick={() => handleDownload(result.id, result.name)}
                      disabled={loadingDownloadId === result.id}
                      className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      {loadingDownloadId === result.id ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4 mr-1" />
                      )}
                      Download
                    </button>

                    {/* Vector DB Buttons */}
                    {!result.vector_collection ? (
                      <button
                        onClick={() => handleCreateVectorDB(result.id)}
                        disabled={processingId === result.id}
                        className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:bg-gray-400"
                      >
                        {processingId === result.id ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <Database className="h-4 w-4 mr-1" />
                        )}
                        Create Vector DB
                      </button>
                    ) : (
                      <button
                        onClick={() => handleDeleteVectorDB(result.id)}
                        disabled={processingId === result.id}
                        className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded hover:bg-orange-100 disabled:opacity-50"
                      >
                        {processingId === result.id ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4 mr-1" />
                        )}
                        Delete Vector DB
                      </button>
                    )}

                    {/* Analyze Button */}
                    <button
                      onClick={() => handleAnalyze(result.id, result.char_count)}
                      className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded hover:bg-purple-100"
                    >
                      <Search className="h-4 w-4 mr-1" />
                      Analyze
                    </button>

                    {deleteConfirmId === result.id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDelete(result.id)}
                          disabled={processingId === result.id}
                          className="px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700"
                        >
                          {processingId === result.id ? 'Deleting...' : 'Confirm'}
                        </button>
                        <button
                          onClick={() => setDeleteConfirmId(null)}
                          className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirmId(result.id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                        title="Delete result"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Full Text Modal */}
      {viewModalData && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 py-6">
            <div
              className="fixed inset-0 bg-gray-500 opacity-75"
              onClick={() => setViewModalData(null)}
            ></div>
            <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">{viewModalData.name}</h3>
                <button
                  onClick={() => setViewModalData(null)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label="Close modal"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
                  {viewModalData.content}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SavedResults
