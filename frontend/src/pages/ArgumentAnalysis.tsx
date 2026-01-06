import { useState, useEffect } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
    Loader2,
    FileText,
    List,
    AlertTriangle,
    ShieldAlert,
    RotateCcw,
    ArrowRight,
    Calendar,
    FileSearch,
    History,
    RefreshCw
} from 'lucide-react'
import api, { ContentAnalysis, ClaimReview } from '../services/api'
import { VerifyButton } from '../components/ClaimVerification'

interface AnalysisData {
    summary?: any
    claims?: any
    controversy?: any
    fallacies?: any
    counterargument?: any
}

interface SavedResultData {
    name: string
    saved_at: string
    source_type: string
    url: string
    title: string
    content: string
    metadata: Record<string, any>
}

const ArgumentAnalysis = () => {
    const location = useLocation()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const savedResultData = (location.state as { savedResultData?: SavedResultData })?.savedResultData

    const [loading, setLoading] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [analysisData, setAnalysisData] = useState<AnalysisData>({})
    const [activeStep, setActiveStep] = useState(0)
    const [progressMessage, setProgressMessage] = useState<string>('')
    const [progressPercent, setProgressPercent] = useState<number>(0)

    // Previous analysis detection
    const [existingAnalysis, setExistingAnalysis] = useState<ContentAnalysis | null>(null)
    const [checkingExisting, setCheckingExisting] = useState(false)
    const [showExistingBanner, setShowExistingBanner] = useState(false)

    // Previous claim review detection
    const [existingClaimReview, setExistingClaimReview] = useState<ClaimReview | null>(null)
    const [showClaimReviewBanner, setShowClaimReviewBanner] = useState(false)

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const formatRelativeDate = (dateStr: string | null) => {
        if (!dateStr) return 'Unknown'
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
        const diffDays = Math.floor(diffHours / 24)

        if (diffHours < 1) return 'just now'
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
        return formatDate(dateStr)
    }

    // Check for existing analysis when URL is available
    useEffect(() => {
        const urlParam = searchParams.get('url')
        const targetUrl = savedResultData?.url || urlParam

        if (targetUrl) {
            checkForExistingAnalysis(targetUrl)
        }
    }, [savedResultData?.url, searchParams])

    const checkForExistingAnalysis = async (url: string) => {
        setCheckingExisting(true)
        try {
            const result = await api.getAnalysisByUrl(url)
            if (result.success && result.analysis && result.analysis.status === 'completed') {
                setExistingAnalysis(result.analysis)
                setShowExistingBanner(true)
            } else {
                setExistingAnalysis(null)
                setShowExistingBanner(false)
            }
        } catch (err) {
            console.error('Failed to check for existing analysis:', err)
        } finally {
            setCheckingExisting(false)
        }
    }

    const loadPreviousAnalysis = async () => {
        if (!existingAnalysis) return

        // Convert stored analysis to the format expected by the UI
        const summaryData = {
            summary: {
                summary: existingAnalysis.executive_summary,
                key_claims: existingAnalysis.key_claims || [],
                main_argument: existingAnalysis.main_argument,
                conclusions: existingAnalysis.conclusions || []
            },
            source_assessment: {
                credibility: existingAnalysis.source_credibility,
                reasoning: existingAnalysis.source_credibility_reasoning,
                potential_biases: existingAnalysis.source_potential_biases || []
            }
        }

        setAnalysisData({ summary: summaryData })
        setActiveStep(1)  // Move to next step after summary
        setShowExistingBanner(false)

        // Check for existing claim review when loading previous summary
        await checkForExistingClaimReview(existingAnalysis.url)
    }

    const startFreshAnalysis = () => {
        setShowExistingBanner(false)
        setExistingAnalysis(null)
        setShowClaimReviewBanner(false)
        setExistingClaimReview(null)
        setAnalysisData({})
        setActiveStep(0)
    }

    const checkForExistingClaimReview = async (url: string) => {
        try {
            const result = await api.getClaimReviewByUrl(url)
            if (result.success && result.claim_review) {
                setExistingClaimReview(result.claim_review)
                setShowClaimReviewBanner(true)
            } else {
                setExistingClaimReview(null)
                setShowClaimReviewBanner(false)
            }
        } catch (err) {
            console.error('Failed to check for existing claim review:', err)
        }
    }

    const loadPreviousClaimReview = () => {
        if (!existingClaimReview) return

        // Convert stored claim review to the format expected by the UI
        const claimsData = {
            claims: existingClaimReview.claims
        }

        setAnalysisData(prev => ({ ...prev, claims: claimsData }))
        setActiveStep(prev => Math.max(prev, 2))  // Move to next step after claims
        setShowClaimReviewBanner(false)
    }

    const startFreshClaimReview = () => {
        setShowClaimReviewBanner(false)
        setExistingClaimReview(null)
    }

    const steps = [
        { id: 'summary', name: 'Summary', icon: FileText },
        { id: 'claims', name: 'Claim Review', icon: List },
        { id: 'controversy', name: 'Controversy', icon: ShieldAlert },
        { id: 'fallacies', name: 'Fallacies', icon: AlertTriangle },
        { id: 'counterargument', name: 'Counterarguments', icon: RotateCcw },
    ]

    const runStep = async (stepId: string) => {
        if (!savedResultData) return

        setLoading(stepId)
        setError(null)
        setProgressMessage('Starting...')
        setProgressPercent(0)

        let previous_data = null
        // Get the summary data, handling both flat (from API) and nested (from loadPreviousAnalysis) structures
        const getSummaryData = () => {
            const summary = analysisData.summary
            // If nested structure (from loadPreviousAnalysis), extract inner summary
            if (summary?.summary?.summary) return summary.summary
            // Otherwise use flat structure directly
            return summary
        }

        if (stepId === 'summary') previous_data = savedResultData
        else if (stepId === 'claims') previous_data = {
            summary_data: getSummaryData(),
            full_text: savedResultData.content,
            url: savedResultData.url  // Include URL for persistence
        }
        else if (stepId === 'controversy') previous_data = {
            summary_data: getSummaryData(),
            full_text: savedResultData.content
        }
        else if (stepId === 'fallacies') previous_data = {
            summary_data: getSummaryData(),
            full_text: savedResultData.content
        }
        else if (stepId === 'counterargument') previous_data = {
            summary_data: getSummaryData()
        }

        // Hide claim review banner when running claims step fresh
        if (stepId === 'claims') {
            setShowClaimReviewBanner(false)
        }

        try {
            const result = await api.runAnalysisStepWithProgress(
                { step: stepId, previous_data },
                (message, progress) => {
                    setProgressMessage(message)
                    setProgressPercent(progress)
                }
            )

            if (result.success) {
                setAnalysisData(prev => ({ ...prev, [stepId]: result.data }))
                setActiveStep(prev => Math.max(prev, steps.findIndex(s => s.id === stepId) + 1))

                // After summary step completes, check for existing claim review
                if (stepId === 'summary' && savedResultData.url) {
                    await checkForExistingClaimReview(savedResultData.url)
                }
            } else {
                setError(result.error || `Failed to run ${stepId}`)
            }
        } catch (err: any) {
            setError(err.message || 'An unexpected error occurred')
        } finally {
            setLoading(null)
            setProgressMessage('')
            setProgressPercent(0)
        }
    }

    const renderContent = (stepId: string) => {
        const data = (analysisData as any)[stepId]
        if (!data) return null

        switch (stepId) {
            case 'summary':
                // Handle both flat structure (from API) and nested structure (from loadPreviousAnalysis)
                const summaryData = data.summary?.summary ? data.summary : data
                const keyClaims = summaryData.key_claims || []
                return (
                    <div className="space-y-4">
                        <div className="bg-white p-4 rounded-lg shadow-sm border">
                            <h3 className="font-bold mb-2">Executive Summary</h3>
                            <p className="text-gray-700">{summaryData.summary}</p>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div className="bg-white p-4 rounded-lg shadow-sm border">
                                <h3 className="font-bold mb-2">Key Claims</h3>
                                <ul className="space-y-2 text-sm">
                                    {keyClaims.map((c: any, i: number) => (
                                        <li key={i} className="flex items-start gap-2">
                                            <span className="text-blue-600 font-medium shrink-0">{i + 1}.</span>
                                            <span>{c.text}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="bg-white p-4 rounded-lg shadow-sm border">
                                <h3 className="font-bold mb-2">Main Argument</h3>
                                <p className="text-sm italic">{summaryData.main_argument}</p>
                            </div>
                        </div>
                    </div>
                )
            case 'claims':
                return (
                    <div className="space-y-3">
                        <h3 className="font-bold">Significant Claims</h3>
                        {data.claims.map((c: any, i: number) => (
                            <div key={i} className="p-3 bg-white rounded border border-gray-100 shadow-sm">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex items-start gap-2 flex-1 min-w-0">
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase flex-shrink-0 ${
                                            c.type === 'factual' ? 'bg-blue-100 text-blue-700' :
                                            c.type === 'unsupported' ? 'bg-yellow-100 text-yellow-700' :
                                            c.type === 'opinion' ? 'bg-purple-100 text-purple-700' :
                                            'bg-orange-100 text-orange-700'
                                        }`}>
                                            {c.type}
                                        </span>
                                        <span className="text-sm">{c.text}</span>
                                    </div>
                                </div>
                                {c.evidence && (
                                    <div className="mt-2 text-xs text-gray-500 italic pl-2 border-l-2 border-gray-200">
                                        <span className="font-medium text-gray-600">Evidence:</span> {c.evidence}
                                    </div>
                                )}
                                {/* Verification button and results - full width for results expansion */}
                                <div className="mt-3 pt-3 border-t border-gray-100">
                                    <VerifyButton
                                        claimText={c.text}
                                        claimId={`claim-${i}`}
                                        sourceUrl={savedResultData?.url || ''}
                                        onVerificationStarted={(id) => console.log('Verification started:', id)}
                                        onVerificationComplete={(result) => console.log('Verification complete:', result)}
                                        onError={(err) => console.error('Verification error:', err)}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )
            case 'controversy':
                return (
                    <div className="bg-red-50 p-4 rounded-lg border border-red-100 space-y-4">
                        <div className="flex justify-between items-center">
                            <h3 className="font-bold text-red-900">Controversy Assessment</h3>
                            <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-bold">
                                {data.overall_assessment.controversy_level.toUpperCase()}
                            </span>
                        </div>
                        <p className="text-sm text-red-800">{data.overall_assessment.summary}</p>
                        {data.conspiracy_indicators.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-xs font-bold uppercase text-red-900">Conspiracy Indicators</h4>
                                {data.conspiracy_indicators.map((i: any, idx: number) => (
                                    <div key={idx} className="text-xs p-2 bg-white/50 rounded border border-red-200">
                                        <span className="font-bold">{i.pattern}:</span> {i.evidence}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )
            case 'fallacies':
                return (
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <h3 className="font-bold">Reasoning Quality:</h3>
                            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                                {data.overall_reasoning_quality.toUpperCase()}
                            </span>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                            {data.fallacies.map((f: any, i: number) => (
                                <div key={i} className="p-3 bg-white rounded border-l-4 border-red-500 shadow-sm text-sm">
                                    <h4 className="font-bold text-red-700">{f.type}</h4>
                                    <p className="italic text-gray-500 my-1">"{f.quote}"</p>
                                    <p>{f.explanation}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )
            case 'counterargument':
                return (
                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 space-y-4">
                        <h3 className="font-bold text-blue-900">Counter-Perspectives</h3>
                        <p className="text-blue-900 text-sm">{data.counterargument}</p>
                        <div className="space-y-1">
                            <h4 className="text-[10px] font-bold uppercase text-blue-700">Sources</h4>
                            <div className="flex flex-wrap gap-2">
                                {data.sources.map((s: any, i: number) => (
                                    <a key={i} href={s.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                                        {s.title}
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>
                )
            default:
                return null
        }
    }

    return (
        <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Argument Analysis</h1>
                <p className="text-gray-500 mb-6">Analyze content for logical consistency, claims, and controversies using multi-agent orchestration.</p>

                {savedResultData ? (
                    <div className="space-y-3">
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <h3 className="font-bold text-lg text-gray-900">{savedResultData.name}</h3>
                            <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
                                <Calendar className="h-4 w-4" />
                                <span>Saved {formatDate(savedResultData.saved_at)}</span>
                            </div>
                            <p className="mt-2 text-xs text-blue-600">Click "Run Step" on Summary to start the analysis.</p>
                        </div>

                        {/* Previous Analysis Banner */}
                        {checkingExisting && (
                            <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                                <span className="text-sm text-gray-600">Checking for previous analysis...</span>
                            </div>
                        )}

                        {showExistingBanner && existingAnalysis && (
                            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                                <div className="flex items-start gap-3">
                                    <History className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <h4 className="font-semibold text-amber-900">Previous Analysis Found</h4>
                                        <p className="text-sm text-amber-700 mt-1">
                                            This content was analyzed {formatRelativeDate(existingAnalysis.completed_at || existingAnalysis.created_at)}
                                        </p>
                                        <div className="flex gap-2 mt-3">
                                            <button
                                                onClick={loadPreviousAnalysis}
                                                className="px-3 py-1.5 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 flex items-center gap-1"
                                            >
                                                <History className="h-3.5 w-3.5" />
                                                Load Previous
                                            </button>
                                            <button
                                                onClick={startFreshAnalysis}
                                                className="px-3 py-1.5 bg-white text-amber-700 text-sm font-medium rounded-lg border border-amber-300 hover:bg-amber-50 flex items-center gap-1"
                                            >
                                                <RefreshCw className="h-3.5 w-3.5" />
                                                Start Fresh
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="p-6 bg-gray-50 border border-gray-200 rounded-lg text-center">
                        <FileSearch className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                        <h3 className="font-medium text-gray-900 mb-1">No result selected</h3>
                        <p className="text-sm text-gray-500 mb-4">Select a saved result to analyze its content.</p>
                        <button
                            onClick={() => navigate('/saved-results')}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                        >
                            Go to Saved Results
                        </button>
                    </div>
                )}
                {error && <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
            </div>

            <div className="space-y-4">
                {steps.map((step, index) => {
                    const isEnabled = savedResultData && index <= activeStep && (index === 0 || (analysisData as any)[steps[index - 1].id])
                    const isCompleted = !!(analysisData as any)[step.id]
                    const isActive = loading === step.id
                    const Icon = step.icon

                    return (
                        <div key={step.id} className={`transition-all duration-300 ${isEnabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                            <div className="flex items-start gap-4">
                                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border-2 ${isCompleted ? 'bg-green-100 border-green-500 text-green-600' :
                                    isActive ? 'bg-blue-100 border-blue-500 text-blue-600' : 'bg-white border-gray-200 text-gray-400'
                                    }`}>
                                    {isActive ? <Loader2 className="h-5 w-5 animate-spin" /> : <Icon className="h-5 w-5" />}
                                </div>

                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-2">
                                        <h2 className="text-lg font-bold text-gray-800">{step.name}</h2>
                                        {isEnabled && !isCompleted && !isActive && !(step.id === 'claims' && showClaimReviewBanner) && (
                                            <button
                                                onClick={() => runStep(step.id)}
                                                className="text-sm text-blue-600 font-medium hover:underline flex items-center gap-1"
                                            >
                                                Run Step <ArrowRight className="h-3 w-3" />
                                            </button>
                                        )}
                                    </div>

                                    {/* Previous Claim Review Banner */}
                                    {step.id === 'claims' && isEnabled && !isCompleted && !isActive && showClaimReviewBanner && existingClaimReview && (
                                        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mb-3">
                                            <div className="flex items-start gap-3">
                                                <History className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                                <div className="flex-1">
                                                    <h4 className="font-semibold text-amber-900">Previous Claim Review Found</h4>
                                                    <p className="text-sm text-amber-700 mt-1">
                                                        {existingClaimReview.claims.length} claims reviewed {formatRelativeDate(existingClaimReview.created_at)}
                                                    </p>
                                                    <div className="flex gap-2 mt-3">
                                                        <button
                                                            onClick={loadPreviousClaimReview}
                                                            className="px-3 py-1.5 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 flex items-center gap-1"
                                                        >
                                                            <History className="h-3.5 w-3.5" />
                                                            Load Previous
                                                        </button>
                                                        <button
                                                            onClick={startFreshClaimReview}
                                                            className="px-3 py-1.5 bg-white text-amber-700 text-sm font-medium rounded-lg border border-amber-300 hover:bg-amber-50 flex items-center gap-1"
                                                        >
                                                            <RefreshCw className="h-3.5 w-3.5" />
                                                            Run Fresh
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {isActive && (
                                        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 animate-pulse">
                                            <div className="flex items-center gap-2 mb-2">
                                                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                                                <span className="text-sm text-blue-700 font-medium">{progressMessage || 'Processing...'}</span>
                                            </div>
                                            <div className="w-full bg-blue-200 rounded-full h-2">
                                                <div
                                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                                    style={{ width: `${progressPercent}%` }}
                                                />
                                            </div>
                                            <p className="text-xs text-blue-500 mt-2">This may take several minutes for long content...</p>
                                        </div>
                                    )}

                                    {isCompleted && (
                                        <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                                            {renderContent(step.id)}
                                        </div>
                                    )}
                                </div>
                            </div>
                            {index < steps.length - 1 && (
                                <div className="ml-5 mt-1 mb-1 border-l-2 border-gray-100 h-8" />
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default ArgumentAnalysis
