import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Layers,
  ArrowRight,
  ShieldCheck,
  Eye,
  FileCheck,
  XCircle,
  Clock,
  Database,
  ChevronLeft,
  ChevronRight,
  Info
} from 'lucide-react';
import { api } from '../api/client';

export default function DatasetImporter({ onImportCompleted }) {
  // File upload state
  const [file, setFile] = useState(null);
  const [fileSizeFormatted, setFileSizeFormatted] = useState('');
  const fileInputRef = useRef(null);

  // Preview & Validation state
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewError, setPreviewError] = useState(null);

  // Import Job Execution state
  const [isStartingImport, setIsStartingImport] = useState(false);
  const [activeJob, setActiveJob] = useState(null);
  const [importJobs, setImportJobs] = useState([]);
  const [isJobsLoading, setIsJobsLoading] = useState(false);

  const isImportInProgress = isStartingImport || Boolean(activeJob && (activeJob.status === 'PENDING' || activeJob.status === 'PROCESSING'));

  // Paginated Job Errors modal state
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorModalJobId, setErrorModalJobId] = useState(null);
  const [jobErrors, setJobErrors] = useState([]);
  const [errorPage, setErrorPage] = useState(1);
  const [totalErrors, setTotalErrors] = useState(0);
  const [isErrorsLoading, setIsErrorsLoading] = useState(false);

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setFileSizeFormatted(formatBytes(selected.size));
      setPreviewData(null);
      setPreviewError(null);
    }
  };

  const handlePreview = async () => {
    if (!file) return;
    setIsPreviewLoading(true);
    setPreviewError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.previewImport(formData);
      setPreviewData(res);
    } catch (err) {
      console.error('Preview error:', err);
      setPreviewError(err.message || 'Failed to inspect CSV file.');
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleStartImport = async () => {
    if (!file) return;
    setIsStartingImport(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const newJob = await api.startImport(formData);
      setActiveJob(newJob);
      loadJobs();
    } catch (err) {
      alert(`Import failed to start: ${err.message}`);
    } finally {
      setIsStartingImport(false);
    }
  };

  const loadJobs = async () => {
    setIsJobsLoading(true);
    try {
      const res = await api.getImportJobs(15);
      const items = res.items || [];
      setImportJobs(items);
      // If active job not set or running, auto-select latest
      if (!activeJob && items.length > 0) {
        setActiveJob(items[0]);
      }
    } catch (err) {
      console.error('Failed to load import jobs:', err);
    } finally {
      setIsJobsLoading(false);
    }
  };

  // Poll active job while PENDING or PROCESSING
  useEffect(() => {
    if (!activeJob) return;
    if (activeJob.status !== 'PENDING' && activeJob.status !== 'PROCESSING') return;

    const interval = setInterval(async () => {
      try {
        const updated = await api.getImportJob(activeJob.job_id);
        setActiveJob(updated);
        if (updated.status === 'COMPLETED' || updated.status === 'FAILED') {
          loadJobs();
          if (onImportCompleted) {
            onImportCompleted();
          }
        }
      } catch (err) {
        console.error('Error polling import job:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob?.job_id, activeJob?.status]);

  useEffect(() => {
    loadJobs();
  }, []);

  const openErrorModal = async (jobId) => {
    setErrorModalJobId(jobId);
    setErrorPage(1);
    setShowErrorModal(true);
    fetchJobErrors(jobId, 1);
  };

  const fetchJobErrors = async (jobId, page) => {
    setIsErrorsLoading(true);
    try {
      const res = await api.getImportJobErrors(jobId, page, 15);
      setJobErrors(res.errors || []);
      setTotalErrors(res.total_errors || 0);
      setErrorPage(page);
    } catch (err) {
      console.error('Failed to load job errors:', err);
    } finally {
      setIsErrorsLoading(false);
    }
  };

  const progressPercent = activeJob?.total_rows && activeJob.total_rows > 0
    ? Math.min(100, Math.round((activeJob.rows_processed / activeJob.total_rows) * 100))
    : activeJob?.status === 'COMPLETED' ? 100 : 0;

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-[#12544F]/50 border border-[#2A835F]/60 flex items-center justify-center text-[#8BBB92]">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Kaggle Dataset Import Engine
                <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded-full bg-[#12544F]/80 text-[#8BBB92] border border-[#2A835F]/50">
                  50,000 Rows Ready
                </span>
              </h1>
              <p className="text-xs text-[#7ea698] mt-0.5">
                Upload local 25-column smartphone review CSV files. Safe UTF-8/BOM parsing, 3-tier deduplication, and periodic transactional ingestion.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <span className="px-2.5 py-1 rounded-lg bg-[#030c0e] border border-[#12544F]/50 text-[#8BBB92]">
              25 Canonical Fields
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-[#030c0e] border border-[#12544F]/50 text-[#8BBB92]">
              Tier-3 SHA256 Guard
            </span>
          </div>
        </div>
      </div>

      {/* Section 1: File Upload & Validation Controller */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-[#8BBB92]" />
            Select Local Kaggle CSV File
          </h2>
          <p className="text-xs text-[#7ea698]">
            Supports the standard 25-column Mobile Reviews Sentiment dataset downloaded from Kaggle.
          </p>
        </div>

        {/* Dropzone Container */}
        <div
          onClick={() => !isImportInProgress && fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all duration-200 ${
            isImportInProgress
              ? 'opacity-70 cursor-not-allowed border-[#12544F]/50 bg-[#030c0e]/30'
              : file
              ? 'border-[#2A835F] bg-[#12544F]/20 cursor-pointer'
              : 'border-[#12544F]/70 bg-[#030c0e]/50 hover:border-[#2A835F]/70 hover:bg-[#12544F]/10 cursor-pointer'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv"
            className="hidden"
          />

          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-[#12544F]/40 border border-[#2A835F]/50 flex items-center justify-center text-[#8BBB92]">
              <UploadCloud className="w-6 h-6" />
            </div>

            {file ? (
              <div className="space-y-1">
                <p className="text-sm font-bold text-white font-mono">{file.name}</p>
                <p className="text-xs text-[#8BBB92]">File Size: {fileSizeFormatted}</p>
                <p className="text-[11px] text-[#649182]">Click to select a different file</p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-white">Click or drag & drop Kaggle review CSV file here</p>
                <p className="text-xs text-[#649182]">Accepted format: .csv (UTF-8, up to 100MB)</p>
              </div>
            )}
          </div>
        </div>

        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-[#12544F]/40">
          <div className="text-xs text-[#649182]">
            <span>Expected Schema: </span>
            <code className="text-[#8BBB92] text-[11px] bg-[#030c0e] px-1.5 py-0.5 rounded">
              review_id, customer_name, brand, model, price_usd, rating, review_text, sentiment, source...
            </code>
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <button
              onClick={handlePreview}
              disabled={!file || isPreviewLoading || isImportInProgress}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-[#12544F]/60 hover:bg-[#12544F] border border-[#2A835F]/60 text-xs font-semibold text-[#8BBB92] hover:text-white flex items-center justify-center space-x-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Eye className={`w-3.5 h-3.5 ${isPreviewLoading ? 'animate-spin' : ''}`} />
              <span>{isPreviewLoading ? 'Inspecting CSV...' : 'Validate & Preview'}</span>
            </button>

            <button
              onClick={handleStartImport}
              disabled={!file || isImportInProgress || (previewData && !previewData.is_schema_valid)}
              className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#12544F] to-[#2A835F] hover:from-[#1b736c] hover:to-[#37a478] border border-[#8BBB92]/30 text-xs font-bold text-white shadow-lg shadow-[#2A835F]/20 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isImportInProgress ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#8BBB92]" />
                  <span>
                    {isStartingImport
                      ? 'Starting Import...'
                      : activeJob?.total_rows
                      ? `Importing (${Math.min(100, Math.round(((activeJob.rows_processed || 0) / activeJob.total_rows) * 100))}%)...`
                      : 'Processing Import...'}
                  </span>
                </>
              ) : (
                <>
                  <FileCheck className="w-3.5 h-3.5" />
                  <span>Start Batch Import</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Validation Preview Report */}
      {previewError && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-4 text-xs text-rose-300">
          <p className="font-semibold">Validation Error:</p>
          <p>{previewError}</p>
        </div>
      )}

      {previewData && (
        <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#12544F]/40 pb-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#8BBB92]" />
                CSV Schema Validation Results
              </h2>
              <p className="text-xs text-[#7ea698]">
                Verified header conformance and preview sample without database insertion.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              {previewData.is_schema_valid ? (
                <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#12544F]/80 text-[#8BBB92] border border-[#2A835F]/60">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#8BBB92]" />
                  <span>Schema Conforming (25/25 Columns)</span>
                </span>
              ) : (
                <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-500/60">
                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>Missing {previewData.missing_columns.length} Required Columns</span>
                </span>
              )}
            </div>
          </div>

          {/* Metrics summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Scanned Rows</span>
              <span className="text-lg font-bold text-white font-mono">{previewData.total_rows_scanned}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Valid Sample Rows</span>
              <span className="text-lg font-bold text-[#8BBB92] font-mono">{previewData.valid_row_count}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Rows with Warnings</span>
              <span className="text-lg font-bold text-amber-400 font-mono">{previewData.warning_row_count}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Rejected Sample Rows</span>
              <span className="text-lg font-bold text-rose-400 font-mono">{previewData.rejected_row_count}</span>
            </div>
          </div>

          {/* Missing columns alert if any */}
          {previewData.missing_columns.length > 0 && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-3.5 text-xs text-rose-300">
              <p className="font-semibold">Missing Required Columns:</p>
              <p className="font-mono mt-1">{previewData.missing_columns.join(', ')}</p>
            </div>
          )}

          {/* Sample Rows Table */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Sample Records Preview (Live Parse)</h3>
            <div className="overflow-x-auto border border-[#12544F]/40 rounded-xl">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#030c0e] text-[#8BBB92] border-b border-[#12544F]/60">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Row</th>
                    <th className="py-2.5 px-3 font-semibold">ID</th>
                    <th className="py-2.5 px-3 font-semibold">Model</th>
                    <th className="py-2.5 px-3 font-semibold">Brand</th>
                    <th className="py-2.5 px-3 font-semibold">Source</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Rating</th>
                    <th className="py-2.5 px-3 font-semibold">Sentiment</th>
                    <th className="py-2.5 px-3 font-semibold">Review Snippet</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#12544F]/20 bg-[#071b1f]/60">
                  {previewData.sample_rows.map((row) => (
                    <tr key={row.csv_row} className="hover:bg-[#12544F]/20 transition-colors">
                      <td className="py-2.5 px-3 font-mono text-[#649182]">#{row.csv_row}</td>
                      <td className="py-2.5 px-3 font-mono text-[#8BBB92] font-semibold">{row.review_id}</td>
                      <td className="py-2.5 px-3 font-semibold text-white">{row.model}</td>
                      <td className="py-2.5 px-3 text-[#7ea698]">{row.brand}</td>
                      <td className="py-2.5 px-3 text-[#7ea698]">{row.source}</td>
                      <td className="py-2.5 px-3 text-center font-mono text-amber-400 font-bold">{row.rating ?? '—'}</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#12544F]/40 text-[#8BBB92]">
                          {row.sentiment || '—'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[#f2fbf6] max-w-xs truncate">{row.review_text}</td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          row.status === 'valid'
                            ? 'bg-[#12544F]/80 text-[#8BBB92]'
                            : row.status === 'warning'
                            ? 'bg-amber-950/60 text-amber-300'
                            : 'bg-rose-950/60 text-rose-300'
                        }`}>
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Section 3: Active Job Progress Tracker */}
      {activeJob && (
        <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#12544F]/40 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-bold text-white">Import Job:</span>
                <span className="font-mono text-xs text-[#8BBB92] bg-[#030c0e] px-2 py-0.5 rounded border border-[#12544F]/60">
                  {activeJob.job_id}
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                  activeJob.status === 'COMPLETED'
                    ? 'bg-[#12544F] text-[#8BBB92] border border-[#2A835F]'
                    : activeJob.status === 'PROCESSING'
                    ? 'bg-amber-950/60 text-amber-300 border border-amber-500/60 animate-pulse'
                    : activeJob.status === 'FAILED'
                    ? 'bg-rose-950/60 text-rose-300 border border-rose-500/60'
                    : 'bg-[#030c0e] text-[#649182] border border-[#12544F]/40'
                }`}>
                  {activeJob.status}
                </span>
              </div>
              <p className="text-xs text-[#7ea698] mt-1">
                Source File: <span className="font-mono text-white">{activeJob.original_filename}</span>
              </p>
            </div>

            {activeJob.rejected_rows > 0 && (
              <button
                onClick={() => openErrorModal(activeJob.job_id)}
                className="px-3 py-1.5 rounded-xl bg-rose-950/40 hover:bg-rose-950/80 border border-rose-500/40 text-xs font-semibold text-rose-300 transition-colors"
              >
                Inspect {activeJob.rejected_rows} Rejections
              </button>
            )}
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-[#7ea698]">
              <span>Ingestion Progress</span>
              <span className="font-mono font-bold text-white">{progressPercent}%</span>
            </div>
            <div className="w-full bg-[#030c0e] rounded-full h-3 overflow-hidden border border-[#12544F]/50">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  activeJob.status === 'COMPLETED'
                    ? 'bg-gradient-to-r from-[#2A835F] to-[#8BBB92]'
                    : activeJob.status === 'FAILED'
                    ? 'bg-rose-600'
                    : 'bg-[#2A835F]'
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Live Metric Counters */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Processed</span>
              <span className="text-base font-bold text-white font-mono">{activeJob.rows_processed}</span>
              <span className="text-[10px] text-[#649182]"> of {activeJob.total_rows || '...'}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Inserted</span>
              <span className="text-base font-bold text-[#8BBB92] font-mono">{activeJob.rows_inserted}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Dups Skipped</span>
              <span className="text-base font-bold text-amber-400 font-mono">{activeJob.duplicate_rows_skipped}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Warnings</span>
              <span className="text-base font-bold text-amber-300 font-mono">{activeJob.rows_with_warnings}</span>
            </div>
            <div className="bg-[#030c0e] rounded-xl p-3 border border-[#12544F]/40">
              <span className="text-[#649182] text-[10px] uppercase block font-medium">Rejected</span>
              <span className="text-base font-bold text-rose-400 font-mono">{activeJob.rejected_rows}</span>
            </div>
          </div>

          {activeJob.status === 'COMPLETED' && (
            <div className="rounded-xl border border-[#2A835F]/60 bg-[#12544F]/30 p-3.5 flex items-center justify-between text-xs text-[#8BBB92]">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-[#8BBB92]" />
                <span>
                  Successfully imported <strong>{activeJob.rows_inserted}</strong> reviews into the warehouse.
                  ({activeJob.duplicate_rows_skipped} duplicates skipped without re-insertion).
                </span>
              </div>
            </div>
          )}

          {activeJob.status === 'FAILED' && (
            <div className="rounded-xl border border-rose-500/60 bg-rose-950/30 p-3.5 text-xs text-rose-300">
              <p className="font-semibold">Import Job Failed:</p>
              <p className="font-mono mt-1">{activeJob.error_summary || 'Unknown error occurred.'}</p>
            </div>
          )}
        </div>
      )}

      {/* Section 4: History of Import Batches */}
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-[#8BBB92]" />
              Import History
            </h2>
            <p className="text-xs text-[#7ea698]">
              Previous dataset ingestion batches and row-level audits.
            </p>
          </div>

          <button
            onClick={loadJobs}
            disabled={isJobsLoading}
            className="p-1.5 rounded-lg text-[#8BBB92] hover:bg-[#12544F]/50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isJobsLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {importJobs.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#649182] border border-[#12544F]/30 rounded-xl bg-[#030c0e]/30">
            No datasets have been imported yet. Use the upload box above to ingest a Kaggle CSV.
          </div>
        ) : (
          <div className="space-y-2.5">
            {importJobs.map((j) => (
              <div
                key={j.job_id}
                onClick={() => setActiveJob(j)}
                className={`rounded-xl border p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer transition-colors ${
                  activeJob?.job_id === j.job_id
                    ? 'border-[#2A835F] bg-[#12544F]/30'
                    : 'border-[#12544F]/40 bg-[#030c0e]/60 hover:border-[#12544F]'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-white">{j.original_filename}</span>
                    <span className={`uppercase text-[10px] font-semibold px-2 py-0.5 rounded ${
                      j.status === 'COMPLETED'
                        ? 'bg-[#12544F] text-[#8BBB92]'
                        : j.status === 'PROCESSING'
                        ? 'bg-amber-950/60 text-amber-300 animate-pulse'
                        : j.status === 'FAILED'
                        ? 'bg-rose-950/60 text-rose-300'
                        : 'bg-[#030c0e] text-[#649182]'
                    }`}>
                      {j.status}
                    </span>
                    <span className="text-[11px] text-[#8BBB92]">
                      ({j.rows_inserted} inserted · {j.duplicate_rows_skipped} dups)
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[#649182]">
                    <span>Job ID: {j.job_id.slice(0, 8)}...</span>
                    <span>Created: {new Date(j.created_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 text-xs">
                  <span className="text-[#7ea698] font-mono">
                    {j.rows_processed} / {j.total_rows || 0} rows
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Paginated Error Modal */}
      {showErrorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-[#12544F] bg-[#071b1f] p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#12544F]/40 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Row-Level Rejection and Warning Audit
              </h3>
              <button
                onClick={() => setShowErrorModal(false)}
                className="text-[#649182] hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[#7ea698]">
              Listing validation events recorded during dataset ingestion (Total: {totalErrors}).
            </p>

            {isErrorsLoading ? (
              <div className="py-12 text-center text-xs text-[#649182]">Loading error details...</div>
            ) : jobErrors.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#8BBB92]">No rejection details recorded.</div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-2">
                {jobErrors.map((errItem, idx) => (
                  <div
                    key={idx}
                    className={`rounded-lg p-2.5 text-xs font-mono border ${
                      errItem.type === 'rejection'
                        ? 'bg-rose-950/30 border-rose-500/30 text-rose-300'
                        : 'bg-amber-950/30 border-amber-500/30 text-amber-300'
                    }`}
                  >
                    <span className="font-bold mr-2">Row #{errItem.row}:</span>
                    <span>{errItem.issue}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination Controls */}
            <div className="flex items-center justify-between pt-3 border-t border-[#12544F]/40 text-xs text-[#7ea698]">
              <span>Page {errorPage} of {Math.max(1, Math.ceil(totalErrors / 15))}</span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => fetchJobErrors(errorModalJobId, errorPage - 1)}
                  disabled={errorPage <= 1}
                  className="px-2.5 py-1 rounded bg-[#030c0e] border border-[#12544F] disabled:opacity-50 text-white"
                >
                  Prev
                </button>
                <button
                  onClick={() => fetchJobErrors(errorModalJobId, errorPage + 1)}
                  disabled={errorPage >= Math.ceil(totalErrors / 15)}
                  className="px-2.5 py-1 rounded bg-[#030c0e] border border-[#12544F] disabled:opacity-50 text-white"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
