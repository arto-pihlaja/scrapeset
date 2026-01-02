import { useState } from 'react'
import { Globe, Loader2, CheckCircle, XCircle, Download } from 'lucide-react'
import { api, ScrapeResponse } from '../services/api'

interface TextElement {
  id: number
  content: string
  tag: string
  preview: string
  word_count: number
  char_count: number
  selected?: boolean
}

const ScrapeWeb = () => {
  const [url, setUrl] = useState('')
  const [collection, setCollection] = useState('')
  const [loading, setLoading] = useState(false)
  const [scrapeResult, setScrapeResult] = useState<ScrapeResponse | null>(null)
  const [textElements, setTextElements] = useState<TextElement[]>([])
  const [processing, setProcessing] = useState(false)
  const [dynamic, setDynamic] = useState(false)

  const handleScrape = async () => {
    if (!url.trim()) return

    setLoading(true)
    try {
      const result = await api.scrapeUrl({
        url: url.trim(),
        collection: collection.trim() || undefined,
        interactive: true,
        dynamic: dynamic
      })

      setScrapeResult(result)

      if (result.success) {
        const elementsWithSelection = result.text_elements.map(el => ({
          ...el,
          selected: true // Default to selected
        }))
        setTextElements(elementsWithSelection)
      }
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

  const toggleElement = (id: number) => {
    setTextElements(prev =>
      prev.map(el =>
        el.id === id ? { ...el, selected: !el.selected } : el
      )
    )
  }

  const selectAll = () => {
    setTextElements(prev => prev.map(el => ({ ...el, selected: true })))
  }

  const deselectAll = () => {
    setTextElements(prev => prev.map(el => ({ ...el, selected: false })))
  }

  const handleAddToCollection = async () => {
    if (!scrapeResult?.success) return

    const selectedElements = textElements.filter(el => el.selected)
    if (selectedElements.length === 0) {
      alert('Please select at least one text element.')
      return
    }

    setProcessing(true)
    try {
      const result = await api.addToCollection({
        url: url.trim(),
        title: scrapeResult.title,
        selected_elements: selectedElements,
        collection: collection.trim() || undefined
      })

      if (result.success) {
        alert(`Successfully added ${result.chunks_created} chunks to collection!`)
        // Reset form
        setUrl('')
        setCollection('')
        setScrapeResult(null)
        setTextElements([])
      } else {
        alert('Failed to add to collection: ' + result.error)
      }
    } catch (error) {
      console.error('Failed to add to collection:', error)
      alert('Failed to add to collection. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  const handleDownload = () => {
    if (!scrapeResult?.success) return

    const fullText = textElements.map(el => el.content).join('\n\n')
    const blob = new Blob([fullText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${scrapeResult.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const selectedCount = textElements.filter(el => el.selected).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Scrape Website</h1>
        <p className="mt-2 text-gray-600">
          Extract content from any website and add it to your collection
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

          <div>
            <label htmlFor="collection" className="block text-sm font-medium text-gray-700">
              Collection Name (optional)
            </label>
            <input
              type="text"
              id="collection"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
              placeholder="Leave empty to use default collection"
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
                <div className="mt-2">
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download as Plain Text
                  </button>
                </div>
              </div>

              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Scraped Text Preview</h3>
                <div
                  className="bg-gray-50 p-4 rounded border border-gray-200 h-64 overflow-y-auto whitespace-pre-wrap font-mono text-sm text-gray-700"
                  id="scraped-text-preview"
                >
                  {scrapeResult.text_elements.map(el => el.content).join('\n\n')}
                </div>
              </div>

              {textElements.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      Select Text Elements ({selectedCount}/{textElements.length})
                    </h3>
                    <div className="space-x-2">
                      <button
                        onClick={selectAll}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        Select All
                      </button>
                      <button
                        onClick={deselectAll}
                        className="text-sm text-gray-600 hover:text-gray-800"
                      >
                        Deselect All
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {textElements.map((element) => (
                      <div
                        key={element.id}
                        className={`border rounded-lg p-4 cursor-pointer transition-colors ${element.selected
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 bg-white hover:bg-gray-50'
                          }`}
                        onClick={() => toggleElement(element.id)}
                      >
                        <div className="flex items-start space-x-3">
                          <input
                            type="checkbox"
                            checked={element.selected}
                            onChange={() => toggleElement(element.id)}
                            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-2">
                              <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                                {element.tag}
                              </span>
                              <span className="text-xs text-gray-500">
                                {element.word_count} words
                              </span>
                            </div>
                            <p className="text-sm text-gray-700">{element.preview}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedCount > 0 && (
                    <div className="mt-6 pt-4 border-t">
                      <button
                        onClick={handleAddToCollection}
                        disabled={processing}
                        className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        {processing ? (
                          <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                        ) : (
                          <CheckCircle className="h-5 w-5 mr-2" />
                        )}
                        {processing ? 'Adding to Collection...' : `Add ${selectedCount} Elements to Collection`}
                      </button>
                    </div>
                  )}
                </div>
              )}
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
    </div>
  )
}

export default ScrapeWeb