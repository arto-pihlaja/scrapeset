import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, Loader2, CheckCircle, XCircle, Download, ArrowRight, Save } from 'lucide-react'
import { api, ScrapeResponse } from '../services/api'

const ScrapeWeb = () => {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [scrapeResult, setScrapeResult] = useState<ScrapeResponse | null>(null)
  const [dynamic, setDynamic] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveName, setSaveName] = useState('')

  const handleScrape = async () => {
    if (!url.trim()) return

    setLoading(true)
    setScrapeResult(null)
    try {
      const result = await api.scrapeUrl({
        url: url.trim(),
        interactive: true,
        dynamic: dynamic
      })
      setScrapeResult(result)
    } catch (error) {
      console.error('Scraping failed:', error)
      setScrapeResult({
        success: false,
        title: '',
        text_elements: [],
        total_text_length: 0,
        error_message: 'Failed to scrape URL. Please check the URL and try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  const getFullContent = () => {
    if (!scrapeResult?.success) return ''
    return scrapeResult.text_elements.map(el => el.content).join('\n\n')
  }

  const handleDownload = () => {
    if (!scrapeResult?.success) return
    const fullText = getFullContent()
    const blob = new Blob([fullText], { type: 'text/plain' })
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `${scrapeResult.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
  }

  const handleAnalyzeContent = () => {
    if (!scrapeResult?.success) return
    const fullContent = getFullContent()
    navigate('/analysis', {
      state: {
        preScrapedData: {
          source_type: 'webpage',
          url: url.trim(),
          title: scrapeResult.title,
          content: fullContent,
          metadata: {}
        }
      }
    })
  }

  const handleSaveResults = async () => {
    if (!scrapeResult?.success || !saveName.trim()) return

    setSaving(true)
    try {
      const fullContent = getFullContent()
      const result = await api.saveResult({
        name: saveName.trim(),
        url: url.trim(),
        title: scrapeResult.title,
        content: fullContent
      })

      if (result.success) {
        setShowSaveModal(false)
        setSaveName('')
        navigate('/saved-results')
      } else {
        alert('Failed to save: ' + result.error_message)
      }
    } catch (error) {
      console.error('Failed to save results:', error)
      alert('Failed to save results. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Scrape Website</h1>
        <p className="mt-2 text-gray-600">
          Extract content from any website and save it for later use
        </p>
      </div>

      {/* URL Input Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Website Details</h2>

        <div className="space-y-4">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700">
              Website URL
            </label>
            <input
              type="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="dynamic"
              checked={dynamic}
              onChange={(e) => setDynamic(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="dynamic" className="text-sm font-medium text-gray-700">
              Enable Dynamic Scraping (with Playwright)
            </label>
          </div>

          <button
            onClick={handleScrape}
            disabled={loading || !url.trim()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Globe className="h-4 w-4 mr-2" />
            )}
            {loading ? 'Scraping...' : 'Start Scraping'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {scrapeResult && (
        <div className="bg-white rounded-lg shadow p-6">
          {scrapeResult.success ? (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <h2 className="text-lg font-medium text-gray-900">Scraping Successful</h2>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-medium text-gray-900">{scrapeResult.title}</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Found {scrapeResult.text_elements.length} text elements
                  ({scrapeResult.total_text_length.toLocaleString()} characters total)
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download as Text
                  </button>
                  <button
                    onClick={() => setShowSaveModal(true)}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent shadow-sm text-sm font-medium rounded text-white bg-green-600 hover:bg-green-700"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save Results
                  </button>
                  <button
                    onClick={handleAnalyzeContent}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent shadow-sm text-sm font-medium rounded text-white bg-purple-600 hover:bg-purple-700"
                  >
                    <ArrowRight className="h-4 w-4 mr-2" />
                    Analyze Content
                  </button>
                </div>
              </div>

              {/* Content Preview */}
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Scraped Content Preview</h3>
                <div className="bg-gray-50 p-4 rounded border border-gray-200 h-64 overflow-y-auto whitespace-pre-wrap font-mono text-sm text-gray-700">
                  {getFullContent()}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <XCircle className="h-5 w-5 text-red-500" />
                <h2 className="text-lg font-medium text-gray-900">Scraping Failed</h2>
              </div>
              <p className="text-red-600">{scrapeResult.error_message}</p>
            </div>
          )}
        </div>
      )}

      {/* Save Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-gray-500 opacity-75"
              onClick={() => setShowSaveModal(false)}
            ></div>
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Save Scraping Results</h3>
              <div className="space-y-4">
                <div>
                  <label htmlFor="saveName" className="block text-sm font-medium text-gray-700">
                    Name for this result
                  </label>
                  <input
                    type="text"
                    id="saveName"
                    value={saveName}
                    onChange={(e) => setSaveName(e.target.value)}
                    placeholder="e.g., Research Article on AI"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && saveName.trim()) {
                        handleSaveResults()
                      }
                    }}
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowSaveModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveResults}
                    disabled={saving || !saveName.trim()}
                    className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:bg-gray-400"
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ScrapeWeb
