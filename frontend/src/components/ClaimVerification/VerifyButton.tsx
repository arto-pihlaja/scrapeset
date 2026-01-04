import { useState, useEffect } from 'react'
import { CheckCircle, Loader2, XCircle, Search, RefreshCw, AlertCircle } from 'lucide-react'
import api from '../../services/api'
import VerificationResult from './VerificationResult'

interface VerifyButtonProps {
  claimText: string
  claimId?: string
  sourceUrl: string
  onVerificationStarted?: (verificationId: string) => void
  onVerificationComplete?: (result: VerificationData) => void
  onError?: (error: string) => void
}

interface VerificationData {
  id: string
  claim_text: string
  source_url: string
  status: string
  evidence_for: Array<{
    source_url: string
    source_title: string
    snippet: string
    credibility_score?: number
    credibility_reasoning?: string
  }>
  evidence_against: Array<{
    source_url: string
    source_title: string
    snippet: string
    credibility_score?: number
    credibility_reasoning?: string
  }>
  conclusion?: string
  conclusion_type?: string
  error_message?: string
  created_at?: string
  completed_at?: string
}

interface VerificationState {
  status: 'idle' | 'loading_existing' | 'loading' | 'completed' | 'error' | 'in_progress'
  progressMessage?: string
  progressStep?: string
  progressPercent?: number
  result?: VerificationData
  error?: string
  failedStep?: string
}

// Parse step information from error message
const parseErrorStep = (error: string): { step: string; message: string } => {
  const match = error.match(/^\[(\w+)\]\s*(.+)$/s)
  if (match) {
    return { step: match[1], message: match[2] }
  }
  return { step: 'unknown', message: error }
}

// Get user-friendly step label
const getStepLabel = (step: string): string => {
  switch (step) {
    case 'searching':
      return 'Web Search'
    case 'analyzing':
      return 'Evidence Analysis'
    case 'assessing':
      return 'Credibility Assessment'
    case 'concluding':
      return 'Conclusion Synthesis'
    case 'starting':
      return 'Initialization'
    default:
      return 'Processing'
  }
}

const VerifyButton = ({
  claimText,
  claimId,
  sourceUrl,
  onVerificationStarted,
  onVerificationComplete,
  onError
}: VerifyButtonProps) => {
  const [state, setState] = useState<VerificationState>({ status: 'idle' })

  // Load existing verification on mount
  useEffect(() => {
    const loadExistingVerification = async () => {
      setState({ status: 'loading_existing' })
      try {
        const response = await api.getVerificationByClaim({
          claim_id: claimId,
          claim_text: claimText,
          source_url: sourceUrl
        })

        if (response.success && response.verification) {
          const verification = response.verification

          // Map status to our state
          if (verification.status === 'completed') {
            setState({
              status: 'completed',
              result: {
                id: verification.id,
                claim_text: verification.claim_text,
                source_url: verification.source_url,
                status: verification.status,
                evidence_for: verification.evidence_for || [],
                evidence_against: verification.evidence_against || [],
                conclusion: verification.conclusion,
                conclusion_type: verification.conclusion_type,
                created_at: verification.created_at,
                completed_at: verification.completed_at
              }
            })
          } else if (verification.status === 'failed') {
            const parsedError = parseErrorStep(verification.error_message || 'Unknown error')
            setState({
              status: 'error',
              error: verification.error_message,
              failedStep: parsedError.step,
              result: {
                id: verification.id,
                claim_text: verification.claim_text,
                source_url: verification.source_url,
                status: verification.status,
                evidence_for: [],
                evidence_against: [],
                error_message: verification.error_message
              }
            })
          } else if (verification.status === 'in_progress' || verification.status === 'pending') {
            // For in-progress, show that status but allow re-triggering
            setState({
              status: 'in_progress',
              progressMessage: 'Verification in progress...'
            })
          } else {
            setState({ status: 'idle' })
          }
        } else {
          setState({ status: 'idle' })
        }
      } catch (err) {
        // If we can't load existing, just go to idle
        setState({ status: 'idle' })
      }
    }

    loadExistingVerification()
  }, [claimId, claimText, sourceUrl])

  const handleVerify = async () => {
    setState({
      status: 'loading',
      progressMessage: 'Starting verification...',
      progressStep: 'starting',
      progressPercent: 0
    })

    try {
      const response = await api.verifyClaimWithProgress(
        {
          claim_text: claimText,
          claim_id: claimId,
          source_url: sourceUrl
        },
        (message, step, progress) => {
          setState(prev => ({
            ...prev,
            progressMessage: message,
            progressStep: step,
            progressPercent: progress
          }))
        }
      )

      if (response.success && response.data) {
        const result: VerificationData = {
          id: response.data.id,
          claim_text: response.data.claim_text,
          source_url: response.data.source_url,
          status: response.data.status,
          evidence_for: response.data.evidence_for || [],
          evidence_against: response.data.evidence_against || [],
          conclusion: response.data.conclusion,
          conclusion_type: response.data.conclusion_type,
          created_at: response.data.created_at,
          completed_at: response.data.completed_at
        }

        setState({
          status: 'completed',
          result
        })

        onVerificationStarted?.(result.id)
        onVerificationComplete?.(result)
      } else {
        const errorMsg = response.error || 'Verification failed'
        const parsedError = parseErrorStep(errorMsg)
        setState({
          status: 'error',
          error: errorMsg,
          failedStep: parsedError.step
        })
        onError?.(errorMsg)
      }
    } catch (err: any) {
      const errorMsg = err.message || 'An unexpected error occurred'
      const parsedError = parseErrorStep(errorMsg)
      setState({
        status: 'error',
        error: errorMsg,
        failedStep: parsedError.step
      })
      onError?.(errorMsg)
    }
  }

  const handleRetry = () => {
    handleVerify()
  }

  const getButtonContent = () => {
    switch (state.status) {
      case 'loading_existing':
        return (
          <>
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Loading...</span>
          </>
        )
      case 'loading':
        return (
          <>
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Verifying...</span>
          </>
        )
      case 'in_progress':
        return (
          <>
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>In Progress</span>
          </>
        )
      case 'completed':
        return (
          <>
            <CheckCircle className="h-3 w-3" />
            <span>Verified</span>
          </>
        )
      case 'error':
        return (
          <>
            <RefreshCw className="h-3 w-3" />
            <span>Retry</span>
          </>
        )
      default:
        return (
          <>
            <Search className="h-3 w-3" />
            <span>Verify</span>
          </>
        )
    }
  }

  const getButtonStyles = () => {
    const base = 'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-colors'

    switch (state.status) {
      case 'loading_existing':
      case 'loading':
        return `${base} bg-gray-100 text-gray-500 cursor-wait`
      case 'in_progress':
        return `${base} bg-blue-100 text-blue-700 cursor-wait`
      case 'completed':
        return `${base} bg-green-100 text-green-700`
      case 'error':
        return `${base} bg-red-100 text-red-700 hover:bg-red-200 cursor-pointer`
      default:
        return `${base} bg-blue-100 text-blue-700 hover:bg-blue-200 cursor-pointer`
    }
  }

  const isDisabled = state.status === 'loading' || state.status === 'loading_existing'

  return (
    <div className="flex flex-col">
      <button
        onClick={state.status === 'error' || state.status === 'in_progress' ? handleRetry : handleVerify}
        disabled={isDisabled}
        className={getButtonStyles()}
        title={state.error || 'Click to verify this claim'}
      >
        {getButtonContent()}
      </button>

      {/* Progress indicator during verification */}
      {state.status === 'loading' && state.progressMessage && (
        <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200 animate-pulse">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
            <span className="text-sm text-blue-700 font-medium">{state.progressMessage}</span>
          </div>
          {state.progressPercent !== undefined && (
            <div className="w-full bg-blue-200 rounded-full h-1.5">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${state.progressPercent}%` }}
              />
            </div>
          )}
          {state.progressStep && (
            <p className="text-xs text-blue-500 mt-2">
              Step: {getStepLabel(state.progressStep)}
            </p>
          )}
        </div>
      )}

      {/* Verification result */}
      {state.status === 'completed' && state.result && (
        <VerificationResult
          verification={state.result}
          onRetry={handleRetry}
        />
      )}

      {/* Error state with step information */}
      {state.status === 'error' && state.error && (
        <div className="mt-2 p-3 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              {state.failedStep && state.failedStep !== 'unknown' && (
                <span className="inline-block px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded mb-1">
                  Failed at: {getStepLabel(state.failedStep)}
                </span>
              )}
              <p className="text-sm text-red-700">
                {parseErrorStep(state.error).message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* In-progress state (existing verification running) */}
      {state.status === 'in_progress' && (
        <div className="mt-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />
            <span className="text-sm text-yellow-700">
              A verification is already in progress. Click Retry to start a new one.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default VerifyButton
