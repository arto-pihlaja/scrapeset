import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ScrapeWeb from './pages/ScrapeWeb'
import SavedResults from './pages/SavedResults'
import Chat from './pages/Chat'
import Conversations from './pages/Conversations'
import Settings from './pages/Settings'
import ArgumentAnalysis from './pages/ArgumentAnalysis'
import AnalysisHistory from './pages/AnalysisHistory'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scrape" element={<ScrapeWeb />} />
        <Route path="/analysis" element={<ArgumentAnalysis />} />
        <Route path="/analysis-history" element={<AnalysisHistory />} />
        <Route path="/saved-results" element={<SavedResults />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/conversations" element={<Conversations />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App