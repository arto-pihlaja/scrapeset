import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ScrapeWeb from './pages/ScrapeWeb'
import Collections from './pages/Collections'
import Chat from './pages/Chat'
import Conversations from './pages/Conversations'
import Settings from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scrape" element={<ScrapeWeb />} />
        <Route path="/collections" element={<Collections />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/conversations" element={<Conversations />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App