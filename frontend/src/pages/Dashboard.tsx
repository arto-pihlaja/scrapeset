import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Globe,
  MessageCircle,
  Database,
  Activity,
  FileText,
  TrendingUp
} from 'lucide-react'
import { api } from '../services/api'

interface DashboardStats {
  totalVectorDBs: number
  totalSavedResults: number
}

const Dashboard = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalVectorDBs: 0,
    totalSavedResults: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [collectionsResponse, resultsResponse] = await Promise.all([
          api.getCollections(),
          api.getResults()
        ])
        setStats({
          totalVectorDBs: collectionsResponse.success ? collectionsResponse.collections.length : 0,
          totalSavedResults: resultsResponse.success ? resultsResponse.results.length : 0
        })
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const quickActions = [
    {
      title: 'Scrape Website',
      description: 'Extract content from a website',
      href: '/scrape',
      icon: Globe,
      color: 'bg-blue-500'
    },
    {
      title: 'Start Chat',
      description: 'Ask questions about your content',
      href: '/chat',
      icon: MessageCircle,
      color: 'bg-green-500'
    },
    {
      title: 'Saved Results',
      description: 'View and manage saved scraping results',
      href: '/saved-results',
      icon: FileText,
      color: 'bg-purple-500'
    }
  ]

  const statCards = [
    {
      title: 'Saved Results',
      value: stats.totalSavedResults,
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-100'
    },
    {
      title: 'Vector Databases',
      value: stats.totalVectorDBs,
      icon: Database,
      color: 'text-green-600',
      bg: 'bg-green-100'
    },
    {
      title: 'Recent Activity',
      value: stats.totalSavedResults > 0 ? 'Active' : 'None',
      icon: Activity,
      color: 'text-orange-600',
      bg: 'bg-orange-100'
    },
    {
      title: 'Status',
      value: 'Online',
      icon: TrendingUp,
      color: 'text-purple-600',
      bg: 'bg-purple-100'
    }
  ]

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
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome to ScrapeSET - your web scraping and RAG tool
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.title} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className={`p-2 rounded-lg ${stat.bg}`}>
                  <Icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.title}
                to={action.href}
                className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6 group"
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${action.color} text-white`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 group-hover:text-blue-600">
                      {action.title}
                    </h3>
                    <p className="text-gray-600">{action.description}</p>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default Dashboard