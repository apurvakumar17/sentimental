import React, { useState, useEffect } from 'react';
import {
  Award,
  Sparkles,
  SlidersHorizontal,
  Smartphone,
  BatteryCharging,
  Camera,
  Cpu,
  Tv,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  TrendingUp,
  X,
  Scale,
  ChevronRight,
  Info,
  DollarSign,
  ShieldCheck,
  Check,
  BarChart3,
  ExternalLink,
  Layers,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';

const ASPECT_ICONS = {
  Battery: BatteryCharging,
  Camera: Camera,
  Performance: Cpu,
  Design: Smartphone,
  Display: Tv,
};

const ASPECT_COLORS = {
  Battery: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  Camera: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
  Performance: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  Design: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  Display: 'text-pink-400 bg-pink-500/10 border-pink-500/30',
};

const PRESET_QUICK_FILTERS = [
  {
    label: 'Best Camera ($300–$700)',
    minPrice: 300,
    maxPrice: 700,
    priorities: ['Camera', 'Battery', 'Performance'],
    brands: [],
  },
  {
    label: 'Battery Beast (Under $500)',
    minPrice: 0,
    maxPrice: 500,
    priorities: ['Battery', 'Performance', 'Display'],
    brands: [],
  },
  {
    label: 'Flagship Performance ($700+)',
    minPrice: 700,
    maxPrice: 1500,
    priorities: ['Performance', 'Camera', 'Display'],
    brands: [],
  },
  {
    label: 'Budget All-Rounder (Under $400)',
    minPrice: 0,
    maxPrice: 400,
    priorities: ['Performance', 'Battery', 'Camera'],
    brands: [],
  },
];

const BUDGET_PRESETS = [
  { label: 'All Budgets', min: null, max: null },
  { label: 'Budget (< $300)', min: 0, max: 300 },
  { label: 'Mid-Range ($300–$600)', min: 300, max: 600 },
  { label: 'Premium ($600–$1,000)', min: 600, max: 1000 },
  { label: 'Flagship ($1,000+)', min: 1000, max: 2500 },
];

export default function RecommendationDashboard({ onNavigateToReviews }) {
  // Query States
  const [minPrice, setMinPrice] = useState(300);
  const [maxPrice, setMaxPrice] = useState(800);
  const [selectedBrands, setSelectedBrands] = useState([]);
  const [priorities, setPriorities] = useState(['Camera', 'Battery', 'Performance']);
  const [minEvidence, setMinEvidence] = useState(1);
  const [availableBrands, setAvailableBrands] = useState([]);

  // Results & Loading
  const [recommendationsData, setRecommendationsData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Side-by-side comparison state
  const [comparisonIds, setComparisonIds] = useState([]);
  const [comparisonData, setComparisonData] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  // Product detailed scores modal
  const [inspectProductId, setInspectProductId] = useState(null);
  const [inspectScoresData, setInspectScoresData] = useState(null);
  const [isInspectLoading, setIsInspectLoading] = useState(false);

  // Sync predictions status
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState(null);

  // Fetch initial products and brand catalog
  useEffect(() => {
    loadBrandCatalog();
    handleFetchRecommendations();
  }, []);

  const loadBrandCatalog = async () => {
    try {
      const prods = await api.getRecommendationProducts();
      if (Array.isArray(prods)) {
        const uniqueBrands = Array.from(
          new Set(prods.map((p) => p.brand).filter(Boolean))
        ).sort();
        setAvailableBrands(uniqueBrands);
      }
    } catch (err) {
      console.error('Failed to load recommendation catalog brands:', err);
    }
  };

  const handleFetchRecommendations = async (overrideParams = {}) => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = {
        min_price: overrideParams.minPrice !== undefined ? overrideParams.minPrice : (minPrice ? Number(minPrice) : null),
        max_price: overrideParams.maxPrice !== undefined ? overrideParams.maxPrice : (maxPrice ? Number(maxPrice) : null),
        brands: overrideParams.brands !== undefined ? overrideParams.brands : (selectedBrands.length > 0 ? selectedBrands : null),
        priorities: overrideParams.priorities !== undefined ? overrideParams.priorities : priorities,
        min_evidence_count: overrideParams.minEvidence !== undefined ? overrideParams.minEvidence : Number(minEvidence),
        limit: 10,
      };

      const data = await api.getRecommendations(payload);
      setRecommendationsData(data);
    } catch (err) {
      console.error('Recommendation fetch failed:', err);
      setError(err.message || 'Failed to generate recommendations. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const applyQuickFilter = (preset) => {
    setMinPrice(preset.minPrice);
    setMaxPrice(preset.maxPrice);
    setPriorities(preset.priorities);
    setSelectedBrands(preset.brands);
    handleFetchRecommendations({
      minPrice: preset.minPrice,
      maxPrice: preset.maxPrice,
      priorities: preset.priorities,
      brands: preset.brands,
    });
  };

  const applyBudgetPreset = (preset) => {
    setMinPrice(preset.min !== null ? preset.min : '');
    setMaxPrice(preset.max !== null ? preset.max : '');
  };

  const toggleBrand = (brand) => {
    setSelectedBrands((prev) =>
      prev.includes(brand) ? prev.filter((b) => b !== brand) : [...prev, brand]
    );
  };

  const togglePriorityAspect = (aspect) => {
    setPriorities((prev) => {
      if (prev.includes(aspect)) {
        if (prev.length <= 1) return prev; // Keep at least one
        return prev.filter((a) => a !== aspect);
      } else {
        return [...prev, aspect];
      }
    });
  };

  const movePriority = (index, direction) => {
    setPriorities((prev) => {
      const updated = [...prev];
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= updated.length) return prev;
      const temp = updated[index];
      updated[index] = updated[targetIndex];
      updated[targetIndex] = temp;
      return updated;
    });
  };

  // Compare Dock Actions
  const toggleComparisonProduct = (productId) => {
    setComparisonIds((prev) => {
      if (prev.includes(productId)) {
        return prev.filter((id) => id !== productId);
      } else {
        if (prev.length >= 4) {
          alert('You can compare up to 4 devices simultaneously.');
          return prev;
        }
        return [...prev, productId];
      }
    });
  };

  const handleRunComparison = async () => {
    if (comparisonIds.length < 2) return;
    setIsComparing(true);
    setIsCompareModalOpen(true);
    try {
      const data = await api.compareProducts(comparisonIds, priorities);
      setComparisonData(data);
    } catch (err) {
      console.error('Comparison error:', err);
      alert('Failed to generate product comparison: ' + err.message);
    } finally {
      setIsComparing(false);
    }
  };

  // Score Inspector Modal
  const handleInspectScores = async (productId) => {
    setInspectProductId(productId);
    setIsInspectLoading(true);
    try {
      const data = await api.getProductScores(productId);
      setInspectScoresData(data);
    } catch (err) {
      console.error('Inspect scores error:', err);
      alert('Failed to fetch detailed product score breakdown: ' + err.message);
    } finally {
      setIsInspectLoading(false);
    }
  };

  // Sync predictions
  const handleSyncPredictions = async () => {
    setIsSyncing(true);
    setSyncStatusMsg(null);
    try {
      const res = await api.syncPredictions(30);
      setSyncStatusMsg(
        `Synced ${res.total_predictions_stored} ABSA predictions across ${res.products_processed} smartphones.`
      );
      handleFetchRecommendations();
    } catch (err) {
      console.error('Sync predictions error:', err);
      setSyncStatusMsg('Sync failed: ' + err.message);
    } finally {
      setIsSyncing(false);
    }
  };

  const allAspects = ['Battery', 'Camera', 'Performance', 'Design', 'Display'];

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return 'text-zinc-500';
    if (score >= 70) return 'text-emerald-400';
    if (score >= 55) return 'text-teal-400';
    if (score >= 45) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getScoreBgColor = (score) => {
    if (score === null || score === undefined) return 'bg-zinc-800';
    if (score >= 70) return 'bg-emerald-500';
    if (score >= 55) return 'bg-teal-500';
    if (score >= 45) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#071b1f] via-[#0b292f] to-[#071b1f] border border-[#12544F]/60 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-[#2A835F]/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-[#12544F] to-[#2A835F]/60 text-white shadow-lg shadow-[#2A835F]/30 border border-[#8BBB92]/40">
                <Award className="w-6 h-6 text-[#8BBB92]" />
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/40">
                Phase 4: Multi-Criteria Recommendation
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Smartphone Recommendation Engine
            </h1>
            <p className="text-sm text-[#7ea698] max-w-2xl leading-relaxed">
              Ranks smartphones by matching your custom budget and brand preferences against
              rigorously aggregated Aspect-Based Sentiment Analysis (ABSA) evidence using Bayesian
              credibility smoothing.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <button
              onClick={handleSyncPredictions}
              disabled={isSyncing}
              className="flex items-center justify-center space-x-2 px-3.5 py-2.5 rounded-xl bg-[#030c0e]/80 border border-[#12544F] text-xs font-semibold text-[#8BBB92] hover:bg-[#12544F]/40 hover:text-white transition-all disabled:opacity-50"
              title="Populate ABSA sentiment evidence for catalog smartphones"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Syncing ABSA...' : 'Sync Predictions'}</span>
            </button>
            <button
              onClick={() => handleFetchRecommendations()}
              disabled={isLoading}
              className="flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#12544F] via-[#2A835F] to-[#12544F] text-white text-sm font-bold shadow-lg shadow-[#2A835F]/30 hover:shadow-[#2A835F]/50 border border-[#8BBB92]/50 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>{isLoading ? 'Ranking Phones...' : 'Run Recommendations'}</span>
            </button>
          </div>
        </div>

        {syncStatusMsg && (
          <div className="mt-4 p-3 rounded-xl bg-[#12544F]/30 border border-[#2A835F]/50 text-xs text-[#8BBB92] flex items-center justify-between">
            <span>{syncStatusMsg}</span>
            <button onClick={() => setSyncStatusMsg(null)} className="text-[#7ea698] hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Quick Presets Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        <span className="text-xs font-semibold text-[#7ea698] shrink-0 flex items-center space-x-1">
          <Sparkles className="w-3.5 h-3.5 text-[#8BBB92]" />
          <span>Quick Presets:</span>
        </span>
        {PRESET_QUICK_FILTERS.map((preset, idx) => (
          <button
            key={idx}
            onClick={() => applyQuickFilter(preset)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#071b1f] hover:bg-[#12544F]/60 text-[#8BBB92] hover:text-white border border-[#12544F]/60 hover:border-[#2A835F] transition-all shrink-0 whitespace-nowrap"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Main Grid: Preferences Controls & Results */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Preferences Controls (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-[#071b1f]/90 border border-[#12544F]/60 rounded-2xl p-5 shadow-xl space-y-6 backdrop-blur-md">
            <div className="flex items-center justify-between pb-3 border-b border-[#12544F]/40">
              <div className="flex items-center space-x-2">
                <SlidersHorizontal className="w-4 h-4 text-[#8BBB92]" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  User Preferences
                </h2>
              </div>
              <button
                onClick={() => {
                  setMinPrice(300);
                  setMaxPrice(800);
                  setSelectedBrands([]);
                  setPriorities(['Camera', 'Battery', 'Performance']);
                  setMinEvidence(1);
                }}
                className="text-xs text-[#7ea698] hover:text-white font-medium transition-colors"
              >
                Reset
              </button>
            </div>

            {/* 1. Budget Filter */}
            <div className="space-y-3">
              <label className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider flex items-center space-x-1.5">
                <DollarSign className="w-3.5 h-3.5" />
                <span>Price Budget (USD)</span>
              </label>

              {/* Budget Quick Chips */}
              <div className="grid grid-cols-2 gap-1.5">
                {BUDGET_PRESETS.map((bp, i) => (
                  <button
                    key={i}
                    onClick={() => applyBudgetPreset(bp)}
                    className="px-2 py-1 rounded-md text-[11px] font-medium bg-[#030c0e] hover:bg-[#12544F]/40 text-[#7ea698] hover:text-white border border-[#12544F]/40 transition-colors text-left truncate"
                  >
                    {bp.label}
                  </button>
                ))}
              </div>

              {/* Min & Max Inputs */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-[11px] text-[#649182] font-medium mb-1 block">Min Price ($)</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 200"
                    value={minPrice}
                    onChange={(e) => setMinPrice(e.target.value)}
                    className="w-full bg-[#030c0e] border border-[#12544F]/80 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#2A835F] transition-all"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-[#649182] font-medium mb-1 block">Max Price ($)</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 800"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(e.target.value)}
                    className="w-full bg-[#030c0e] border border-[#12544F]/80 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#2A835F] transition-all"
                  />
                </div>
              </div>
            </div>

            {/* 2. Priority Ordering */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider flex items-center space-x-1.5">
                  <Award className="w-3.5 h-3.5" />
                  <span>Aspect Priorities</span>
                </label>
                <span className="text-[10px] text-[#649182]">Reorder by importance</span>
              </div>
              <p className="text-[11px] text-[#7ea698] leading-tight">
                Higher ranked priorities carry greater exponential weight in recommendation scoring.
              </p>

              {/* Active ordered priorities */}
              <div className="space-y-1.5">
                {priorities.map((asp, idx) => {
                  const Icon = ASPECT_ICONS[asp] || Smartphone;
                  const rankWeightLabel = idx === 0 ? '5.0x' : idx === 1 ? '2.5x' : idx === 2 ? '1.5x' : '1.0x';
                  return (
                    <div
                      key={asp}
                      className="flex items-center justify-between p-2 rounded-xl bg-[#030c0e] border border-[#12544F]/70 group hover:border-[#2A835F] transition-all"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold bg-[#12544F]/60 text-[#8BBB92]">
                          #{idx + 1}
                        </span>
                        <Icon className="w-4 h-4 text-[#8BBB92]" />
                        <span className="text-xs font-semibold text-white">{asp}</span>
                      </div>

                      <div className="flex items-center space-x-1.5">
                        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/30">
                          {rankWeightLabel}
                        </span>
                        <div className="flex items-center">
                          <button
                            onClick={() => movePriority(idx, -1)}
                            disabled={idx === 0}
                            className="p-1 rounded text-[#649182] hover:text-white disabled:opacity-20 hover:bg-[#12544F]/40"
                            title="Move up"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => movePriority(idx, 1)}
                            disabled={idx === priorities.length - 1}
                            className="p-1 rounded text-[#649182] hover:text-white disabled:opacity-20 hover:bg-[#12544F]/40"
                            title="Move down"
                          >
                            ▼
                          </button>
                        </div>
                        <button
                          onClick={() => togglePriorityAspect(asp)}
                          className="p-1 text-zinc-500 hover:text-rose-400"
                          title="Remove priority"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Add other aspects if any missing */}
              {allAspects.some((a) => !priorities.includes(a)) && (
                <div className="pt-1">
                  <span className="text-[10px] text-[#649182] block mb-1">Add additional aspect:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {allAspects
                      .filter((a) => !priorities.includes(a))
                      .map((asp) => (
                        <button
                          key={asp}
                          onClick={() => togglePriorityAspect(asp)}
                          className="px-2 py-1 rounded-md text-[11px] font-medium bg-[#030c0e] hover:bg-[#12544F]/50 text-[#8BBB92] border border-[#12544F]/50 flex items-center space-x-1"
                        >
                          <span>+ {asp}</span>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* 3. Brand Preferences */}
            <div className="space-y-3">
              <label className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider flex items-center justify-between">
                <span>Brand Selection</span>
                <span className="text-[10px] text-[#649182]">
                  {selectedBrands.length === 0 ? 'All Brands' : `${selectedBrands.length} selected`}
                </span>
              </label>

              <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto no-scrollbar pr-1">
                <button
                  onClick={() => setSelectedBrands([])}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                    selectedBrands.length === 0
                      ? 'bg-[#12544F] text-white border border-[#2A835F]'
                      : 'bg-[#030c0e] text-[#7ea698] border border-[#12544F]/50 hover:text-white'
                  }`}
                >
                  All Brands
                </button>
                {availableBrands.map((brand) => {
                  const isSelected = selectedBrands.includes(brand);
                  return (
                    <button
                      key={brand}
                      onClick={() => toggleBrand(brand)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-[#2A835F] text-white border border-[#8BBB92]'
                          : 'bg-[#030c0e] text-[#7ea698] border border-[#12544F]/50 hover:text-white'
                      }`}
                    >
                      {brand}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 4. Minimum Evidence Requirement */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Min Review Evidence</span>
                </label>
                <span className="text-xs font-semibold text-white">≥ {minEvidence} reviews</span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="1"
                value={minEvidence}
                onChange={(e) => setMinEvidence(e.target.value)}
                className="w-full accent-[#2A835F] bg-[#030c0e] cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-[#649182]">
                <span>0 (All)</span>
                <span>5</span>
                <span>10</span>
                <span>20+</span>
              </div>
            </div>

            {/* Primary Action Button */}
            <button
              onClick={() => handleFetchRecommendations()}
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[#12544F] via-[#2A835F] to-[#12544F] text-white text-sm font-bold shadow-xl shadow-[#2A835F]/20 hover:shadow-[#2A835F]/40 border border-[#8BBB92]/60 hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
            >
              <Sparkles className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>{isLoading ? 'Ranking Smartphones...' : 'Generate Recommendations'}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Ranked Recommendations Results (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Status Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#071b1f]/60 border border-[#12544F]/40 rounded-xl px-4 py-3">
            <div className="flex items-center space-x-2">
              <Award className="w-4 h-4 text-[#8BBB92]" />
              <span className="text-sm font-bold text-white">
                {recommendationsData
                  ? `${recommendationsData.matched_products_count} Smartphones Recommended`
                  : 'Ready to Recommend'}
              </span>
              {recommendationsData?.applied_budget_filter && (
                <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#12544F]/40 text-[#8BBB92] border border-[#2A835F]/30">
                  {recommendationsData.applied_budget_filter}
                </span>
              )}
            </div>

            {comparisonIds.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-[#8BBB92] font-medium">
                  {comparisonIds.length} selected for comparison
                </span>
                <button
                  onClick={handleRunComparison}
                  disabled={comparisonIds.length < 2 || isComparing}
                  className="px-3 py-1 rounded-lg text-xs font-bold bg-[#2A835F] text-white shadow-sm hover:bg-[#1e7a68] transition-all disabled:opacity-40"
                >
                  Compare ({comparisonIds.length})
                </button>
              </div>
            )}
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="p-12 rounded-2xl bg-[#071b1f]/40 border border-[#12544F]/40 flex flex-col items-center justify-center space-y-4 text-center">
              <div className="w-10 h-10 border-2 border-[#2A835F] border-t-transparent rounded-full animate-spin" />
              <div className="space-y-1">
                <p className="text-sm font-bold text-white">Aggregating Aspect Sentiment...</p>
                <p className="text-xs text-[#7ea698]">
                  Applying Bayesian shrinkage & calculating multi-criteria priority scores.
                </p>
              </div>
            </div>
          )}

          {/* Error State */}
          {!isLoading && error && (
            <div className="p-6 rounded-2xl bg-rose-950/20 border border-rose-500/30 text-rose-300 space-y-2">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-rose-400" />
                <h3 className="text-sm font-bold">Recommendation Error</h3>
              </div>
              <p className="text-xs">{error}</p>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && recommendationsData?.recommendations?.length === 0 && (
            <div className="p-12 rounded-2xl bg-[#071b1f]/40 border border-[#12544F]/40 flex flex-col items-center justify-center space-y-4 text-center">
              <div className="p-3 rounded-full bg-[#12544F]/30 text-[#8BBB92]">
                <Smartphone className="w-8 h-8" />
              </div>
              <div className="space-y-1 max-w-md">
                <h3 className="text-base font-bold text-white">No Matching Smartphones Found</h3>
                <p className="text-xs text-[#7ea698]">
                  {recommendationsData.empty_state_reason ||
                    'Try widening your budget range, including more brands, or decreasing the minimum review requirement.'}
                </p>
              </div>
              <button
                onClick={() => {
                  setMinPrice(0);
                  setMaxPrice(2000);
                  setSelectedBrands([]);
                  setMinEvidence(0);
                  handleFetchRecommendations({ minPrice: 0, maxPrice: 2000, brands: null, minEvidence: 0 });
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#12544F]/60 text-[#8BBB92] hover:text-white border border-[#2A835F]/40"
              >
                Reset All Filters
              </button>
            </div>
          )}

          {/* Ranked Cards List */}
          {!isLoading && !error && recommendationsData?.recommendations?.map((item) => {
            const isSelectedForCompare = comparisonIds.includes(item.product_id);
            const isRank1 = item.rank === 1;
            const isRank2 = item.rank === 2;
            const isRank3 = item.rank === 3;

            const rankBadgeColor = isRank1
              ? 'bg-gradient-to-r from-amber-400 to-amber-600 text-black border-amber-300'
              : isRank2
              ? 'bg-gradient-to-r from-slate-200 to-slate-400 text-black border-slate-200'
              : isRank3
              ? 'bg-gradient-to-r from-amber-700 to-amber-900 text-white border-amber-600'
              : 'bg-[#12544F]/60 text-[#8BBB92] border-[#2A835F]/40';

            return (
              <div
                key={item.product_id}
                className={`relative rounded-2xl bg-[#071b1f]/90 border transition-all duration-300 p-5 sm:p-6 shadow-xl ${
                  isRank1
                    ? 'border-[#2A835F] shadow-[0_0_25px_rgba(42,131,95,0.15)] ring-1 ring-[#8BBB92]/40'
                    : 'border-[#12544F]/60 hover:border-[#2A835F]/80'
                }`}
              >
                {/* Top Section: Rank, Title, Price, Overall Score */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-[#12544F]/40">
                  <div className="flex items-start space-x-3.5">
                    {/* Rank Badge */}
                    <div
                      className={`w-10 h-10 rounded-xl flex flex-col items-center justify-center font-extrabold text-sm shrink-0 border shadow-md ${rankBadgeColor}`}
                    >
                      <span className="text-[10px] leading-none uppercase">Rank</span>
                      <span className="text-base leading-none">#{item.rank}</span>
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider">
                          {item.brand}
                        </span>
                        {item.price_usd && (
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[#12544F]/40 text-emerald-300 border border-[#2A835F]/30">
                            ${Math.round(item.price_usd)} USD
                          </span>
                        )}
                        {!item.price_usd && (
                          <span className="text-[11px] text-[#649182] italic">
                            Price unavailable
                          </span>
                        )}
                      </div>
                      <h3 className="text-lg font-bold text-white tracking-tight mt-0.5">
                        {item.product_name}
                      </h3>
                      <div className="flex items-center space-x-3 text-xs text-[#7ea698] mt-1">
                        <span>{item.total_reviews} Total Reviews</span>
                        <span>•</span>
                        <span>{item.absa_predictions_count} ABSA Records</span>
                      </div>
                    </div>
                  </div>

                  {/* Overall Score Badge */}
                  <div className="flex items-center sm:flex-col items-end shrink-0 gap-2 sm:gap-1 bg-[#030c0e]/80 sm:bg-transparent p-3 sm:p-0 rounded-xl border sm:border-0 border-[#12544F]/40">
                    <div className="text-right">
                      <span className="text-[11px] text-[#649182] uppercase tracking-wider block font-semibold">
                        Overall Score
                      </span>
                      <div className="flex items-baseline space-x-1">
                        <span className={`text-2xl sm:text-3xl font-black ${getScoreColor(item.overall_score)}`}>
                          {item.overall_score !== null ? item.overall_score : 'N/A'}
                        </span>
                        <span className="text-xs text-[#649182] font-bold">/ 100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Aspect Scores Grid */}
                <div className="py-4 space-y-2.5">
                  <span className="text-xs font-bold text-[#8BBB92] uppercase tracking-wider block">
                    Aspect-Level Performance
                  </span>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 sm:gap-2.5">
                    {allAspects.map((asp) => {
                      const Icon = ASPECT_ICONS[asp] || Smartphone;
                      const aspItem = item.aspect_scores[asp];
                      const isAvail = aspItem && aspItem.is_available && aspItem.score !== null;
                      const scoreVal = isAvail ? aspItem.score : null;
                      const isUserPriority = priorities.includes(asp);

                      return (
                        <div
                          key={asp}
                          className={`p-2.5 rounded-xl border transition-all ${
                            isUserPriority
                              ? 'bg-[#030c0e] border-[#2A835F]/60 shadow-sm'
                              : 'bg-[#030c0e]/60 border-[#12544F]/40'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center space-x-1.5">
                              <Icon className="w-3.5 h-3.5 text-[#8BBB92]" />
                              <span className="text-xs font-semibold text-white">{asp}</span>
                            </div>
                            {isUserPriority && (
                              <span className="w-1.5 h-1.5 rounded-full bg-[#8BBB92]" title="User Priority" />
                            )}
                          </div>

                          {isAvail ? (
                            <div className="space-y-1.5">
                              <div className="flex items-baseline justify-between">
                                <span className={`text-base font-extrabold ${getScoreColor(scoreVal)}`}>
                                  {scoreVal}
                                </span>
                                <span className="text-[10px] text-[#649182]">
                                  n={aspItem.evidence_count}
                                </span>
                              </div>
                              {/* Mini Score Progress Bar */}
                              <div className="w-full bg-[#071b1f] h-1.5 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all duration-500 ${getScoreBgColor(scoreVal)}`}
                                  style={{ width: `${Math.min(Math.max(scoreVal, 0), 100)}%` }}
                                />
                              </div>
                            </div>
                          ) : (
                            <div className="py-1">
                              <span className="text-[10px] text-zinc-500 block italic leading-tight">
                                Unavailable
                              </span>
                              <span className="text-[9px] text-zinc-600">No ABSA data</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Natural Language Recommendation Explanation */}
                <div className="p-3.5 rounded-xl bg-[#030c0e]/90 border border-[#12544F]/50 space-y-1.5">
                  <div className="flex items-center space-x-2 text-xs font-bold text-[#8BBB92]">
                    <Sparkles className="w-3.5 h-3.5 text-[#8BBB92]" />
                    <span>Why This Phone Matches Your Preferences</span>
                  </div>
                  <p className="text-xs text-[#f2fbf6] leading-relaxed">
                    {item.explanation}
                  </p>
                </div>

                {/* Strengths & Weaknesses Badges */}
                <div className="pt-3 flex flex-wrap items-center gap-2">
                  {item.strengths?.map((str, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1"
                    >
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span>{str}</span>
                    </span>
                  ))}
                  {item.weaknesses?.map((wk, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-rose-500/15 text-rose-300 border border-rose-500/30 flex items-center space-x-1"
                    >
                      <X className="w-3 h-3 text-rose-400" />
                      <span>{wk}</span>
                    </span>
                  ))}

                  {/* Data limitations notice */}
                  {item.data_limitations?.map((lim, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-md text-[11px] text-amber-300/80 bg-amber-500/10 border border-amber-500/20"
                    >
                      ⚠️ {lim}
                    </span>
                  ))}
                </div>

                {/* Bottom Actions Bar */}
                <div className="pt-4 mt-4 border-t border-[#12544F]/30 flex flex-wrap items-center justify-between gap-3">
                  <button
                    onClick={() => handleInspectScores(item.product_id)}
                    className="text-xs text-[#8BBB92] hover:text-white font-medium flex items-center space-x-1 hover:underline transition-colors"
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    <span>Inspect Bayesian Breakdown</span>
                  </button>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => toggleComparisonProduct(item.product_id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                        isSelectedForCompare
                          ? 'bg-[#2A835F] text-white border border-[#8BBB92]'
                          : 'bg-[#030c0e] text-[#8BBB92] hover:text-white border border-[#12544F]/80 hover:border-[#2A835F]'
                      }`}
                    >
                      <Scale className="w-3.5 h-3.5" />
                      <span>{isSelectedForCompare ? 'Selected for Compare' : 'Add to Compare'}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Floating Side-by-Side Comparison Dock */}
      {comparisonIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[#071b1f]/95 border border-[#2A835F] rounded-2xl px-5 py-3 shadow-2xl backdrop-blur-xl flex items-center space-x-4 max-w-lg w-full">
          <div className="flex items-center space-x-2 text-xs font-bold text-white">
            <Scale className="w-4 h-4 text-[#8BBB92]" />
            <span>{comparisonIds.length} / 4 Selected</span>
          </div>

          <div className="flex-1 flex items-center justify-end space-x-2">
            <button
              onClick={() => setComparisonIds([])}
              className="text-xs text-[#7ea698] hover:text-white font-medium px-2 py-1"
            >
              Clear
            </button>
            <button
              onClick={handleRunComparison}
              disabled={comparisonIds.length < 2 || isComparing}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-[#12544F] via-[#2A835F] to-[#12544F] text-white border border-[#8BBB92]/60 shadow-lg shadow-[#2A835F]/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-40"
            >
              {isComparing ? 'Comparing...' : 'Compare Side-by-Side'}
            </button>
          </div>
        </div>
      )}

      {/* Side-by-Side Product Comparison Modal */}
      {isCompareModalOpen && comparisonData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#071b1f] border border-[#12544F] rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-[#12544F]/50 flex items-center justify-between bg-[#030c0e]">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-[#12544F]/60 text-[#8BBB92]">
                  <Scale className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Side-by-Side Smartphone Comparison</h3>
                  <p className="text-xs text-[#7ea698]">
                    Comparing {comparisonData.compared_products_count} smartphones across ABSA aspect scores and review evidence
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-[#12544F]/40 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Comparison Matrix Content */}
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Product Info Cards */}
              <div className={`grid grid-cols-1 md:grid-cols-${comparisonData.compared_products_count} gap-4`}>
                {comparisonData.products.map((p) => (
                  <div
                    key={p.product_id}
                    className="p-4 rounded-xl bg-[#030c0e] border border-[#12544F]/70 space-y-2 relative"
                  >
                    <span className="text-[11px] font-bold text-[#8BBB92] uppercase tracking-wider">
                      {p.brand}
                    </span>
                    <h4 className="text-sm font-bold text-white leading-tight">{p.product_name}</h4>
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-xs font-semibold text-emerald-400">
                        {p.price_usd ? `$${Math.round(p.price_usd)} USD` : 'Price N/A'}
                      </span>
                      <div className="flex items-baseline space-x-1">
                        <span className="text-xs text-[#649182]">Score:</span>
                        <span className={`text-sm font-black ${getScoreColor(p.overall_score)}`}>
                          {p.overall_score !== null ? p.overall_score : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Aspect Scores Comparison Table */}
              <div className="border border-[#12544F]/50 rounded-xl overflow-hidden bg-[#030c0e]/60">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#030c0e] border-b border-[#12544F]/60 text-[#8BBB92] font-bold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Aspect Category</th>
                      {comparisonData.products.map((p) => (
                        <th key={p.product_id} className="py-3 px-4">
                          {p.product_name}
                        </th>
                      ))}
                      <th className="py-3 px-4 text-center">Winner</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#12544F]/30">
                    {allAspects.map((asp) => {
                      const Icon = ASPECT_ICONS[asp] || Smartphone;
                      const winnerName = comparisonData.aspect_winners[asp];

                      return (
                        <tr key={asp} className="hover:bg-[#12544F]/10 transition-colors">
                          <td className="py-3 px-4 font-semibold text-white flex items-center space-x-2">
                            <Icon className="w-4 h-4 text-[#8BBB92]" />
                            <span>{asp}</span>
                          </td>
                          {comparisonData.products.map((p) => {
                            const aspScore = p.aspect_scores[asp];
                            const isWinner = winnerName && winnerName === p.product_name;

                            return (
                              <td key={p.product_id} className="py-3 px-4">
                                {aspScore && aspScore.is_available && aspScore.score !== null ? (
                                  <div className="space-y-1">
                                    <div className="flex items-center space-x-1.5">
                                      <span className={`font-bold ${getScoreColor(aspScore.score)}`}>
                                        {aspScore.score}/100
                                      </span>
                                      {isWinner && (
                                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                          BEST
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center space-x-2 text-[10px] text-[#649182]">
                                      <span>n={aspScore.evidence_count} reviews</span>
                                      <span className="text-emerald-400">+{aspScore.positive_count}</span>
                                      <span className="text-zinc-400">~{aspScore.neutral_count}</span>
                                      <span className="text-rose-400">-{aspScore.negative_count}</span>
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-zinc-600 italic">Unavailable</span>
                                )}
                              </td>
                            );
                          })}
                          <td className="py-3 px-4 text-center">
                            {winnerName ? (
                              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/40">
                                {winnerName}
                              </span>
                            ) : (
                              <span className="text-zinc-600">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Strengths & Weaknesses Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {comparisonData.products.map((p) => (
                  <div
                    key={p.product_id}
                    className="p-4 rounded-xl bg-[#030c0e] border border-[#12544F]/50 space-y-2.5"
                  >
                    <h5 className="text-xs font-bold text-white uppercase tracking-wider">
                      {p.product_name} Profile
                    </h5>
                    <div className="space-y-1.5">
                      <span className="text-[11px] text-emerald-400 font-semibold block">Strengths:</span>
                      <div className="flex flex-wrap gap-1">
                        {p.strengths?.length > 0 ? (
                          p.strengths.map((s, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                            >
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-[10px] text-zinc-500 italic">No standout strengths detected</span>
                        )}
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <span className="text-[11px] text-rose-400 font-semibold block">Weaknesses:</span>
                      <div className="flex flex-wrap gap-1">
                        {p.weaknesses?.length > 0 ? (
                          p.weaknesses.map((w, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-300 border border-rose-500/30"
                            >
                              {w}
                            </span>
                          ))
                        ) : (
                          <span className="text-[10px] text-zinc-500 italic">No standout weaknesses detected</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Product Bayesian Breakdown Inspector Modal */}
      {inspectProductId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#071b1f] border border-[#12544F] rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-[#12544F]/50 flex items-center justify-between bg-[#030c0e]">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5 text-[#8BBB92]" />
                <h3 className="text-sm font-bold text-white">
                  Academic Bayesian Credibility Breakdown
                </h3>
              </div>
              <button
                onClick={() => setInspectProductId(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-[#12544F]/40"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5">
              {isInspectLoading && (
                <div className="p-8 text-center text-xs text-[#7ea698]">Loading calculations...</div>
              )}

              {!isInspectLoading && inspectScoresData && (
                <>
                  <div className="p-4 rounded-xl bg-[#030c0e] border border-[#12544F]/60 space-y-1">
                    <span className="text-[11px] font-bold text-[#8BBB92] uppercase tracking-wider">
                      {inspectScoresData.brand}
                    </span>
                    <h4 className="text-base font-bold text-white">{inspectScoresData.product_name}</h4>
                    <p className="text-xs text-[#7ea698]">
                      Total Reviews: {inspectScoresData.total_reviews} • ABSA Predictions:{' '}
                      {inspectScoresData.total_predictions}
                    </p>
                  </div>

                  {/* Mathematical Formula Explanation */}
                  <div className="p-4 rounded-xl bg-[#12544F]/20 border border-[#2A835F]/40 space-y-2">
                    <span className="text-xs font-bold text-[#8BBB92] block">
                      Mathematical Formulation (Empirical Bayes):
                    </span>
                    <div className="font-mono text-[11px] text-emerald-200 bg-[#030c0e] p-2.5 rounded-lg border border-[#12544F]/50">
                      Score = [ (W_pos + 0.5 × W_neu) × 100 + m × μ_0 ] / (N_eff + m)
                    </div>
                    <p className="text-[11px] text-[#7ea698] leading-relaxed">
                      Where prior mean μ_0 = 50.0 (neutral baseline) and damping constant m = 3.0 effective reviews.
                      Verified human annotations receive 1.5× weight, while automated predictions are scaled by model confidence.
                    </p>
                  </div>

                  {/* Aspects breakdown table */}
                  <div className="space-y-3">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Aspect Detail Breakdown:
                    </span>
                    <div className="space-y-2">
                      {Object.entries(inspectScoresData.aspect_scores).map(([asp, item]) => (
                        <div
                          key={asp}
                          className="p-3 rounded-xl bg-[#030c0e] border border-[#12544F]/40 flex items-center justify-between text-xs"
                        >
                          <div>
                            <span className="font-bold text-white block">{asp}</span>
                            <span className="text-[10px] text-[#649182]">
                              Evidence Count: {item.evidence_count} reviews (Eff: {item.confidence_weighted_evidence})
                            </span>
                            <div className="flex items-center space-x-2 text-[10px] mt-0.5">
                              <span className="text-emerald-400 font-semibold">Pos: {item.positive_count}</span>
                              <span className="text-zinc-400 font-semibold">Neu: {item.neutral_count}</span>
                              <span className="text-rose-400 font-semibold">Neg: {item.negative_count}</span>
                            </div>
                          </div>

                          <div className="text-right">
                            <span className={`text-base font-black ${getScoreColor(item.score)}`}>
                              {item.score !== null ? `${item.score}/100` : 'Unavailable'}
                            </span>
                            <span className="text-[10px] text-[#649182] block">
                              Raw Ratio: {item.raw_sentiment_ratio !== null ? `${Math.round(item.raw_sentiment_ratio * 100)}%` : '—'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
