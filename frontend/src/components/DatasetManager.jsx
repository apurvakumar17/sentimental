import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Download, 
  FileText, 
  Filter, 
  Layers, 
  RefreshCw, 
  FileSpreadsheet, 
  Hash, 
  Check, 
  Info, 
  Copy, 
  Database,
  SlidersHorizontal,
  FileCode,
  Tag,
  Trash2
} from 'lucide-react';
import { api } from '../api/client';

export default function DatasetManager({ products, onOpenClearDbModal }) {
  // Filter & Selection States
  const [selectedProductId, setSelectedProductId] = useState('');
  
  // Quality Audit States
  const [qualitySummary, setQualitySummary] = useState(null);
  const [isQualityLoading, setIsQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState(null);

  // Preparation & Filter Options
  const [minRating, setMinRating] = useState('');
  const [maxRating, setMaxRating] = useState('');
  const [excludeErrors, setExcludeErrors] = useState(true);
  const [excludeExactDuplicates, setExcludeExactDuplicates] = useState(true);
  const [excludePotentialDuplicates, setExcludePotentialDuplicates] = useState(false);
  const [exportFormat, setExportFormat] = useState('csv');
  const [includeUnannotatedColumns, setIncludeUnannotatedColumns] = useState(true);

  // Preview States
  const [previewRecords, setPreviewRecords] = useState([]);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewLimit, setPreviewLimit] = useState(5);

  // Export Trigger & Manifest States
  const [isExporting, setIsExporting] = useState(false);
  const [latestManifest, setLatestManifest] = useState(null);
  const [manifests, setManifests] = useState([]);
  const [isManifestsLoading, setIsManifestsLoading] = useState(false);
  const [copiedChecksum, setCopiedChecksum] = useState(null);

  // Fetch Quality Summary
  const fetchQuality = async () => {
    setIsQualityLoading(true);
    setQualityError(null);
    try {
      const summary = await api.getDatasetQuality({
        productId: selectedProductId || undefined,
      });
      setQualitySummary(summary);
    } catch (err) {
      console.error('Failed to evaluate dataset quality:', err);
      setQualityError(err.message || 'Quality assessment failed.');
    } finally {
      setIsQualityLoading(false);
    }
  };

  // Fetch Preview Records
  const fetchPreview = async () => {
    setIsPreviewLoading(true);
    try {
      const filters = {
        product_id: selectedProductId ? parseInt(selectedProductId, 10) : undefined,
        min_rating: minRating !== '' ? parseFloat(minRating) : undefined,
        max_rating: maxRating !== '' ? parseFloat(maxRating) : undefined,
        exclude_errors: excludeErrors,
        exclude_exact_duplicates: excludeExactDuplicates,
        exclude_potential_duplicates: excludePotentialDuplicates,
      };
      const previewData = await api.previewDataset(filters, previewLimit, 0);
      setPreviewRecords(previewData.records || []);
    } catch (err) {
      console.error('Failed to preview dataset:', err);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  // Fetch Export Manifests
  const fetchManifests = async () => {
    setIsManifestsLoading(true);
    try {
      const res = await api.getDatasetExports();
      setManifests(res.manifests || []);
    } catch (err) {
      console.error('Failed to fetch manifests:', err);
    } finally {
      setIsManifestsLoading(false);
    }
  };

  // Trigger File Export
  const handleExport = async () => {
    setIsExporting(true);
    try {
      const exportReq = {
        format: exportFormat,
        filters: {
          product_id: selectedProductId ? parseInt(selectedProductId, 10) : undefined,
          min_rating: minRating !== '' ? parseFloat(minRating) : undefined,
          max_rating: maxRating !== '' ? parseFloat(maxRating) : undefined,
          exclude_errors: excludeErrors,
          exclude_exact_duplicates: excludeExactDuplicates,
          exclude_potential_duplicates: excludePotentialDuplicates,
        },
        include_unannotated_columns: includeUnannotatedColumns,
      };
      const manifest = await api.exportDataset(exportReq);
      setLatestManifest(manifest);
      fetchManifests();
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Initial and reactive loads
  useEffect(() => {
    fetchQuality();
    fetchPreview();
  }, [
    selectedProductId, 
    minRating, 
    maxRating, 
    excludeErrors, 
    excludeExactDuplicates, 
    excludePotentialDuplicates,
    previewLimit
  ]);

  useEffect(() => {
    fetchManifests();
  }, []);

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedChecksum(key);
    setTimeout(() => setCopiedChecksum(null), 2000);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-start sm:items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-[#12544F]/50 border border-[#2A835F]/60 flex items-center justify-center text-[#8BBB92] shrink-0 mt-0.5 sm:mt-0">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight flex flex-wrap items-center gap-2">
                  <span>Dataset Preparation & Data Quality Pipeline</span>
                  <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#12544F]/80 text-[#8BBB92] border border-[#2A835F]/50 shrink-0">
                    Phase 2
                  </span>
                </h1>
                <p className="text-xs text-[#7ea698] mt-0.5">
                  Safe Unicode NFKC preprocessing, multi-rule data health auditing, and deterministic export generation for ABSA.
                </p>
              </div>
            </div>
          </div>

          {/* Product Filter & Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 xl:shrink-0">
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] w-full sm:w-auto sm:max-w-[220px] truncate"
            >
              <option value="">All Products (Entire Corpus)</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.brand ? `${p.brand} ` : ''}{p.name} ({p.review_count} reviews)
                </option>
              ))}
            </select>

            <button
              onClick={fetchQuality}
              disabled={isQualityLoading}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-[#12544F]/50 hover:bg-[#12544F] border border-[#2A835F]/60 text-xs font-semibold text-[#8BBB92] hover:text-white transition-all disabled:opacity-50 shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isQualityLoading ? 'animate-spin' : ''}`} />
              <span>Audit Quality</span>
            </button>

            {onOpenClearDbModal && (
              <button
                type="button"
                onClick={onOpenClearDbModal}
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-rose-950/40 hover:bg-rose-950/80 border border-rose-900/60 hover:border-rose-700/70 text-xs font-semibold text-rose-300 hover:text-white transition-all shrink-0"
                title="Permanently clear all reviews, products, and jobs"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                <span>Clear Database</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Section 1: Quality Assessment Summary */}
      {qualityError && (
        <div className="rounded-xl border border-red-500/40 bg-red-950/20 p-4 text-xs text-red-300">
          <p className="font-semibold">Quality Assessment Error:</p>
          <p>{qualityError}</p>
        </div>
      )}

      {qualitySummary && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Quality Score Hero Card */}
          <div className="lg:col-span-4 rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-5 backdrop-blur-xl shadow-2xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs text-[#7ea698]">
                <span className="font-semibold uppercase tracking-wider">Dataset Health Score</span>
                <span className="text-[11px] text-[#8BBB92] font-mono">0 - 100 Scale</span>
              </div>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="text-5xl font-black tracking-tight text-white">
                  {qualitySummary.quality_score}
                </span>
                <span className="text-xl font-bold text-[#8BBB92]">/ 100</span>
              </div>

              {/* Score Bar */}
              <div className="mt-3 w-full bg-[#030c0e] rounded-full h-2.5 overflow-hidden border border-[#12544F]/40">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    qualitySummary.quality_score >= 80 
                      ? 'bg-gradient-to-r from-[#2A835F] to-[#8BBB92]' 
                      : qualitySummary.quality_score >= 50 
                      ? 'bg-amber-500' 
                      : 'bg-rose-500'
                  }`}
                  style={{ width: `${qualitySummary.quality_score}%` }}
                />
              </div>

              <p className="mt-3 text-[11px] text-[#649182] leading-relaxed">
                Formula: Penalizes fatal errors (1.0x), warnings (0.15x), and duplicate records (0.25x) relative to total volume.
              </p>
            </div>

            <div className="mt-5 pt-4 border-t border-[#12544F]/30 grid grid-cols-2 gap-3 text-xs">
              <div className="bg-[#030c0e]/60 rounded-xl p-2.5 border border-[#12544F]/40">
                <span className="text-[#649182] text-[10px] block uppercase font-medium">Valid Records</span>
                <span className="text-base font-bold text-[#8BBB92] font-mono">
                  {qualitySummary.valid_reviews}
                </span>
                <span className="text-[10px] text-[#649182]"> ({qualitySummary.total_reviews ? Math.round((qualitySummary.valid_reviews / qualitySummary.total_reviews) * 100) : 0}%)</span>
              </div>
              <div className="bg-[#030c0e]/60 rounded-xl p-2.5 border border-[#12544F]/40">
                <span className="text-[#649182] text-[10px] block uppercase font-medium">Clean (No Warnings)</span>
                <span className="text-base font-bold text-white font-mono">
                  {qualitySummary.clean_reviews}
                </span>
                <span className="text-[10px] text-[#649182]"> ({qualitySummary.total_reviews ? Math.round((qualitySummary.clean_reviews / qualitySummary.total_reviews) * 100) : 0}%)</span>
              </div>
            </div>
          </div>

          {/* Breakdown Tiles */}
          <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Tile 1: Fatal Errors */}
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-4 backdrop-blur-xl shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-400 uppercase tracking-wide flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Fatal Errors
                  </span>
                  <span className="text-sm font-mono font-bold text-rose-400">
                    {qualitySummary.reviews_with_errors}
                  </span>
                </div>
                <p className="text-[11px] text-[#649182] mt-1">Unusable without curation.</p>

                <div className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Missing/Empty Text:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.missing_text_count}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Normalization Empty:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.normalization_empty_count}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Invalid Rating (&lt;0 or &gt;5):</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.invalid_rating_count}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#7ea698]">Missing Product Link:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.missing_product_count}</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 text-[10px] text-[#8BBB92] bg-[#12544F]/20 rounded-lg p-2 border border-[#12544F]/30">
                Safe behavior: Excluded from exports without DB deletion.
              </div>
            </div>

            {/* Tile 2: Warnings & Metadata */}
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-4 backdrop-blur-xl shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5" />
                    Review Warnings
                  </span>
                  <span className="text-sm font-mono font-bold text-amber-400">
                    {qualitySummary.reviews_with_warnings}
                  </span>
                </div>
                <p className="text-[11px] text-[#649182] mt-1">Non-fatal statistical anomalies.</p>

                <div className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Excessively Short (&lt;10c):</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.excessively_short_count}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Excessively Long (&gt;5kc):</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.excessively_long_count}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Missing Date:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.missing_date_count}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#7ea698]">Unrecorded Author:</span>
                    <span className="font-mono text-white font-medium">
                      {qualitySummary.sample_issues.filter(i => i.issue_type === 'missing_author').length}
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-3 text-[10px] text-[#7ea698] bg-[#030c0e]/50 rounded-lg p-2 border border-[#12544F]/20">
                Preserved for rich qualitative aspect mining.
              </div>
            </div>

            {/* Tile 3: Deduplication Breakdown */}
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-4 backdrop-blur-xl shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#8BBB92] uppercase tracking-wide flex items-center gap-1.5">
                    <Copy className="w-3.5 h-3.5" />
                    Duplicates Audited
                  </span>
                  <span className="text-sm font-mono font-bold text-[#8BBB92]">
                    {qualitySummary.exact_duplicate_count + qualitySummary.potential_duplicate_count}
                  </span>
                </div>
                <p className="text-[11px] text-[#649182] mt-1">Multi-tier collision check.</p>

                <div className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Exact Content Hashes:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.exact_duplicate_count}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#12544F]/20">
                    <span className="text-[#7ea698]">Potential Text Match:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.potential_duplicate_count}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#7ea698]">Total Examined:</span>
                    <span className="font-mono text-white font-medium">{qualitySummary.total_reviews}</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 text-[10px] text-[#8BBB92] bg-[#12544F]/20 rounded-lg p-2 border border-[#12544F]/30">
                Zero data loss: Original DB records intact.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Dataset Export & Pipeline Controls */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#12544F]/40 pb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Download className="w-4 h-4 text-[#8BBB92]" />
              Deterministic Dataset Exporter
            </h2>
            <p className="text-xs text-[#7ea698]">
              Configure filters, choose output format, and package reproducible NLP corpora with cryptographic fingerprints.
            </p>
          </div>

          {/* Format Radio Selection */}
          <div className="flex items-center bg-[#030c0e] rounded-xl p-1 border border-[#12544F]/70">
            <button
              onClick={() => setExportFormat('csv')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                exportFormat === 'csv'
                  ? 'bg-[#12544F] text-[#8BBB92] border border-[#2A835F]/60 shadow-sm'
                  : 'text-[#649182] hover:text-white'
              }`}
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              CSV Spreadsheet
            </button>
            <button
              onClick={() => setExportFormat('jsonl')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                exportFormat === 'jsonl'
                  ? 'bg-[#12544F] text-[#8BBB92] border border-[#2A835F]/60 shadow-sm'
                  : 'text-[#649182] hover:text-white'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              JSONL Stream
            </button>
          </div>
        </div>

        {/* Filter and Configuration Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Rating Range */}
          <div className="space-y-3">
            <label className="text-xs font-semibold text-white block">Rating Filtering</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-[10px] text-[#649182] block mb-1">Min Rating (0-5)</span>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.5"
                  placeholder="e.g. 3.0"
                  value={minRating}
                  onChange={(e) => setMinRating(e.target.value)}
                  className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F]"
                />
              </div>
              <div>
                <span className="text-[10px] text-[#649182] block mb-1">Max Rating (0-5)</span>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.5"
                  placeholder="e.g. 5.0"
                  value={maxRating}
                  onChange={(e) => setMaxRating(e.target.value)}
                  className="w-full bg-[#030c0e] border border-[#12544F]/70 rounded-xl px-3 py-2 text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F]"
                />
              </div>
            </div>
          </div>

          {/* Quality Exclusions */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-white block">Quality Exclusions</label>
            <label className="flex items-center space-x-2 text-xs text-[#7ea698] cursor-pointer">
              <input
                type="checkbox"
                checked={excludeErrors}
                onChange={(e) => setExcludeErrors(e.target.checked)}
                className="rounded border-[#12544F] text-[#2A835F] focus:ring-[#2A835F] bg-[#030c0e]"
              />
              <span>Exclude records with fatal errors (blank text, etc.)</span>
            </label>
            <label className="flex items-center space-x-2 text-xs text-[#7ea698] cursor-pointer">
              <input
                type="checkbox"
                checked={excludeExactDuplicates}
                onChange={(e) => setExcludeExactDuplicates(e.target.checked)}
                className="rounded border-[#12544F] text-[#2A835F] focus:ring-[#2A835F] bg-[#030c0e]"
              />
              <span>Exclude exact content duplicates</span>
            </label>
            <label className="flex items-center space-x-2 text-xs text-[#7ea698] cursor-pointer">
              <input
                type="checkbox"
                checked={excludePotentialDuplicates}
                onChange={(e) => setExcludePotentialDuplicates(e.target.checked)}
                className="rounded border-[#12544F] text-[#2A835F] focus:ring-[#2A835F] bg-[#030c0e]"
              />
              <span>Exclude potential duplicates (identical normalized text)</span>
            </label>
          </div>

          {/* Annotation Scaffolding & Action */}
          <div className="space-y-3 flex flex-col justify-between">
            <div>
              <label className="text-xs font-semibold text-white block">ABSA Annotation Scaffolding</label>
              <label className="flex items-center space-x-2 text-xs text-[#7ea698] cursor-pointer mt-2">
                <input
                  type="checkbox"
                  checked={includeUnannotatedColumns}
                  onChange={(e) => setIncludeUnannotatedColumns(e.target.checked)}
                  className="rounded border-[#12544F] text-[#2A835F] focus:ring-[#2A835F] bg-[#030c0e]"
                />
                <span>Include empty aspect/sentiment annotation columns</span>
              </label>
              <p className="text-[10px] text-[#649182] mt-1">
                Adds <code>aspect_labels</code>, <code>sentiment_labels</code>, <code>annotation_status: UNANNOTATED</code>.
              </p>
            </div>

            <button
              onClick={handleExport}
              disabled={isExporting}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#12544F] to-[#2A835F] hover:from-[#1b736c] hover:to-[#37a478] border border-[#8BBB92]/30 text-xs font-bold text-white shadow-lg shadow-[#2A835F]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
            >
              <Download className={`w-4 h-4 ${isExporting ? 'animate-bounce' : ''}`} />
              <span>{isExporting ? 'Generating Dataset...' : `Export ${exportFormat.toUpperCase()} Dataset`}</span>
            </button>
          </div>
        </div>

        {/* Latest Export Result Card */}
        {latestManifest && (
          <div className="rounded-xl border border-[#2A835F]/70 bg-[#12544F]/30 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-2.5">
                <CheckCircle2 className="w-5 h-5 text-[#8BBB92] shrink-0" />
                <div>
                  <h3 className="text-xs font-bold text-white font-mono">{latestManifest.filename}</h3>
                  <p className="text-[11px] text-[#8BBB92]">
                    Exported {latestManifest.total_exported_records} records ({latestManifest.total_source_examined} examined, {latestManifest.excluded_records} excluded).
                  </p>
                </div>
              </div>

              <a
                href={api.getDownloadUrl(latestManifest.filename)}
                download
                className="px-4 py-2 rounded-xl bg-[#2A835F] hover:bg-[#349e73] text-xs font-bold text-white flex items-center justify-center space-x-2 shadow-md transition-all shrink-0"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download File</span>
              </a>
            </div>

            {/* Checksum & Metadata */}
            <div className="bg-[#030c0e]/80 rounded-lg p-2.5 border border-[#12544F]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px]">
              <div className="flex items-center space-x-2 overflow-hidden">
                <Hash className="w-3.5 h-3.5 text-[#649182] shrink-0" />
                <span className="text-[#649182]">SHA-256:</span>
                <span className="font-mono text-[#8BBB92] truncate">{latestManifest.sha256_checksum}</span>
              </div>
              <button
                onClick={() => copyToClipboard(latestManifest.sha256_checksum, 'latest')}
                className="text-[10px] text-[#8BBB92] hover:text-white flex items-center space-x-1 shrink-0"
              >
                {copiedChecksum === 'latest' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span>{copiedChecksum === 'latest' ? 'Copied' : 'Copy Hash'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Dual-View Dataset Live Preview */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#8BBB92]" />
              Dataset Preprocessing Preview
            </h2>
            <p className="text-xs text-[#7ea698]">
              Verify side-by-side preservation of immutable raw text versus clean Unicode NFKC normalized text.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#649182]">Sample size:</span>
            <select
              value={previewLimit}
              onChange={(e) => setPreviewLimit(parseInt(e.target.value, 10))}
              className="bg-[#030c0e] border border-[#12544F]/70 rounded-lg px-2.5 py-1 text-xs text-[#f2fbf6] focus:outline-none"
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </div>
        </div>

        {isPreviewLoading ? (
          <div className="py-12 text-center text-xs text-[#649182] flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-[#8BBB92]" />
            <span>Generating live preprocessing preview...</span>
          </div>
        ) : previewRecords.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#649182] border border-[#12544F]/30 rounded-xl bg-[#030c0e]/40">
            No reviews match the specified criteria or no reviews are present in the warehouse.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-[#12544F]/30 rounded-xl overflow-hidden">
              <thead className="bg-[#030c0e] text-[#8BBB92] border-b border-[#12544F]/60">
                <tr>
                  <th className="py-2.5 px-3 font-semibold w-16">ID</th>
                  <th className="py-2.5 px-3 font-semibold w-40">Device</th>
                  <th className="py-2.5 px-3 font-semibold">Raw Review Text (Immutable)</th>
                  <th className="py-2.5 px-3 font-semibold">Normalized Text (Clean NFKC)</th>
                  <th className="py-2.5 px-3 font-semibold w-24 text-center">Stats</th>
                  <th className="py-2.5 px-3 font-semibold w-24 text-center">Status</th>
                  <th className="py-2.5 px-3 font-semibold w-28 text-center">Annotation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#12544F]/20 bg-[#071b1f]/60">
                {previewRecords.map((rec) => (
                  <tr key={rec.review_id} className="hover:bg-[#12544F]/20 transition-colors">
                    <td className="py-3 px-3 font-mono text-[#649182] font-semibold">
                      #{rec.review_id}
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-semibold text-white block truncate max-w-[150px]">{rec.product_name}</span>
                      <span className="text-[10px] text-[#649182]">{rec.brand || '—'} · {rec.source}</span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="max-h-20 overflow-y-auto font-mono text-[11px] text-[#f2fbf6] bg-[#030c0e]/80 p-2 rounded-lg border border-[#12544F]/30 whitespace-pre-wrap">
                        {rec.raw_review_text}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="max-h-20 overflow-y-auto font-mono text-[11px] text-[#8BBB92] bg-[#030c0e]/80 p-2 rounded-lg border border-[#2A835F]/30 whitespace-pre-wrap">
                        {rec.normalized_review_text}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className="font-mono text-[11px] text-[#7ea698] block">{rec.word_count} w</span>
                      <span className="font-mono text-[10px] text-[#649182] block">{rec.char_count} c</span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        rec.quality_status === 'clean' 
                          ? 'bg-[#12544F]/80 text-[#8BBB92] border border-[#2A835F]/60' 
                          : rec.quality_status === 'warning'
                          ? 'bg-amber-950/40 text-amber-300 border border-amber-500/40'
                          : 'bg-rose-950/40 text-rose-300 border border-rose-500/40'
                      }`}>
                        {rec.quality_status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-[#030c0e] text-[#649182] border border-[#12544F]/50">
                        {rec.annotation_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 4: Export History & Manifest Repository */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-[#8BBB92]" />
              Export Manifest History
            </h2>
            <p className="text-xs text-[#7ea698]">
              Cryptographically verified datasets generated in <code>data/exports</code> ready for ABSA annotation.
            </p>
          </div>

          <button
            onClick={fetchManifests}
            disabled={isManifestsLoading}
            className="p-1.5 rounded-lg text-[#8BBB92] hover:bg-[#12544F]/50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isManifestsLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {manifests.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#649182] border border-[#12544F]/30 rounded-xl bg-[#030c0e]/30">
            No exported datasets generated yet. Use the exporter above to produce an NLP-ready corpus.
          </div>
        ) : (
          <div className="space-y-2.5">
            {manifests.map((m) => (
              <div
                key={m.filename}
                className="rounded-xl border border-[#12544F]/40 bg-[#030c0e]/60 p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-[#2A835F]/60 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-white">{m.filename}</span>
                    <span className="uppercase text-[10px] font-semibold px-2 py-0.5 rounded bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/40">
                      {m.format}
                    </span>
                    <span className="text-[11px] text-[#649182]">
                      ({m.total_exported_records} records)
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[#649182]">
                    <span>Created: {new Date(m.created_at).toLocaleString()}</span>
                    <span>Schema: {m.dataset_schema_version}</span>
                    <span className="font-mono text-[10px] truncate max-w-xs">SHA: {m.sha256_checksum.slice(0, 16)}...</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => copyToClipboard(m.sha256_checksum, m.filename)}
                    className="p-2 rounded-lg bg-[#12544F]/30 hover:bg-[#12544F]/60 text-[#8BBB92] text-xs transition-colors"
                    title="Copy SHA-256 Checksum"
                  >
                    {copiedChecksum === m.filename ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <a
                    href={api.getDownloadUrl(m.filename)}
                    download
                    className="px-3 py-1.5 rounded-lg bg-[#12544F]/60 hover:bg-[#2A835F] text-[#8BBB92] hover:text-white border border-[#2A835F]/50 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 5: Database Maintenance & Reset */}
      {onOpenClearDbModal && (
        <div className="rounded-2xl border border-rose-950/60 bg-[#071b1f]/80 p-5 backdrop-blur-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-900/60 text-rose-400">
                <Trash2 className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Database Maintenance & Full Reset</h4>
                <p className="text-xs text-[#7ea698]">
                  Permanently wipe all collected reviews, catalog products, and scraper/import jobs to start fresh.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onOpenClearDbModal}
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-rose-950/50 hover:bg-rose-950 border border-rose-900/70 hover:border-rose-600 text-xs font-semibold text-rose-300 hover:text-white transition-all shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
              <span>Clear Full Database</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
