import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  BatteryCharging,
  Camera,
  Cpu,
  Smartphone,
  Tv,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Play,
  SlidersHorizontal,
  Layers,
  FileText,
  Check,
  Bookmark,
  ChevronRight,
  Info,
  TrendingUp,
  BarChart3,
  Search,
  Save,
  Tag,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { api } from '../api/client';

const SAMPLE_REVIEWS = [
  {
    title: 'Multi-Aspect Contrastive',
    text: 'The camera takes excellent photos, but the battery drains too quickly.',
  },
  {
    title: 'Gaming & Display Performance',
    text: 'The 120Hz OLED display looks gorgeous and ultra bright, and the Snapdragon processor delivers blistering gaming performance with zero lag.',
  },
  {
    title: 'Hardware Build & Slow Charging',
    text: 'Premium titanium design feels great in hand, though the charging speed is quite slow.',
  },
  {
    title: 'Negative Multi-Aspect',
    text: 'Terrible battery backup and the phone gets uncomfortably hot during video recording.',
  },
  {
    title: 'Neutral / No Smartphone Aspects',
    text: 'The package arrived promptly on Tuesday in good packaging by the courier.',
  },
];

const ASPECT_ICONS = {
  Battery: BatteryCharging,
  Camera: Camera,
  Performance: Cpu,
  Design: Smartphone,
  Display: Tv,
};

const ASPECT_COLORS = {
  Battery: 'border-emerald-500/40 bg-emerald-950/20 text-emerald-400',
  Camera: 'border-cyan-500/40 bg-cyan-950/20 text-cyan-400',
  Performance: 'border-purple-500/40 bg-purple-950/20 text-purple-400',
  Design: 'border-amber-500/40 bg-amber-950/20 text-amber-400',
  Display: 'border-blue-500/40 bg-blue-950/20 text-blue-400',
};

export default function AbsaDashboard({ products = [], onNavigateToReviews }) {
  const [activeSubTab, setActiveSubTab] = useState('text_analyzer');
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);

  // Live text analyzer state
  const [inputText, setInputText] = useState(SAMPLE_REVIEWS[0].text);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzingText, setIsAnalyzingText] = useState(false);
  const [textError, setTextError] = useState(null);

  // Warehouse review analyzer state
  const [warehouseReviewId, setWarehouseReviewId] = useState('');
  const [isAnalyzingWarehouse, setIsAnalyzingWarehouse] = useState(false);
  const [warehouseResult, setWarehouseResult] = useState(null);
  const [warehouseError, setWarehouseError] = useState(null);
  const [saveToWarehouseDb, setSaveToWarehouseDb] = useState(true);
  const [warehouseReviewPreview, setWarehouseReviewPreview] = useState(null);
  const [isLoadingWarehousePreview, setIsLoadingWarehousePreview] = useState(false);
  const [warehousePreviewError, setWarehousePreviewError] = useState(null);

  // Training state
  const [isTraining, setIsTraining] = useState(false);
  const [trainConfig, setTrainConfig] = useState({
    testSize: 0.2,
    randomState: 42,
    includeSeedDataset: true,
  });
  const [trainResponse, setTrainResponse] = useState(null);
  const [trainError, setTrainError] = useState(null);

  // Annotation state
  const [annoReviewId, setAnnoReviewId] = useState('');
  const [annoAspect, setAnnoAspect] = useState('Camera');
  const [annoSentiment, setAnnoSentiment] = useState('Positive');
  const [annoStatus, setAnnoStatus] = useState('VERIFIED');
  const [annoNotes, setAnnoNotes] = useState('');
  const [isSavingAnno, setIsSavingAnno] = useState(false);
  const [annoSuccessMsg, setAnnoSuccessMsg] = useState(null);
  const [annotationsList, setAnnotationsList] = useState([]);
  const [isLoadingAnnos, setIsLoadingAnnos] = useState(false);
  const [annoReviewPreview, setAnnoReviewPreview] = useState(null);
  const [isLoadingAnnoPreview, setIsLoadingAnnoPreview] = useState(false);
  const [annoPreviewError, setAnnoPreviewError] = useState(null);

  // Fetch status and metrics
  const loadStatusAndMetrics = async () => {
    setIsLoadingStatus(true);
    try {
      const [statusRes, metricsRes] = await Promise.all([
        api.getAbsaStatus().catch(() => null),
        api.getAbsaMetrics().catch(() => null),
      ]);
      setStatus(statusRes);
      setMetrics(metricsRes);
    } catch (err) {
      console.error('Error loading ABSA status:', err);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  const loadAnnotations = async () => {
    setIsLoadingAnnos(true);
    try {
      const res = await api.getAnnotations({ pageSize: 15 });
      setAnnotationsList(res.items || []);
    } catch (err) {
      console.error('Error loading annotations:', err);
    } finally {
      setIsLoadingAnnos(false);
    }
  };

  useEffect(() => {
    loadStatusAndMetrics();
    loadAnnotations();
  }, []);

  // Live preview for Warehouse Review Analyzer
  useEffect(() => {
    const id = parseInt(warehouseReviewId, 10);
    if (isNaN(id) || id <= 0) {
      setWarehouseReviewPreview(null);
      setWarehousePreviewError(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoadingWarehousePreview(true);
      setWarehousePreviewError(null);
      try {
        const rev = await api.getReview(id);
        setWarehouseReviewPreview(rev);
      } catch (err) {
        setWarehouseReviewPreview(null);
        setWarehousePreviewError(`Review #${id} not found in database.`);
      } finally {
        setIsLoadingWarehousePreview(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [warehouseReviewId]);

  // Live preview for Ground-Truth Annotator
  useEffect(() => {
    const id = parseInt(annoReviewId, 10);
    if (isNaN(id) || id <= 0) {
      setAnnoReviewPreview(null);
      setAnnoPreviewError(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoadingAnnoPreview(true);
      setAnnoPreviewError(null);
      try {
        const rev = await api.getReview(id);
        setAnnoReviewPreview(rev);
      } catch (err) {
        setAnnoReviewPreview(null);
        setAnnoPreviewError(`Review #${id} not found in database.`);
      } finally {
        setIsLoadingAnnoPreview(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [annoReviewId]);

  // Handle live text analysis
  const handleAnalyzeText = async () => {
    if (!inputText.trim()) {
      setTextError('Please enter review text to analyze.');
      return;
    }
    setTextError(null);
    setIsAnalyzingText(true);
    try {
      const res = await api.predictAbsa(inputText.trim(), false);
      setAnalysisResult(res);
    } catch (err) {
      setTextError(err.message || 'Analysis failed. Please check backend connection.');
    } finally {
      setIsAnalyzingText(false);
    }
  };

  // Handle warehouse review analysis
  const handleAnalyzeWarehouseReview = async () => {
    const id = parseInt(warehouseReviewId, 10);
    if (isNaN(id) || id <= 0) {
      setWarehouseError('Please enter a valid numeric Review ID.');
      return;
    }
    setWarehouseError(null);
    setIsAnalyzingWarehouse(true);
    try {
      const res = await api.predictReviewAbsa(id, saveToWarehouseDb);
      setWarehouseResult(res);
      loadStatusAndMetrics();
    } catch (err) {
      setWarehouseError(err.message || `Failed to analyze Review #${id}`);
    } finally {
      setIsAnalyzingWarehouse(false);
    }
  };

  // Handle training
  const handleTrainModel = async () => {
    setIsTraining(true);
    setTrainError(null);
    setTrainResponse(null);
    try {
      const res = await api.trainAbsaModel(trainConfig);
      setTrainResponse(res);
      await loadStatusAndMetrics();
    } catch (err) {
      setTrainError(err.message || 'Training failed.');
    } finally {
      setIsTraining(false);
    }
  };

  // Handle annotation save
  const handleSaveAnnotation = async (e) => {
    e.preventDefault();
    const id = parseInt(annoReviewId, 10);
    if (isNaN(id) || id <= 0) {
      setAnnoSuccessMsg({ type: 'error', text: 'Enter a valid numeric Review ID.' });
      return;
    }

    setIsSavingAnno(true);
    setAnnoSuccessMsg(null);
    try {
      await api.annotateReview(id, [
        {
          aspect: annoAspect,
          sentiment: annoSentiment,
          status: annoStatus,
          annotator_notes: annoNotes.trim() || undefined,
        },
      ]);
      setAnnoSuccessMsg({
        type: 'success',
        text: `Annotation for Review #${id} (${annoAspect} → ${annoSentiment}) successfully saved as ${annoStatus}!`,
      });
      setAnnoNotes('');
      await loadAnnotations();
      await loadStatusAndMetrics();
    } catch (err) {
      setAnnoSuccessMsg({ type: 'error', text: err.message || 'Failed to save annotation.' });
    } finally {
      setIsSavingAnno(false);
    }
  };

  // Render aspect pill / sentiment badge
  const renderSentimentBadge = (sentiment) => {
    if (sentiment === 'Positive') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/50">
          <CheckCircle2 className="w-3 h-3 text-[#8BBB92]" />
          <span>Positive</span>
        </span>
      );
    }
    if (sentiment === 'Negative') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-950/40 text-rose-300 border border-rose-800/60">
          <AlertCircle className="w-3 h-3 text-rose-400" />
          <span>Negative</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-950/40 text-sky-300 border border-sky-800/60">
        <HelpCircle className="w-3 h-3 text-sky-400" />
        <span>Neutral</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-[#12544F]/60 bg-gradient-to-r from-[#071b1f] via-[#0d2a2e] to-[#071b1f] p-6 backdrop-blur-xl shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-[#2A835F]/30 text-[#8BBB92] border border-[#2A835F]/50 uppercase tracking-wider">
                Phase 3 Module
              </span>
              <span className="text-xs text-[#7ea698]">
                Natural Language Processing Engine
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center space-x-2.5">
              <Sparkles className="w-6 h-6 text-[#8BBB92]" />
              <span>Aspect-Based Sentiment Analysis (ABSA)</span>
            </h1>
            <p className="text-sm text-[#7ea698] leading-relaxed">
              Identifies smartphone aspects (<strong className="text-white">Battery</strong>, <strong className="text-white">Camera</strong>, <strong className="text-white">Performance</strong>, <strong className="text-white">Design</strong>, <strong className="text-white">Display</strong>) discussed in reviews and predicts polarity (<strong className="text-emerald-400">Positive</strong>, <strong className="text-rose-400">Negative</strong>, <strong className="text-sky-400">Neutral</strong>) per aspect.
            </p>
          </div>

          {/* Quick Model Status Badges */}
          <div className="flex flex-wrap lg:flex-col gap-2 shrink-0">
            <div className="px-3 py-2 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/60 text-xs flex items-center justify-between gap-3">
              <span className="text-[#7ea698]">Model Engine:</span>
              <span className="font-semibold text-white font-mono">
                {status?.model_version || 'absa-hybrid-v1.0'}
              </span>
            </div>
            <div className="px-3 py-2 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/60 text-xs flex items-center justify-between gap-3">
              <span className="text-[#7ea698]">Macro F1 Score:</span>
              <span className="font-bold text-[#8BBB92] font-mono">
                {metrics?.has_metrics && metrics.sentiment_classification_metrics
                  ? `${(metrics.sentiment_classification_metrics.macro_f1 * 100).toFixed(1)}%`
                  : 'Ready'}
              </span>
            </div>
            <div className="px-3 py-2 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/60 text-xs flex items-center justify-between gap-3">
              <span className="text-[#7ea698]">Verified Annotations:</span>
              <span className="font-bold text-amber-400 font-mono">
                {status?.verified_annotations_count || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-[#12544F]/50 space-x-2 overflow-x-auto pb-1">
        <button
          onClick={() => setActiveSubTab('text_analyzer')}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
            activeSubTab === 'text_analyzer'
              ? 'bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/70 shadow-sm'
              : 'text-[#7ea698] hover:text-white hover:bg-[#12544F]/30 border border-transparent'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Interactive Text Analyzer</span>
        </button>

        <button
          onClick={() => setActiveSubTab('warehouse_analyzer')}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
            activeSubTab === 'warehouse_analyzer'
              ? 'bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/70 shadow-sm'
              : 'text-[#7ea698] hover:text-white hover:bg-[#12544F]/30 border border-transparent'
          }`}
        >
          <Search className="w-4 h-4" />
          <span>Warehouse Review Analyzer</span>
        </button>

        <button
          onClick={() => setActiveSubTab('training')}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
            activeSubTab === 'training'
              ? 'bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/70 shadow-sm'
              : 'text-[#7ea698] hover:text-white hover:bg-[#12544F]/30 border border-transparent'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Model Training & Evaluation</span>
        </button>

        <button
          onClick={() => setActiveSubTab('annotator')}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
            activeSubTab === 'annotator'
              ? 'bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/70 shadow-sm'
              : 'text-[#7ea698] hover:text-white hover:bg-[#12544F]/30 border border-transparent'
          }`}
        >
          <Tag className="w-4 h-4" />
          <span>Ground-Truth Annotator</span>
        </button>
      </div>

      {/* SUBTAB 1: LIVE TEXT ANALYZER */}
      {activeSubTab === 'text_analyzer' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Input Form & Sample Picks */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40 mb-3">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-[#8BBB92]" />
                  <span>Input Smartphone Review</span>
                </h3>
                <span className="text-[11px] text-[#649182]">
                  {inputText.length} / 5000 chars
                </span>
              </div>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                rows={5}
                placeholder="Type or paste any smartphone review text here (e.g., 'The camera takes excellent photos, but the battery drains too quickly.')..."
                className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl p-3.5 text-xs sm:text-sm text-white placeholder-[#649182] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-all resize-none font-sans leading-relaxed"
              />

              {textError && (
                <div className="mt-3 p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{textError}</span>
                </div>
              )}

              <div className="mt-4 flex items-center justify-between gap-3">
                <button
                  onClick={() => setInputText('')}
                  className="px-3 py-2 rounded-xl bg-[#030c0e] border border-[#12544F]/50 text-xs text-[#7ea698] hover:text-white transition-colors"
                >
                  Clear
                </button>

                <button
                  onClick={handleAnalyzeText}
                  disabled={isAnalyzingText || !inputText.trim()}
                  className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#2A835F] to-[#12544F] hover:from-[#329b71] hover:to-[#186a64] disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-lg shadow-[#2A835F]/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  {isAnalyzingText ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Analyzing Aspects...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-white" />
                      <span>Analyze Review</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Quick Test Samples */}
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <h4 className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider mb-2.5 flex items-center space-x-1.5">
                <Bookmark className="w-3.5 h-3.5" />
                <span>Quick Test Benchmarks</span>
              </h4>
              <p className="text-xs text-[#649182] mb-3">
                Click any scenario below to populate and run the model immediately:
              </p>
              <div className="space-y-2">
                {SAMPLE_REVIEWS.map((sample, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputText(sample.text);
                      setTextError(null);
                    }}
                    className="w-full text-left p-2.5 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/40 hover:border-[#2A835F]/60 hover:bg-[#12544F]/20 transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white group-hover:text-[#8BBB92] transition-colors">
                        {sample.title}
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 text-[#649182] group-hover:translate-x-0.5 transition-transform" />
                    </div>
                    <p className="text-[11px] text-[#7ea698] mt-1 line-clamp-1 italic">
                      "{sample.text}"
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Output & Detected Aspects */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl min-h-[380px] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40 mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-[#8BBB92]" />
                    <span>ABSA Inference Results</span>
                  </h3>
                  {analysisResult && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#12544F]/40 text-[#8BBB92] border border-[#2A835F]/40">
                      {analysisResult.aspects_count} aspect{analysisResult.aspects_count === 1 ? '' : 's'} detected
                    </span>
                  )}
                </div>

                {/* Loading State */}
                {isAnalyzingText && (
                  <div className="py-16 text-center space-y-3">
                    <RefreshCw className="w-8 h-8 text-[#8BBB92] animate-spin mx-auto" />
                    <p className="text-xs text-[#7ea698]">Segmenting review clauses & scoring polarities...</p>
                  </div>
                )}

                {/* Not Analyzed Yet State */}
                {!isAnalyzingText && !analysisResult && (
                  <div className="py-16 text-center space-y-2 border border-dashed border-[#12544F]/60 rounded-xl bg-[#030c0e]/40 p-6">
                    <Info className="w-8 h-8 text-[#649182] mx-auto" />
                    <p className="text-xs font-semibold text-[#8BBB92]">No prediction generated yet</p>
                    <p className="text-[11px] text-[#649182] max-w-sm mx-auto">
                      Click <strong>Analyze Review</strong> or choose one of the sample benchmarks on the left to inspect aspect detections and sentiment scores.
                    </p>
                  </div>
                )}

                {/* Result: Aspect List */}
                {!isAnalyzingText && analysisResult && (
                  <div className="space-y-3">
                    {/* Empty State when no supported aspects detected */}
                    {!analysisResult.has_aspects ? (
                      <div className="p-5 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-300 text-xs space-y-2">
                        <div className="flex items-center space-x-2 font-bold">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          <span>No Supported Smartphone Aspects Detected</span>
                        </div>
                        <p className="text-[11px] text-[#7ea698] leading-relaxed">
                          This review does not explicitly mention any of the 5 canonical smartphone aspects: <strong>Battery</strong>, <strong>Camera</strong>, <strong>Performance</strong>, <strong>Design</strong>, or <strong>Display</strong>. The system gracefully returns no aspect rather than fabricating an unsubstantiated polarity label.
                        </p>
                      </div>
                    ) : (
                      analysisResult.detected_aspects.map((aspectRes, i) => {
                        const Icon = ASPECT_ICONS[aspectRes.aspect] || Smartphone;
                        const colorClass = ASPECT_COLORS[aspectRes.aspect] || '';
                        return (
                          <div
                            key={i}
                            className="rounded-xl border border-[#12544F]/70 bg-[#030c0e]/90 p-4 transition-all hover:border-[#2A835F]/60 shadow-md"
                          >
                            <div className="flex items-center justify-between mb-2.5">
                              <div className="flex items-center space-x-2.5">
                                <span className={`p-1.5 rounded-lg border ${colorClass}`}>
                                  <Icon className="w-4 h-4" />
                                </span>
                                <div>
                                  <h4 className="text-sm font-bold text-white">
                                    {aspectRes.aspect}
                                  </h4>
                                  <span className="text-[10px] text-[#649182]">
                                    Target Category
                                  </span>
                                </div>
                              </div>

                              <div className="flex items-center space-x-3">
                                {renderSentimentBadge(aspectRes.sentiment)}
                                <span className="text-xs font-mono font-bold text-white" title="Model confidence score">
                                  {Math.round(aspectRes.confidence * 100)}%
                                </span>
                              </div>
                            </div>

                            {/* Confidence Progress Bar */}
                            <div className="w-full bg-[#071b1f] rounded-full h-1.5 mb-2.5 overflow-hidden">
                              <div
                                className={`h-1.5 rounded-full transition-all duration-500 ${
                                  aspectRes.sentiment === 'Positive'
                                    ? 'bg-[#2A835F]'
                                    : aspectRes.sentiment === 'Negative'
                                    ? 'bg-rose-500'
                                    : 'bg-sky-500'
                                }`}
                                style={{ width: `${Math.round(aspectRes.confidence * 100)}%` }}
                              />
                            </div>

                            {/* Evidence Quote */}
                            {aspectRes.evidence_text && (
                              <div className="bg-[#071b1f]/80 rounded-lg p-2.5 border border-[#12544F]/40 text-xs">
                                <span className="text-[10px] uppercase font-bold text-[#649182] block mb-1">
                                  Supporting Evidence Clause:
                                </span>
                                <p className="text-[#8BBB92] italic leading-relaxed">
                                  "{aspectRes.evidence_text}"
                                </p>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>

              {/* Footer Model Metadata */}
              {analysisResult && (
                <div className="mt-4 pt-3 border-t border-[#12544F]/40 flex flex-wrap items-center justify-between text-[11px] text-[#649182]">
                  <span>Model: {analysisResult.model_version}</span>
                  <span>Evaluated in real-time</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 2: WAREHOUSE REVIEW ANALYZER */}
      {activeSubTab === 'warehouse_analyzer' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-6 backdrop-blur-md shadow-xl max-w-3xl">
            <h3 className="text-base font-bold text-white mb-1.5 flex items-center space-x-2">
              <Search className="w-4 h-4 text-[#8BBB92]" />
              <span>Analyze Database Review by ID</span>
            </h3>
            <p className="text-xs text-[#7ea698] mb-4">
              Pulls normalized review text from the Review Warehouse, predicts all discussed smartphone aspects, and optionally stores predictions into the database.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="flex items-center gap-1.5 w-full sm:w-auto">
                <input
                  type="number"
                  min="1"
                  placeholder="Enter Review ID (e.g. 1)"
                  value={warehouseReviewId}
                  onChange={(e) => setWarehouseReviewId(e.target.value)}
                  className="w-full sm:w-56 bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-white placeholder-[#649182] focus:outline-none focus:border-[#2A835F]"
                />
                <button
                  type="button"
                  onClick={() => {
                    const curr = parseInt(warehouseReviewId, 10) || 1;
                    if (curr > 1) setWarehouseReviewId(String(curr - 1));
                  }}
                  className="px-2.5 py-2.5 rounded-xl bg-[#030c0e] border border-[#12544F] text-xs text-[#7ea698] hover:text-white hover:border-[#2A835F] transition-colors"
                  title="Previous Review"
                >
                  ◀
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const curr = parseInt(warehouseReviewId, 10) || 0;
                    setWarehouseReviewId(String(curr + 1));
                  }}
                  className="px-2.5 py-2.5 rounded-xl bg-[#030c0e] border border-[#12544F] text-xs text-[#7ea698] hover:text-white hover:border-[#2A835F] transition-colors"
                  title="Next Review"
                >
                  ▶
                </button>
              </div>

              <label className="flex items-center space-x-2 text-xs text-[#8BBB92] cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={saveToWarehouseDb}
                  onChange={(e) => setSaveToWarehouseDb(e.target.checked)}
                  className="rounded bg-[#030c0e] border-[#12544F] text-[#2A835F] focus:ring-0"
                />
                <span>Persist predictions to database</span>
              </label>

              <button
                onClick={handleAnalyzeWarehouseReview}
                disabled={isAnalyzingWarehouse || !warehouseReviewId}
                className="w-full sm:w-auto flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-[#2A835F] hover:bg-[#329b71] disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-md transition-all"
              >
                {isAnalyzingWarehouse ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Run ABSA</span>
                  </>
                )}
              </button>
            </div>

            {/* Live Review Text Preview Card for Warehouse */}
            {isLoadingWarehousePreview && (
              <div className="mt-3.5 p-3 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/60 text-xs text-[#7ea698] flex items-center space-x-2 animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#8BBB92]" />
                <span>Fetching Review #{warehouseReviewId} preview from database...</span>
              </div>
            )}

            {warehousePreviewError && (
              <div className="mt-3.5 p-2.5 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                <span>{warehousePreviewError}</span>
              </div>
            )}

            {warehouseReviewPreview && (
              <div className="mt-3.5 p-4 rounded-xl bg-[#030c0e] border border-[#2A835F]/60 shadow-lg space-y-2 transition-all">
                <div className="flex items-center justify-between text-[11px] pb-2 border-b border-[#12544F]/40">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-white flex items-center space-x-1">
                      <Smartphone className="w-3.5 h-3.5 text-[#8BBB92]" />
                      <span>{warehouseReviewPreview.product_name || 'Smartphone Device'}</span>
                    </span>
                    {warehouseReviewPreview.product_brand && (
                      <span className="px-1.5 py-0.5 rounded bg-[#071b1f] border border-[#12544F]/50 text-[#7ea698] text-[10px]">
                        {warehouseReviewPreview.product_brand}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2 text-[10px]">
                    {warehouseReviewPreview.rating !== null && warehouseReviewPreview.rating !== undefined && (
                      <span className="text-amber-400 font-bold">★ {warehouseReviewPreview.rating.toFixed(1)}</span>
                    )}
                    <span className="px-1.5 py-0.5 rounded bg-[#12544F]/40 text-[#8BBB92] uppercase font-mono text-[9px]">
                      {warehouseReviewPreview.source || 'Warehouse'}
                    </span>
                  </div>
                </div>

                <div>
                  {warehouseReviewPreview.review_title && (
                    <h5 className="text-xs font-bold text-white mb-1">
                      {warehouseReviewPreview.review_title}
                    </h5>
                  )}
                  <span className="text-[10px] uppercase font-bold text-[#649182] block mb-1">
                    Review Text:
                  </span>
                  <p className="text-xs text-[#d8f0e2] leading-relaxed italic bg-[#071b1f]/90 p-2.5 rounded-lg border border-[#12544F]/50 select-text">
                    "{warehouseReviewPreview.normalized_review_text || warehouseReviewPreview.raw_review_text}"
                  </p>
                </div>
              </div>
            )}

            {warehouseError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{warehouseError}</span>
              </div>
            )}
          </div>

          {/* Warehouse Analysis Results */}
          {warehouseResult && (
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-6 backdrop-blur-md shadow-xl max-w-4xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40">
                <div>
                  <h4 className="text-sm font-bold text-white">
                    Review #{warehouseResult.review_id} Analysis
                  </h4>
                  <p className="text-xs text-[#649182] mt-0.5">
                    Analyzed Text: <span className="text-[#8BBB92] italic">"{warehouseResult.text}"</span>
                  </p>
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#12544F]/40 text-[#8BBB92] border border-[#2A835F]/40">
                  {warehouseResult.aspects_count} Aspects Found
                </span>
              </div>

              {!warehouseResult.has_aspects ? (
                <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-300 text-xs">
                  No canonical smartphone aspects detected for Review #{warehouseResult.review_id}.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {warehouseResult.detected_aspects.map((asp, i) => {
                    const Icon = ASPECT_ICONS[asp.aspect] || Smartphone;
                    return (
                      <div
                        key={i}
                        className="rounded-xl border border-[#12544F]/60 bg-[#030c0e]/90 p-4 space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Icon className="w-4 h-4 text-[#8BBB92]" />
                            <span className="font-bold text-white text-sm">{asp.aspect}</span>
                          </div>
                          {renderSentimentBadge(asp.sentiment)}
                        </div>
                        <div className="text-xs text-[#7ea698]">
                          Confidence: <strong className="text-white font-mono">{Math.round(asp.confidence * 100)}%</strong>
                        </div>
                        {asp.evidence_text && (
                          <p className="text-xs text-[#8BBB92] italic bg-[#071b1f] p-2 rounded-lg border border-[#12544F]/40">
                            "{asp.evidence_text}"
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: MODEL TRAINING & EVALUATION */}
      {activeSubTab === 'training' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Training Control Box */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
                <SlidersHorizontal className="w-4 h-4 text-[#8BBB92]" />
                <span>Supervised Training Pipeline</span>
              </h3>
              <p className="text-xs text-[#7ea698] mb-4 leading-relaxed">
                Retrains the TF-IDF feature vectorizer and multi-class Logistic Regression classifier using verified human annotations merged with the seed benchmark.
              </p>

              <div className="space-y-4 bg-[#030c0e]/80 p-4 rounded-xl border border-[#12544F]/50 text-xs">
                <div>
                  <div className="flex justify-between text-white font-semibold mb-1">
                    <span>Held-Out Test Split:</span>
                    <span className="font-mono text-[#8BBB92]">
                      {Math.round(trainConfig.testSize * 100)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.4"
                    step="0.05"
                    value={trainConfig.testSize}
                    onChange={(e) =>
                      setTrainConfig({ ...trainConfig, testSize: parseFloat(e.target.value) })
                    }
                    className="w-full accent-[#2A835F]"
                  />
                  <div className="flex justify-between text-[10px] text-[#649182] mt-1">
                    <span>10% (More Train)</span>
                    <span>40% (More Test)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-[#7ea698] font-semibold mb-1">
                    Random Seed (Reproducibility):
                  </label>
                  <input
                    type="number"
                    value={trainConfig.randomState}
                    onChange={(e) =>
                      setTrainConfig({
                        ...trainConfig,
                        randomState: parseInt(e.target.value, 10) || 42,
                      })
                    }
                    className="w-full bg-[#071b1f] border border-[#12544F] rounded-lg px-3 py-1.5 text-white font-mono text-xs focus:outline-none focus:border-[#2A835F]"
                  />
                </div>

                <label className="flex items-center space-x-2 cursor-pointer select-none text-white">
                  <input
                    type="checkbox"
                    checked={trainConfig.includeSeedDataset}
                    onChange={(e) =>
                      setTrainConfig({ ...trainConfig, includeSeedDataset: e.target.checked })
                    }
                    className="rounded bg-[#071b1f] border-[#12544F] text-[#2A835F] focus:ring-0"
                  />
                  <span>Include Gold Seed Benchmark Dataset</span>
                </label>
              </div>

              {trainError && (
                <div className="mt-3 p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{trainError}</span>
                </div>
              )}

              {trainResponse && (
                <div className="mt-3 p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs space-y-1">
                  <div className="flex items-center space-x-1.5 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Model Retrained Successfully!</span>
                  </div>
                  <p className="text-[11px] text-[#8BBB92]">
                    Evaluated on {trainResponse.test_samples} held-out test samples. Overall Macro F1: {(trainResponse.overall_macro_f1 * 100).toFixed(1)}%.
                  </p>
                </div>
              )}

              <button
                onClick={handleTrainModel}
                disabled={isTraining}
                className="mt-4 w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-gradient-to-r from-[#2A835F] to-[#12544F] hover:from-[#329b71] hover:to-[#186a64] disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-lg shadow-[#2A835F]/20 transition-all"
              >
                {isTraining ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Training TF-IDF & Logistic Regression...</span>
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4" />
                    <span>Train ABSA Model</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Evaluation Metrics & Confusion Matrix */}
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40 mb-4">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4 text-[#8BBB92]" />
                  <span>Held-Out Test Set Evaluation Report</span>
                </h3>
                {metrics?.test_samples_count && (
                  <span className="text-xs text-[#8BBB92] font-mono">
                    N = {metrics.test_samples_count} Test Samples
                  </span>
                )}
              </div>

              {!metrics?.has_metrics ? (
                <div className="py-12 text-center text-xs text-[#649182]">
                  No evaluation run recorded yet. Click <strong>Train ABSA Model</strong> to generate metrics.
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="bg-[#030c0e] p-3.5 rounded-xl border border-[#12544F]/50">
                      <span className="text-[10px] text-[#649182] uppercase tracking-wider block mb-1">
                        Macro F1-Score
                      </span>
                      <span className="text-xl font-bold font-mono text-[#8BBB92]">
                        {metrics.sentiment_classification_metrics?.macro_f1
                          ? `${(metrics.sentiment_classification_metrics.macro_f1 * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                    </div>

                    <div className="bg-[#030c0e] p-3.5 rounded-xl border border-[#12544F]/50">
                      <span className="text-[10px] text-[#649182] uppercase tracking-wider block mb-1">
                        Macro Precision
                      </span>
                      <span className="text-xl font-bold font-mono text-cyan-400">
                        {metrics.sentiment_classification_metrics?.macro_precision
                          ? `${(metrics.sentiment_classification_metrics.macro_precision * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                    </div>

                    <div className="bg-[#030c0e] p-3.5 rounded-xl border border-[#12544F]/50 col-span-2 sm:col-span-1">
                      <span className="text-[10px] text-[#649182] uppercase tracking-wider block mb-1">
                        Macro Recall
                      </span>
                      <span className="text-xl font-bold font-mono text-purple-400">
                        {metrics.sentiment_classification_metrics?.macro_recall
                          ? `${(metrics.sentiment_classification_metrics.macro_recall * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                    </div>
                  </div>

                  {/* Per-Class Metrics Table */}
                  {metrics.per_class_sentiment_metrics && (
                    <div>
                      <h4 className="text-xs font-bold text-white mb-2">
                        Per-Class Polarity Breakdown
                      </h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-[#030c0e] text-[#8BBB92] border-b border-[#12544F]/60">
                            <tr>
                              <th className="py-2 px-3">Sentiment Class</th>
                              <th className="py-2 px-3 text-center">Precision</th>
                              <th className="py-2 px-3 text-center">Recall</th>
                              <th className="py-2 px-3 text-center">F1-Score</th>
                              <th className="py-2 px-3 text-right">Support</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#12544F]/25">
                            {Object.entries(metrics.per_class_sentiment_metrics).map(([cls, m]) => (
                              <tr key={cls} className="hover:bg-[#12544F]/10">
                                <td className="py-2.5 px-3 font-semibold text-white">
                                  {renderSentimentBadge(cls)}
                                </td>
                                <td className="py-2.5 px-3 text-center font-mono text-cyan-300">
                                  {(m.precision * 100).toFixed(1)}%
                                </td>
                                <td className="py-2.5 px-3 text-center font-mono text-purple-300">
                                  {(m.recall * 100).toFixed(1)}%
                                </td>
                                <td className="py-2.5 px-3 text-center font-mono font-bold text-[#8BBB92]">
                                  {(m.f1_score * 100).toFixed(1)}%
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono text-[#649182]">
                                  {m.support}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Confusion Matrix Table */}
                  {metrics.confusion_matrix && (
                    <div className="pt-2">
                      <h4 className="text-xs font-bold text-white mb-2">
                        Confusion Matrix (Rows: Actual, Cols: Predicted)
                      </h4>
                      <div className="bg-[#030c0e] p-3 rounded-xl border border-[#12544F]/50 overflow-x-auto">
                        <table className="w-full text-center text-xs">
                          <thead>
                            <tr className="text-[#649182]">
                              <th className="py-1 px-2 text-left">Actual \ Pred</th>
                              {metrics.confusion_matrix.classes.map((c) => (
                                <th key={c} className="py-1 px-2 font-mono">{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {metrics.confusion_matrix.matrix.map((row, rIdx) => (
                              <tr key={rIdx} className="border-t border-[#12544F]/20">
                                <td className="py-1.5 px-2 text-left font-semibold text-[#8BBB92]">
                                  {metrics.confusion_matrix.classes[rIdx]}
                                </td>
                                {row.map((val, cIdx) => (
                                  <td
                                    key={cIdx}
                                    className={`py-1.5 px-2 font-mono font-bold ${
                                      rIdx === cIdx
                                        ? 'bg-[#2A835F]/20 text-[#8BBB92]'
                                        : val > 0
                                        ? 'bg-rose-950/20 text-rose-300'
                                        : 'text-[#649182]'
                                    }`}
                                  >
                                    {val}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Split Note */}
                  <div className="p-3 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/40 text-[11px] text-[#649182] flex items-center justify-between">
                    <span>{metrics.data_split_info || 'Stratified train/test split'}</span>
                    <span className="text-[#8BBB92]">Strict Zero Data Leakage</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 4: HUMAN GROUND-TRUTH ANNOTATOR */}
      {activeSubTab === 'annotator' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Annotation Form */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <h3 className="text-sm font-bold text-white mb-1.5 flex items-center space-x-2">
                <Tag className="w-4 h-4 text-[#8BBB92]" />
                <span>Assign Verified Ground-Truth Label</span>
              </h3>
              <p className="text-xs text-[#7ea698] mb-4">
                Research annotation tool to tag reviews with verified aspect sentiments. Separates human verified ground-truth from raw Kaggle stars.
              </p>

              <form onSubmit={handleSaveAnnotation} className="space-y-3.5">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-white">
                      Review ID:
                    </label>
                    <div className="flex items-center space-x-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          const curr = parseInt(annoReviewId, 10) || 1;
                          if (curr > 1) setAnnoReviewId(String(curr - 1));
                        }}
                        className="px-2 py-0.5 rounded-lg bg-[#030c0e] border border-[#12544F] text-[10px] text-[#7ea698] hover:text-white hover:border-[#2A835F] transition-colors"
                        title="Previous Review"
                      >
                        ◀ Prev
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curr = parseInt(annoReviewId, 10) || 0;
                          setAnnoReviewId(String(curr + 1));
                        }}
                        className="px-2 py-0.5 rounded-lg bg-[#030c0e] border border-[#12544F] text-[10px] text-[#7ea698] hover:text-white hover:border-[#2A835F] transition-colors"
                        title="Next Review"
                      >
                        Next ▶
                      </button>
                    </div>
                  </div>
                  <input
                    type="number"
                    min="1"
                    required
                    placeholder="Enter Review ID (e.g., 1)"
                    value={annoReviewId}
                    onChange={(e) => setAnnoReviewId(e.target.value)}
                    className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3.5 py-2 text-xs text-white placeholder-[#649182] focus:outline-none focus:border-[#2A835F]"
                  />
                </div>

                {/* Live Review Text Preview Card */}
                {isLoadingAnnoPreview && (
                  <div className="p-3 rounded-xl bg-[#030c0e]/80 border border-[#12544F]/60 text-xs text-[#7ea698] flex items-center space-x-2 animate-pulse">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#8BBB92]" />
                    <span>Fetching Review #{annoReviewId} preview from database...</span>
                  </div>
                )}

                {annoPreviewError && (
                  <div className="p-2.5 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs flex items-center space-x-2">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                    <span>{annoPreviewError}</span>
                  </div>
                )}

                {annoReviewPreview && (
                  <div className="p-3.5 rounded-xl bg-[#030c0e] border border-[#2A835F]/60 shadow-lg space-y-2 transition-all">
                    <div className="flex items-center justify-between text-[11px] pb-2 border-b border-[#12544F]/40">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white flex items-center space-x-1">
                          <Smartphone className="w-3.5 h-3.5 text-[#8BBB92]" />
                          <span>{annoReviewPreview.product_name || 'Smartphone Device'}</span>
                        </span>
                        {annoReviewPreview.product_brand && (
                          <span className="px-1.5 py-0.5 rounded bg-[#071b1f] border border-[#12544F]/50 text-[#7ea698] text-[10px]">
                            {annoReviewPreview.product_brand}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2 text-[10px]">
                        {annoReviewPreview.rating !== null && annoReviewPreview.rating !== undefined && (
                          <span className="text-amber-400 font-bold">★ {annoReviewPreview.rating.toFixed(1)}</span>
                        )}
                        <span className="px-1.5 py-0.5 rounded bg-[#12544F]/40 text-[#8BBB92] uppercase font-mono text-[9px]">
                          {annoReviewPreview.source || 'Warehouse'}
                        </span>
                      </div>
                    </div>

                    <div>
                      {annoReviewPreview.review_title && (
                        <h5 className="text-xs font-bold text-white mb-1">
                          {annoReviewPreview.review_title}
                        </h5>
                      )}
                      <span className="text-[10px] uppercase font-bold text-[#649182] block mb-1">
                        Review Text Preview:
                      </span>
                      <p className="text-xs text-[#d8f0e2] leading-relaxed italic bg-[#071b1f]/90 p-2.5 rounded-lg border border-[#12544F]/50 select-text">
                        "{annoReviewPreview.normalized_review_text || annoReviewPreview.raw_review_text}"
                      </p>
                    </div>

                    {annoReviewPreview.dataset_sentiment && (
                      <div className="flex items-center space-x-2 text-[10px] text-[#7ea698] pt-0.5">
                        <span>Imported Kaggle Label:</span>
                        <span className={`font-semibold px-2 py-0.5 rounded-full border text-[9px] ${
                          annoReviewPreview.dataset_sentiment.toLowerCase() === 'positive'
                            ? 'bg-[#2A835F]/20 text-[#8BBB92] border-[#2A835F]/50'
                            : annoReviewPreview.dataset_sentiment.toLowerCase() === 'negative'
                            ? 'bg-rose-950/40 text-rose-300 border-rose-800/60'
                            : 'bg-amber-950/40 text-amber-300 border-amber-800/60'
                        }`}>
                          {annoReviewPreview.dataset_sentiment}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-white mb-1">
                      Aspect:
                    </label>
                    <select
                      value={annoAspect}
                      onChange={(e) => setAnnoAspect(e.target.value)}
                      className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#2A835F]"
                    >
                      {['Battery', 'Camera', 'Performance', 'Design', 'Display'].map((asp) => (
                        <option key={asp} value={asp}>{asp}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-white mb-1">
                      Sentiment:
                    </label>
                    <select
                      value={annoSentiment}
                      onChange={(e) => setAnnoSentiment(e.target.value)}
                      className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#2A835F]"
                    >
                      {['Positive', 'Negative', 'Neutral'].map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white mb-1">
                    Annotation Status:
                  </label>
                  <select
                    value={annoStatus}
                    onChange={(e) => setAnnoStatus(e.target.value)}
                    className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#2A835F]"
                  >
                    <option value="VERIFIED">VERIFIED (Eligible for Model Training)</option>
                    <option value="IN_REVIEW">IN_REVIEW (Pending Verification)</option>
                    <option value="UNANNOTATED">UNANNOTATED</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white mb-1">
                    Annotator Notes (Optional):
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Explicit complaint about thermal throttling"
                    value={annoNotes}
                    onChange={(e) => setAnnoNotes(e.target.value)}
                    className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3.5 py-2 text-xs text-white placeholder-[#649182] focus:outline-none focus:border-[#2A835F]"
                  />
                </div>

                {annoSuccessMsg && (
                  <div
                    className={`p-3 rounded-xl border text-xs flex items-center space-x-2 ${
                      annoSuccessMsg.type === 'success'
                        ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                        : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                    }`}
                  >
                    {annoSuccessMsg.type === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    )}
                    <span>{annoSuccessMsg.text}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSavingAnno || !annoReviewId}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-xl bg-[#2A835F] hover:bg-[#329b71] disabled:opacity-50 text-white font-bold text-xs shadow-md transition-all"
                >
                  {isSavingAnno ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Saving Annotation...</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span>Save Verified Annotation</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Annotations Warehouse List */}
          <div className="lg:col-span-7 space-y-4">
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40 mb-3">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-[#8BBB92]" />
                  <span>Existing Ground-Truth Annotations</span>
                </h3>
                <button
                  onClick={loadAnnotations}
                  className="p-1 rounded-lg hover:bg-[#12544F]/40 text-[#7ea698] hover:text-white transition-colors"
                  title="Refresh"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>

              {isLoadingAnnos ? (
                <div className="py-12 text-center text-xs text-[#7ea698]">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#8BBB92]" />
                  Loading annotations...
                </div>
              ) : annotationsList.length === 0 ? (
                <div className="py-12 text-center text-xs text-[#649182]">
                  No annotations added yet. Use the form on the left to add ground-truth labels for database reviews.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#030c0e] text-[#8BBB92] border-b border-[#12544F]/50">
                      <tr>
                        <th className="py-2 px-3">Review</th>
                        <th className="py-2 px-3">Aspect</th>
                        <th className="py-2 px-3">Sentiment</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#12544F]/20">
                      {annotationsList.map((ann) => (
                        <tr key={ann.id} className="hover:bg-[#12544F]/10">
                          <td className="py-2.5 px-3 font-mono font-bold text-white">
                            #{ann.review_id}
                          </td>
                          <td className="py-2.5 px-3 font-medium text-cyan-300">
                            {ann.aspect}
                          </td>
                          <td className="py-2.5 px-3">
                            {renderSentimentBadge(ann.sentiment)}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                                ann.status === 'VERIFIED'
                                  ? 'bg-[#2A835F]/20 text-[#8BBB92] border-[#2A835F]/50'
                                  : 'bg-amber-950/20 text-amber-300 border-amber-800/40'
                              }`}
                            >
                              {ann.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-[#7ea698] max-w-[150px] truncate" title={ann.annotator_notes || ''}>
                            {ann.annotator_notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
