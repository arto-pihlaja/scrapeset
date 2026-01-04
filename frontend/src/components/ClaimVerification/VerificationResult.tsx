import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle, XCircle, HelpCircle, AlertCircle } from 'lucide-react'
import EvidenceList from './EvidenceList'

interface EvidenceItem {
  source_url: string
  source_title: string
  snippet: string
  credibility_score?: number
  credibility_reasoning?: string
}

interface VerificationData {
  id: string
  claim_text: string
  source_url: string
  status: string
  evidence_for: EvidenceItem[]
  evidence_against: EvidenceItem[]
  conclusion?: string
  conclusion_type?: string
  created_at?: string
  completed_at?: string
  error_message?: string
}

interface VerificationResultProps {
  verification: VerificationData
  onRetry?: () => void
}

const VerificationResult = ({ verification, onRetry }: VerificationResultProps) => {
  const [isExpanded, setIsExpanded] = useState(true)

  const getConclusionConfig = (type?: string) => {
    switch (type) {
      case 'supported':
        return {
          label: 'Supported',
          bgColor: 'bg-green-100',
          textColor: 'text-green-800',
          borderColor: 'border-green-300',
          Icon: CheckCircle,
          iconColor: 'text-green-600'
        }
      case 'refuted':
        return {
          label: 'Refuted',
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          borderColor: 'border-red-300',
          Icon: XCircle,
          iconColor: 'text-red-600'
        }
      case 'inconclusive':
        return {
          label: 'Inconclusive',
          bgColor: 'bg-yellow-100',
          textColor: 'text-yellow-800',
          borderColor: 'border-yellow-300',
          Icon: HelpCircle,
          iconColor: 'text-yellow-600'
        }
      default:
        return {
          label: 'Unknown',
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          borderColor: 'border-gray-300',
          Icon: AlertCircle,
          iconColor: 'text-gray-600'
        }
    }
  }

  // Handle failed verifications
  if (verification.status === 'failed') {
    return (
      <div className="mt-3 p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2 text-red-700">
          <XCircle className="h-5 w-5" />
          <span className="font-medium">Verification Failed</span>
        </div>
        <p className="text-sm text-red-600 mt-2">
          {verification.error_message || 'An error occurred during verification'}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded-md transition-colors"
          >
            Retry Verification
          </button>
        )}
      </div>
    )
  }

  const conclusionConfig = getConclusionConfig(verification.conclusion_type)
  const ConclusionIcon = conclusionConfig.Icon

  const evidenceForCount = verification.evidence_for?.length || 0
  const evidenceAgainstCount = verification.evidence_against?.length || 0

  return (
    <div className="mt-3 border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-sm font-medium rounded-full ${conclusionConfig.bgColor} ${conclusionConfig.textColor}`}>
            <ConclusionIcon className={`h-4 w-4 ${conclusionConfig.iconColor}`} />
            {conclusionConfig.label}
          </span>
          <span className="text-sm text-gray-600">
            {evidenceForCount} supporting · {evidenceAgainstCount} contradicting
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Conclusion */}
          {verification.conclusion && (
            <div className={`p-3 rounded-lg border ${conclusionConfig.bgColor} ${conclusionConfig.borderColor}`}>
              <div className="flex items-center gap-2 mb-2">
                <ConclusionIcon className={`h-5 w-5 ${conclusionConfig.iconColor}`} />
                <span className={`font-medium ${conclusionConfig.textColor}`}>Conclusion</span>
              </div>
              <p className="text-sm text-gray-800">{verification.conclusion}</p>
            </div>
          )}

          {/* Evidence For */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Evidence For ({evidenceForCount})
            </h4>
            <EvidenceList evidence={verification.evidence_for || []} type="for" />
          </div>

          {/* Evidence Against */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Evidence Against ({evidenceAgainstCount})
            </h4>
            <EvidenceList evidence={verification.evidence_against || []} type="against" />
          </div>

          {/* Metadata */}
          {verification.completed_at && (
            <div className="pt-2 border-t border-gray-100 text-xs text-gray-400">
              Verified at {new Date(verification.completed_at).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default VerificationResult
