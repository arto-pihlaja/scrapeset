import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ClipboardList,
  Youtube,
  Globe,
  Trash2,
  ExternalLink,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import api, { AnalysisHistoryItem } from '../services/api'

const AnalysisHistory = () => {
  const navigate = useNavigate()
  const [analyses, setAnalyses] = useState<AnalysisHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [deleting, setDeleting] = useState<string | null>(null)
  const limit = 20

  const loadAnalyses = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.getAnalysisHistory({ limit, offset })
      if (result.success) {
        setAnalyses(result.analyses)
        setTotal(result.total)
      } else {
        setError('Failed to load analysis history')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnalyses()
  }, [offset])

  const handleDelete = async (analysisId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this analysis?')) return

    setDeleting(analysisId)
    try {
      const result = await api.deleteAnalysis(analysisId)
      if (result.success) {
        setAnalyses(prev => prev.filter(a => a.id !== analysisId))
        setTotal(prev => prev - 1)
      } else {
        setError('Failed to delete analysis')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete analysis')
    } finally {
      setDeleting(null)
    }
  }

  const handleView = (analysis: AnalysisHistoryItem) => {
    // Navigate to ArgumentAnalysis with URL parameter
    navigate(`/analysis?url=${encodeURIComponent(analysis.url)}`)
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown'
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    return date.toLocaleDateString()
  }

  const truncate = (text: string | null, maxLength: number) => {
    if (!text) return ''
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
  }

  const filteredAnalyses = analyses.filter(a =>
    !searchQuery ||
    (a.title?.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (a.url?.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (a.executive_summary?.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <ClipboardList className="h-7 w-7 text-blue-600" />
              Analysis History
            </h1>
            <p className="text-gray-500 mt-1">View and manage your previous content analyses</p>
          </div>
          <div className="text-sm text-gray-500">
            {total} total {total === 1 ? 'analysis' : 'analyses'}
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by title, URL, or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-500">Loading analyses...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredAnalyses.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl border">
          <ClipboardList className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900 mb-1">No analyses found</h3>
          <p className="text-gray-500 mb-4">
            {searchQuery
              ? 'Try a different search term'
              : 'Run an analysis from Saved Results to see it here'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => navigate('/saved-results')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
            >
              Go to Saved Results
            </button>
          )}
        </div>
      )}

      {/* Analysis List */}
      {!loading && filteredAnalyses.length > 0 && (
        <div className="space-y-3">
          {filteredAnalyses.map((analysis) => (
            <div
              key={analysis.id}
              onClick={() => handleView(analysis)}
              className="bg-white p-4 rounded-lg border shadow-sm hover:shadow-md hover:border-blue-200 transition-all cursor-pointer"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Title and Source Type */}
                  <div className="flex items-center gap-2 mb-1">
                    {analysis.source_type === 'youtube' ? (
                      <Youtube className="h-4 w-4 text-red-500 flex-shrink-0" />
                    ) : (
                      <Globe className="h-4 w-4 text-blue-500 flex-shrink-0" />
                    )}
                    <h3 className="font-semibold text-gray-900 truncate">
                      {analysis.title || 'Untitled'}
                    </h3>
                    {analysis.status === 'completed' && (
                      <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full flex-shrink-0">
                        Completed
                      </span>
                    )}
                    {analysis.status === 'pending' && (
                      <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full flex-shrink-0">
                        Pending
                      </span>
                    )}
                  </div>

                  {/* URL */}
                  <p className="text-xs text-gray-400 truncate mb-2">{analysis.url}</p>

                  {/* Summary Preview */}
                  {analysis.executive_summary && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {truncate(analysis.executive_summary, 200)}
                    </p>
                  )}

                  {/* Date */}
                  <p className="text-xs text-gray-400 mt-2">
                    Analyzed: {formatDate(analysis.completed_at || analysis.created_at)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      window.open(analysis.url, '_blank')
                    }}
                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    title="Open source URL"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(analysis.id, e)}
                    disabled={deleting === analysis.id}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Delete analysis"
                  >
                    {deleting === analysis.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-lg border">
          <div className="text-sm text-gray-500">
            Showing {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm text-gray-600">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default AnalysisHistory
