import { useState } from 'react'
import { Settings as SettingsIcon, Save, Eye, EyeOff } from 'lucide-react'

const Settings = () => {
  const [showApiKeys, setShowApiKeys] = useState(false)
  const [settings, setSettings] = useState({
    // LLM Configuration
    openaiApiKey: '',
    anthropicApiKey: '',
    openrouterApiKey: '',
    defaultLlmProvider: 'openai',
    defaultModel: 'gpt-3.5-turbo',
    llmTemperature: 0.1,
    maxTokens: 2000,

    // Text Processing
    minTextLength: 300,
    minWordCount: 100,
    textPreviewWords: 50,
    chunkSize: 1000,
    chunkOverlap: 200,

    // Embedding Models
    embeddingModel: 'default',

    // Conversation Memory
    conversationMemorySize: 5,
    conversationPersistence: false,
    conversationContextRatio: 0.3,

    // Scraping Settings
    requestTimeout: 30,
    maxRetries: 3,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  })

  const handleInputChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleSave = () => {
    // In a real implementation, this would save to backend
    alert('Settings saved! (Note: This is a demo - settings are not actually saved)')
  }

  const embeddingModels = [
    { value: 'default', label: 'Default (ChromaDB)', description: 'sentence-transformers/all-MiniLM-L6-v2' },
    { value: 'openai', label: 'OpenAI Embeddings', description: 'text-embedding-ada-002 (requires API key)' },
    { value: 'sentence-transformers/all-mpnet-base-v2', label: 'All-MPNet-Base-v2', description: 'High quality English embeddings' },
    { value: 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', label: 'Multilingual MiniLM', description: 'Multilingual support' },
    { value: 'instructor', label: 'Instructor Embeddings', description: 'Domain-specific tasks' }
  ]

  const llmProviders = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'openrouter', label: 'OpenRouter' }
  ]

  const openaiModels = ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo-preview']
  const anthropicModels = ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
  const openrouterModels = [
    'mistralai/mistral-small-3.2-24b-instruct',
    'anthropic/claude-3-haiku-20240307',
    'google/gemini-pro-1.5',
    'meta-llama/llama-3.1-8b-instruct'
  ]

  const getAvailableModels = () => {
    switch (settings.defaultLlmProvider) {
      case 'openai': return openaiModels
      case 'anthropic': return anthropicModels
      case 'openrouter': return openrouterModels
      default: return openaiModels
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">
          Configure your ScrapeSET application settings
        </p>
      </div>

      <div className="max-w-4xl space-y-8">
        {/* LLM Configuration */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">LLM Configuration</h2>

          <div className="space-y-4">
            {/* API Keys */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium text-gray-900">API Keys</h3>
                <button
                  onClick={() => setShowApiKeys(!showApiKeys)}
                  className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-800"
                >
                  {showApiKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  <span>{showApiKeys ? 'Hide' : 'Show'}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OpenAI API Key
                  </label>
                  <input
                    type={showApiKeys ? 'text' : 'password'}
                    value={settings.openaiApiKey}
                    onChange={(e) => handleInputChange('openaiApiKey', e.target.value)}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Anthropic API Key
                  </label>
                  <input
                    type={showApiKeys ? 'text' : 'password'}
                    value={settings.anthropicApiKey}
                    onChange={(e) => handleInputChange('anthropicApiKey', e.target.value)}
                    placeholder="sk-ant-..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    OpenRouter API Key
                  </label>
                  <input
                    type={showApiKeys ? 'text' : 'password'}
                    value={settings.openrouterApiKey}
                    onChange={(e) => handleInputChange('openrouterApiKey', e.target.value)}
                    placeholder="sk-or-..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Model Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default LLM Provider
                </label>
                <select
                  value={settings.defaultLlmProvider}
                  onChange={(e) => handleInputChange('defaultLlmProvider', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {llmProviders.map(provider => (
                    <option key={provider.value} value={provider.value}>
                      {provider.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Default Model
                </label>
                <select
                  value={settings.defaultModel}
                  onChange={(e) => handleInputChange('defaultModel', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {getAvailableModels().map(model => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature ({settings.llmTemperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={settings.llmTemperature}
                  onChange={(e) => handleInputChange('llmTemperature', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Tokens
                </label>
                <input
                  type="number"
                  value={settings.maxTokens}
                  onChange={(e) => handleInputChange('maxTokens', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Text Processing */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Text Processing</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Text Length
              </label>
              <input
                type="number"
                value={settings.minTextLength}
                onChange={(e) => handleInputChange('minTextLength', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Minimum Word Count
              </label>
              <input
                type="number"
                value={settings.minWordCount}
                onChange={(e) => handleInputChange('minWordCount', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Text Preview Words
              </label>
              <input
                type="number"
                value={settings.textPreviewWords}
                onChange={(e) => handleInputChange('textPreviewWords', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Chunk Size
              </label>
              <input
                type="number"
                value={settings.chunkSize}
                onChange={(e) => handleInputChange('chunkSize', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Embedding Models */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Embedding Models</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Embedding Model
            </label>
            <select
              value={settings.embeddingModel}
              onChange={(e) => handleInputChange('embeddingModel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {embeddingModels.map(model => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-600 mt-1">
              {embeddingModels.find(m => m.value === settings.embeddingModel)?.description}
            </p>
          </div>
        </div>

        {/* Conversation Memory */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Conversation Memory</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Memory Size (conversation pairs)
              </label>
              <input
                type="number"
                value={settings.conversationMemorySize}
                onChange={(e) => handleInputChange('conversationMemorySize', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Context Ratio ({settings.conversationContextRatio})
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.conversationContextRatio}
                onChange={(e) => handleInputChange('conversationContextRatio', parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <div className="md:col-span-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.conversationPersistence}
                  onChange={(e) => handleInputChange('conversationPersistence', e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm font-medium text-gray-700">
                  Auto-save conversations
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="flex items-center space-x-2 bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Save className="h-5 w-5" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Settings