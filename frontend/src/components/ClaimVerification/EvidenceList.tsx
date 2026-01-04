import { ExternalLink, ThumbsUp, ThumbsDown } from 'lucide-react'
import CredibilityBadge from './CredibilityBadge'

interface EvidenceItem {
  source_url: string
  source_title: string
  snippet: string
  credibility_score?: number
  credibility_reasoning?: string
}

interface EvidenceListProps {
  evidence: EvidenceItem[]
  type: 'for' | 'against'
}

const EvidenceList = ({ evidence, type }: EvidenceListProps) => {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic py-2">
        No {type === 'for' ? 'supporting' : 'contradicting'} evidence found
      </div>
    )
  }

  const isFor = type === 'for'
  const bgColor = isFor ? 'bg-green-50' : 'bg-red-50'
  const borderColor = isFor ? 'border-green-200' : 'border-red-200'
  const iconColor = isFor ? 'text-green-600' : 'text-red-600'
  const Icon = isFor ? ThumbsUp : ThumbsDown

  return (
    <div className="space-y-2">
      {evidence.map((item, index) => (
        <div
          key={index}
          className={`p-3 rounded-lg border ${bgColor} ${borderColor}`}
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Icon className={`h-4 w-4 flex-shrink-0 ${iconColor}`} />
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-blue-600 hover:underline truncate flex items-center gap-1"
                title={item.source_title || item.source_url}
              >
                {item.source_title || 'Source'}
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
              </a>
            </div>
            <CredibilityBadge
              score={item.credibility_score}
              reasoning={item.credibility_reasoning}
            />
          </div>

          <p className="text-sm text-gray-700 pl-6">
            "{item.snippet}"
          </p>

          <div className="mt-2 pl-6">
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gray-500 hover:text-blue-600 truncate block"
            >
              {item.source_url}
            </a>
          </div>
        </div>
      ))}
    </div>
  )
}

export default EvidenceList
