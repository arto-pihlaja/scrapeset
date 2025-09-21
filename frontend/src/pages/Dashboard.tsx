import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Globe,
  MessageCircle,
  Database,
  Activity,
  FileText,
  Clock,
  TrendingUp,
  Users
} from 'lucide-react'
import { api } from '../services/api'

interface Collection {
  name: string
  id: string
  document_count: number
  metadata?: any
}

interface DashboardStats {
  totalCollections: number
  totalDocuments: number
  recentActivity: any[]
}

const Dashboard = () => {
  const [collections, setCollections] = useState<Collection[]>([])
  const [stats, setStats] = useState<DashboardStats>({
    totalCollections: 0,
    totalDocuments: 0,
    recentActivity: []
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const collectionsResponse = await api.getCollections()
        if (collectionsResponse.success) {
          setCollections(collectionsResponse.collections)
          const totalDocs = collectionsResponse.collections.reduce(
            (sum: number, col: Collection) => sum + col.document_count,
            0
          )
          setStats({
            totalCollections: collectionsResponse.collections.length,
            totalDocuments: totalDocs,
            recentActivity: []
          })
        }
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
      title: 'Manage Collections',
      description: 'View and organize your data',
      href: '/collections',
      icon: Database,
      color: 'bg-purple-500'
    }
  ]

  const statCards = [
    {
      title: 'Total Collections',
      value: stats.totalCollections,
      icon: Database,
      color: 'text-blue-600',
      bg: 'bg-blue-100'
    },
    {
      title: 'Total Documents',
      value: stats.totalDocuments,
      icon: FileText,
      color: 'text-green-600',
      bg: 'bg-green-100'
    },
    {
      title: 'Recent Activity',
      value: collections.length > 0 ? 'Active' : 'None',
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

      {/* Recent Collections */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recent Collections</h2>
          <Link
            to="/collections"
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            View all →
          </Link>
        </div>

        {collections.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Collections Yet</h3>
            <p className="text-gray-600 mb-4">
              Start by scraping your first website to create a collection.
            </p>
            <Link
              to="/scrape"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <Globe className="h-4 w-4 mr-2" />
              Scrape Website
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <ul className="divide-y divide-gray-200">
              {collections.slice(0, 5).map((collection) => (
                <li key={collection.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <Database className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {collection.name}
                        </p>
                        <p className="text-sm text-gray-600">
                          {collection.document_count} documents
                        </p>
                      </div>
                    </div>
                    <Link
                      to={`/collections`}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View →
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard