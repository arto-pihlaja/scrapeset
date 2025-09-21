import { useState, useEffect } from 'react'
import { Database, Trash2, Eye, ExternalLink, FileText, Clock, X, MoreVertical } from 'lucide-react'
import { api, Collection, CollectionStats } from '../services/api'

interface CollectionWithStats extends Collection {
  sources?: Array<{ url: string; title: string; chunk_count: number }>
  stats?: CollectionStats
}

const Collections = () => {
  const [collections, setCollections] = useState<CollectionWithStats[]>([])
  const [selectedCollection, setSelectedCollection] = useState<CollectionWithStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingStats, setLoadingStats] = useState(false)

  useEffect(() => {
    fetchCollections()
  }, [])

  const fetchCollections = async () => {
    try {
      const response = await api.getCollections()
      if (response.success) {
        setCollections(response.collections)
      }
    } catch (error) {
      console.error('Failed to fetch collections:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchCollectionDetails = async (collection: Collection) => {
    setLoadingStats(true)
    try {
      const response = await api.getCollectionStats(collection.name)
      if (response.success) {
        const collectionWithStats: CollectionWithStats = {
          ...collection,
          stats: response.stats,
          sources: response.sources
        }
        setSelectedCollection(collectionWithStats)
      }
    } catch (error) {
      console.error('Failed to fetch collection details:', error)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleClearCollection = async (collectionName: string) => {
    if (!window.confirm(`Are you sure you want to clear all documents from "${collectionName}"? This will remove all documents but keep the collection structure.`)) {
      return
    }

    try {
      const response = await api.clearCollection(collectionName)
      if (response.success) {
        // Refresh collections list
        await fetchCollections()
        // Close details panel if showing cleared collection
        if (selectedCollection?.name === collectionName) {
          setSelectedCollection(null)
        }
        alert('Collection cleared successfully!')
      }
    } catch (error) {
      console.error('Failed to clear collection:', error)
      alert('Failed to clear collection. Please try again.')
    }
  }

  const handleDropCollection = async (collectionName: string) => {
    if (!window.confirm(`Are you sure you want to DROP the entire collection "${collectionName}"? This will completely remove the collection and all its documents. This action cannot be undone.`)) {
      return
    }

    try {
      const response = await api.dropCollection(collectionName)
      if (response.success) {
        // Refresh collections list
        await fetchCollections()
        // Close details panel if showing dropped collection
        if (selectedCollection?.name === collectionName) {
          setSelectedCollection(null)
        }
        alert('Collection dropped successfully!')
      }
    } catch (error) {
      console.error('Failed to drop collection:', error)
      alert('Failed to drop collection. Please try again.')
    }
  }

  // Backward compatibility
  const handleDeleteCollection = handleClearCollection

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
        <h1 className="text-3xl font-bold text-gray-900">Collections</h1>
        <p className="mt-2 text-gray-600">
          Manage your document collections and view their contents
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Collections List */}
        <div className="lg:col-span-2">
          {collections.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <Database className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Collections Found</h3>
              <p className="text-gray-600 mb-4">
                You haven't created any collections yet. Start by scraping a website.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">
                  All Collections ({collections.length})
                </h2>
              </div>

              <div className="divide-y divide-gray-200">
                {collections.map((collection) => (
                  <div
                    key={collection.id}
                    className={`p-6 hover:bg-gray-50 cursor-pointer transition-colors ${
                      selectedCollection?.id === collection.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                    }`}
                    onClick={() => fetchCollectionDetails(collection)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Database className="h-8 w-8 text-blue-500" />
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">
                            {collection.name}
                          </h3>
                          <div className="flex items-center space-x-4 text-sm text-gray-600">
                            <span className="flex items-center">
                              <FileText className="h-4 w-4 mr-1" />
                              {collection.document_count} documents
                            </span>
                            <span className="flex items-center">
                              <Clock className="h-4 w-4 mr-1" />
                              ID: {collection.id.toString().substring(0, 8)}...
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            fetchCollectionDetails(collection)
                          }}
                          className="p-2 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50"
                          title="View details"
                        >
                          <Eye className="h-5 w-5" />
                        </button>

                        {/* Dropdown menu for actions */}
                        <div className="relative group">
                          <button
                            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-50"
                            title="Collection actions"
                          >
                            <MoreVertical className="h-5 w-5" />
                          </button>

                          {/* Dropdown content */}
                          <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                            <div className="py-1">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleClearCollection(collection.name)
                                }}
                                className="flex items-center w-full px-4 py-2 text-sm text-orange-700 hover:bg-orange-50"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Clear Documents
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDropCollection(collection.name)
                                }}
                                className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                              >
                                <X className="h-4 w-4 mr-2" />
                                Drop Collection
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Collection Details */}
        <div className="lg:col-span-1">
          {selectedCollection ? (
            <div className="bg-white rounded-lg shadow p-6">
              {loadingStats ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Collection Info */}
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4">
                      {selectedCollection.name}
                    </h3>

                    {selectedCollection.stats && (
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Documents:</span>
                          <span className="text-sm font-medium">
                            {selectedCollection.stats.document_count}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Storage:</span>
                          <span className="text-sm font-medium">
                            {selectedCollection.stats.persist_directory}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Sources */}
                  {selectedCollection.sources && selectedCollection.sources.length > 0 && (
                    <div>
                      <h4 className="text-md font-medium text-gray-900 mb-3">
                        Sources ({selectedCollection.sources.length})
                      </h4>
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        {selectedCollection.sources.map((source, index) => (
                          <div key={index} className="border border-gray-200 rounded-lg p-3">
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {source.title || 'Untitled'}
                                </p>
                                <p className="text-xs text-gray-600 mt-1">
                                  {source.chunk_count} chunks
                                </p>
                              </div>
                              {source.url && source.url !== 'Unknown' && (
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="ml-2 text-gray-400 hover:text-blue-600"
                                  title="Open source URL"
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              )}
                            </div>
                            {source.url && source.url !== 'Unknown' && (
                              <p className="text-xs text-gray-500 mt-2 truncate">
                                {source.url}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="space-y-2">
                    <button
                      onClick={() => handleClearCollection(selectedCollection.name)}
                      className="w-full flex items-center justify-center px-4 py-2 border border-orange-300 text-sm font-medium rounded-md text-orange-700 bg-white hover:bg-orange-50"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Clear Documents
                    </button>
                    <button
                      onClick={() => handleDropCollection(selectedCollection.name)}
                      className="w-full flex items-center justify-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Drop Collection
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6 text-center">
              <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Collection Details</h3>
              <p className="text-gray-600">
                Select a collection from the list to view its details and sources.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Collections