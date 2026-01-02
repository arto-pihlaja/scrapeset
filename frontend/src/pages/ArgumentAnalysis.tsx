import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
    Search,
    Loader2,
    ChevronRight,
    FileText,
    List,
    AlertTriangle,
    ShieldAlert,
    RotateCcw,
    ArrowRight,
    CheckCircle
} from 'lucide-react'
import api from '../services/api'

interface AnalysisData {
    fetch?: any
    summary?: any
    claims?: any
    controversy?: any
    fallacies?: any
    counterargument?: any
}

interface PreScrapedData {
    source_type: string
    url: string
    title: string
    content: string
    metadata: Record<string, any>
}

const ArgumentAnalysis = () => {
    const location = useLocation()
    const preScrapedData = (location.state as { preScrapedData?: PreScrapedData })?.preScrapedData

    const [url, setUrl] = useState(preScrapedData?.url || '')
    const [loading, setLoading] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [analysisData, setAnalysisData] = useState<AnalysisData>({})
    const [activeStep, setActiveStep] = useState(0)

    // Auto-populate fetch data if pre-scraped content is available
    useEffect(() => {
        if (preScrapedData) {
            setAnalysisData({ fetch: preScrapedData })
            setActiveStep(1)
        }
    }, [])

    const steps = [
        { id: 'fetch', name: 'Source Extraction', icon: Search },
        { id: 'summary', name: 'Summary', icon: FileText },
        { id: 'claims', name: 'Key Claims', icon: List },
        { id: 'controversy', name: 'Controversy', icon: ShieldAlert },
        { id: 'fallacies', name: 'Fallacies', icon: AlertTriangle },
        { id: 'counterargument', name: 'Counterarguments', icon: RotateCcw },
    ]

    const runStep = async (stepId: string) => {
        setLoading(stepId)
        setError(null)

        let previous_data = null
        if (stepId === 'summary') previous_data = analysisData.fetch
        else if (stepId === 'claims') previous_data = analysisData.summary
        else if (stepId === 'controversy') previous_data = {
            summary: analysisData.summary.summary,
            claims: analysisData.claims,
            full_text: analysisData.fetch.content || analysisData.fetch.transcript
        }
        else if (stepId === 'fallacies') previous_data = {
            claims: analysisData.claims,
            full_text: analysisData.fetch.content || analysisData.fetch.transcript
        }
        else if (stepId === 'counterargument') previous_data = {
            claims: analysisData.claims,
            summary: analysisData.summary.summary
        }

        try {
            const result = await api.runAnalysisStep({
                step: stepId,
                url: stepId === 'fetch' ? url : undefined,
                previous_data
            })

            if (result.success) {
                setAnalysisData(prev => ({ ...prev, [stepId]: result.data }))
                setActiveStep(prev => Math.max(prev, steps.findIndex(s => s.id === stepId) + 1))
            } else {
                setError(result.error || `Failed to run ${stepId}`)
            }
        } catch (err: any) {
            setError(err.message || 'An unexpected error occurred')
        } finally {
            setLoading(null)
        }
    }

    const renderContent = (stepId: string) => {
        const data = (analysisData as any)[stepId]
        if (!data) return null

        switch (stepId) {
            case 'fetch':
                return (
                    <div className="bg-white p-4 rounded-lg shadow-sm border">
                        <h3 className="font-bold text-lg mb-2">{data.title}</h3>
                        <p className="text-sm text-gray-500 mb-4">{data.url}</p>
                        <div className="max-h-60 overflow-y-auto text-sm text-gray-700 bg-gray-50 p-3 rounded">
                            {data.content || data.transcript}
                        </div>
                    </div>
                )
            case 'summary':
                return (
                    <div className="space-y-4">
                        <div className="bg-white p-4 rounded-lg shadow-sm border">
                            <h3 className="font-bold mb-2">Executive Summary</h3>
                            <p className="text-gray-700">{data.summary.summary}</p>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div className="bg-white p-4 rounded-lg shadow-sm border">
                                <h3 className="font-bold mb-2">Key Points</h3>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    {data.summary.key_points.map((p: any, i: number) => (
                                        <li key={i}><span className="text-blue-600 font-medium">{p.location}</span> {p.point}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="bg-white p-4 rounded-lg shadow-sm border">
                                <h3 className="font-bold mb-2">Main Argument</h3>
                                <p className="text-sm italic">{data.summary.main_argument}</p>
                            </div>
                        </div>
                    </div>
                )
            case 'claims':
                return (
                    <div className="grid md:grid-cols-3 gap-4">
                        <div className="md:col-span-2 space-y-2">
                            <h3 className="font-bold">Significant Claims</h3>
                            {data.claims.map((c: any, i: number) => (
                                <div key={i} className="p-3 bg-white rounded border border-gray-100 shadow-sm flex items-center gap-2">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${c.type === 'factual' ? 'bg-blue-100 text-blue-700' :
                                        c.type === 'opinion' ? 'bg-purple-100 text-purple-700' : 'bg-orange-100 text-orange-700'
                                        }`}>
                                        {c.type}
                                    </span>
                                    <span className="text-sm">{c.text}</span>
                                </div>
                            ))}
                        </div>
                        <div className="space-y-2">
                            <h3 className="font-bold">Entities</h3>
                            <div className="flex flex-wrap gap-2">
                                {data.key_entities.map((e: string, i: number) => (
                                    <span key={i} className="px-2 py-1 bg-gray-100 rounded text-xs">{e}</span>
                                ))}
                            </div>
                        </div>
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

                {preScrapedData ? (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2 text-green-800">
                            <CheckCircle className="h-5 w-5" />
                            <span className="font-medium">Content pre-loaded from scraper</span>
                        </div>
                        <p className="mt-1 text-sm text-green-700">
                            <span className="font-medium">{preScrapedData.title}</span> — {preScrapedData.url}
                        </p>
                        <p className="mt-2 text-xs text-green-600">Click "Run Step" on Summary to continue the analysis.</p>
                    </div>
                ) : (
                    <div className="flex gap-4">
                        <input
                            type="text"
                            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            placeholder="Enter YouTube or Web URL..."
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            disabled={loading !== null}
                        />
                        <button
                            onClick={() => runStep('fetch')}
                            disabled={!url || loading !== null}
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading === 'fetch' ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight className="h-4 w-4" />}
                            Start Analysis
                        </button>
                    </div>
                )}
                {error && <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}
            </div>

            <div className="space-y-4">
                {steps.map((step, index) => {
                    const isEnabled = index <= activeStep && (index === 0 || (analysisData as any)[steps[index - 1].id])
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
                                        {isEnabled && !isCompleted && !isActive && (
                                            <button
                                                onClick={() => runStep(step.id)}
                                                className="text-sm text-blue-600 font-medium hover:underline flex items-center gap-1"
                                            >
                                                Run Step <ArrowRight className="h-3 w-3" />
                                            </button>
                                        )}
                                    </div>

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
