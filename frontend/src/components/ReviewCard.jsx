import React, { useState } from 'react';
import { Star, ThumbsUp, Calendar, User, Smartphone, Hash, Code, Sparkles, RefreshCw } from 'lucide-react';
import { api } from '../api/client';

export default function ReviewCard({ review }) {
  const [showNormalized, setShowNormalized] = useState(false);
  const [absaResult, setAbsaResult] = useState(null);
  const [isAnalyzingAbsa, setIsAnalyzingAbsa] = useState(false);
  const [showAbsa, setShowAbsa] = useState(false);

  const handleToggleAbsa = async () => {
    if (showAbsa) {
      setShowAbsa(false);
      return;
    }
    setShowAbsa(true);
    if (!absaResult) {
      setIsAnalyzingAbsa(true);
      try {
        const text = review.normalized_review_text || review.raw_review_text;
        const res = await api.predictAbsa(text, false);
        setAbsaResult(res);
      } catch (err) {
        console.error('Failed to analyze ABSA for review:', err);
      } finally {
        setIsAnalyzingAbsa(false);
      }
    }
  };

  const renderStars = (rating) => {
    if (rating === null || rating === undefined) return null;
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.5;

    return (
      <div className="flex items-center space-x-1">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={`w-3.5 h-3.5 ${
              i < fullStars || (i === fullStars && hasHalf)
                ? 'text-amber-400 fill-amber-400'
                : 'text-[#12544F]'
            }`}
          />
        ))}
        <span className="text-xs font-bold text-amber-400 ml-1.5">
          {rating.toFixed(1)}
        </span>
      </div>
    );
  };

  return (
    <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-5 backdrop-blur-md shadow-lg transition-all duration-200 hover:border-[#2A835F]/60 hover:bg-[#071b1f]">
      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#12544F]/50">
        <div className="flex items-center space-x-2">
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#12544F]/40 text-[#8BBB92] border border-[#2A835F]/40">
            <Smartphone className="w-3 h-3 text-[#8BBB92]" />
            <span>{review.product_name || 'Smartphone'}</span>
          </span>
          {review.product_brand && (
            <span className="text-xs px-2 py-0.5 rounded bg-[#030c0e] border border-[#12544F]/50 text-[#7ea698] font-medium">
              {review.product_brand}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {renderStars(review.rating)}
          <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-[#030c0e] text-[#8BBB92] border border-[#12544F]/50">
            {review.source}
          </span>
          {review.ingestion_method === 'kaggle_import' ? (
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/50 font-medium">
              Kaggle Import
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#12544F]/20 text-[#7ea698] border border-[#12544F]/40">
              Scraper
            </span>
          )}
        </div>
      </div>

      {/* Title & Body */}
      <div className="mt-3">
        {review.review_title && (
          <h4 className="text-sm font-bold text-white mb-1.5">
            {review.review_title}
          </h4>
        )}
        <p className="text-xs text-[#d8f0e2] leading-relaxed">
          {showNormalized && review.normalized_review_text
            ? review.normalized_review_text
            : review.raw_review_text}
        </p>
        {review.dataset_sentiment && (
          <div className="mt-2.5 flex items-center space-x-2">
            <span className="text-[10px] text-[#7ea698]">Kaggle Sentiment Label:</span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
              review.dataset_sentiment.toLowerCase() === 'positive'
                ? 'bg-[#2A835F]/20 text-[#8BBB92] border-[#2A835F]/50'
                : review.dataset_sentiment.toLowerCase() === 'negative'
                ? 'bg-rose-950/40 text-rose-300 border-rose-800/60'
                : 'bg-amber-950/40 text-amber-300 border-amber-800/60'
            }`}>
              {review.dataset_sentiment}
            </span>
          </div>
        )}

        {/* Inline ABSA Analysis Tray */}
        {showAbsa && (
          <div className="mt-3 p-3 rounded-xl bg-[#030c0e]/90 border border-[#12544F]/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-white flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5 text-[#8BBB92]" />
                <span>Aspect-Based Sentiment Analysis</span>
              </span>
              {isAnalyzingAbsa && (
                <span className="text-[10px] text-[#8BBB92] flex items-center space-x-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span>Analyzing...</span>
                </span>
              )}
            </div>

            {!isAnalyzingAbsa && absaResult && (
              <div>
                {!absaResult.has_aspects ? (
                  <p className="text-[11px] text-[#7ea698] italic">
                    No canonical smartphone aspects detected in this review.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {absaResult.detected_aspects.map((asp, idx) => (
                      <div
                        key={idx}
                        className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg border flex items-center space-x-1.5 ${
                          asp.sentiment === 'Positive'
                            ? 'bg-[#2A835F]/20 text-[#8BBB92] border-[#2A835F]/50'
                            : asp.sentiment === 'Negative'
                            ? 'bg-rose-950/30 text-rose-300 border-rose-800/60'
                            : 'bg-sky-950/30 text-sky-300 border-sky-800/60'
                        }`}
                      >
                        <span className="font-bold text-white">{asp.aspect}:</span>
                        <span>{asp.sentiment}</span>
                        <span className="text-[9px] opacity-75 font-mono">({Math.round(asp.confidence * 100)}%)</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Details */}
      <div className="mt-4 pt-3 border-t border-[#12544F]/50 flex flex-wrap items-center justify-between gap-2 text-xs text-[#649182]">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1 text-[#7ea698]">
            <User className="w-3.5 h-3.5 text-[#649182]" />
            <span>{review.reviewer_name || 'Anonymous Reviewer'}</span>
          </span>
          {(review.review_date || review.review_date_raw) && (
            <span className="flex items-center space-x-1 text-[#7ea698]">
              <Calendar className="w-3.5 h-3.5 text-[#649182]" />
              <span>{review.review_date || review.review_date_raw}</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {review.helpful_count > 0 && (
            <span className="flex items-center space-x-1 text-[#8BBB92] bg-[#12544F]/30 border border-[#12544F]/60 px-2 py-0.5 rounded font-medium text-[11px]">
              <ThumbsUp className="w-3 h-3" />
              <span>{review.helpful_count} helpful</span>
            </span>
          )}

          <button
            onClick={handleToggleAbsa}
            className={`flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded border transition-colors ${
              showAbsa
                ? 'bg-[#2A835F]/30 text-white border-[#2A835F]'
                : 'text-[#8BBB92] hover:text-white border-[#12544F]/60 hover:bg-[#12544F]/40'
            }`}
          >
            <Sparkles className="w-3 h-3 text-[#8BBB92]" />
            <span>{showAbsa ? 'Hide ABSA' : 'Analyze ABSA'}</span>
          </button>

          {review.normalized_review_text && (
            <button
              onClick={() => setShowNormalized(!showNormalized)}
              className="flex items-center space-x-1 text-[11px] text-[#8BBB92] hover:text-[#f2fbf6] transition-colors"
            >
              <Code className="w-3 h-3" />
              <span>{showNormalized ? 'Show Raw' : 'Show Clean'}</span>
            </button>
          )}

          <span title={`Hash: ${review.content_hash}`} className="text-[#649182] hover:text-[#8BBB92] text-[10px] flex items-center">
            <Hash className="w-3 h-3 mr-0.5" />
            {review.content_hash.slice(0, 6)}
          </span>
        </div>
      </div>
    </div>
  );
}
