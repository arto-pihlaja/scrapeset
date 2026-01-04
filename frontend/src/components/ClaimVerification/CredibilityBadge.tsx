import { useState } from 'react'
import { Shield, ShieldAlert, ShieldCheck, ShieldQuestion, Info } from 'lucide-react'

interface CredibilityBadgeProps {
  score?: number
  reasoning?: string
}

const CredibilityBadge = ({ score, reasoning }: CredibilityBadgeProps) => {
  const [showTooltip, setShowTooltip] = useState(false)

  if (score === undefined || score === null) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-gray-400">
        <ShieldQuestion className="h-3 w-3" />
        <span>N/A</span>
      </span>
    )
  }

  const getScoreConfig = (score: number) => {
    if (score >= 8) {
      return {
        label: 'High',
        bgColor: 'bg-green-100',
        textColor: 'text-green-700',
        borderColor: 'border-green-200',
        Icon: ShieldCheck
      }
    } else if (score >= 5) {
      return {
        label: 'Medium',
        bgColor: 'bg-yellow-100',
        textColor: 'text-yellow-700',
        borderColor: 'border-yellow-200',
        Icon: Shield
      }
    } else {
      return {
        label: 'Low',
        bgColor: 'bg-red-100',
        textColor: 'text-red-700',
        borderColor: 'border-red-200',
        Icon: ShieldAlert
      }
    }
  }

  const config = getScoreConfig(score)
  const Icon = config.Icon

  return (
    <div className="relative inline-block">
      <button
        type="button"
        className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor}`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(!showTooltip)}
      >
        <Icon className="h-3 w-3" />
        <span>{score}/10</span>
        {reasoning && <Info className="h-3 w-3 opacity-60" />}
      </button>

      {showTooltip && reasoning && (
        <div className="absolute z-10 bottom-full left-0 mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
          <div className="font-medium mb-1">Credibility Assessment</div>
          <p className="text-gray-300">{reasoning}</p>
          <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-900"></div>
        </div>
      )}
    </div>
  )
}

export default CredibilityBadge
