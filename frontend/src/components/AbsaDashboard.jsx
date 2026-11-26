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
  FileText,
  Bookmark,
  ChevronRight,
  Info,
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
  Battery: 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50',
  Camera: 'bg-sky-950/40 text-sky-400 border-sky-800/50',
  Performance: 'bg-purple-950/40 text-purple-400 border-purple-800/50',
  Design: 'bg-amber-950/40 text-amber-400 border-amber-800/50',
  Display: 'bg-teal-950/40 text-[#8BBB92] border-[#2A835F]/50',
};

export default function AbsaDashboard({ products = [], onNavigateToReviews }) {
  // Live text analyzer state
  const [inputText, setInputText] = useState(SAMPLE_REVIEWS[0].text);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzingText, setIsAnalyzingText] = useState(false);
  const [textError, setTextError] = useState(null);

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
        <div className="space-y-1.5 max-w-4xl">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-[#8BBB92] bg-[#2A835F]/20 px-2.5 py-0.5 rounded-md border border-[#2A835F]/40">
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
      </div>

      {/* LIVE TEXT ANALYZER */}
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
              <div className="mt-4 pt-3 border-t border-[#12544F]/40 flex items-center justify-end text-[11px] text-[#649182]">
                <span>Evaluated in real-time</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
