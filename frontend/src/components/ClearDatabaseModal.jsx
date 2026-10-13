import React, { useState } from 'react';
import { AlertTriangle, Trash2, X, RefreshCw, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';

export default function ClearDatabaseModal({ isOpen, onClose, onDatabaseCleared, stats = {} }) {
  const [confirmInput, setConfirmInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const isConfirmed = confirmInput.trim().toUpperCase() === 'CLEAR';

  const handleClear = async () => {
    if (!isConfirmed || isLoading) return;
    setIsLoading(true);
    setError(null);

    try {
      const res = await api.clearDatabase();
      setResult(res);
      if (onDatabaseCleared) {
        await onDatabaseCleared();
      }
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err) {
      console.error('Failed to clear database:', err);
      setError(err.message || 'Failed to clear database');
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setConfirmInput('');
    setError(null);
    setResult(null);
    setIsLoading(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl border border-rose-800/60 bg-[#071b1f] p-6 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={handleClose}
          disabled={isLoading}
          className="absolute right-4 top-4 text-[#7ea698] hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3 pb-4 border-b border-[#12544F]/50">
          <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-700/60 text-rose-400">
            <Trash2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Clear Full Database</h3>
            <p className="text-xs text-rose-300">Irreversible System Reset</p>
          </div>
        </div>

        {/* Success State */}
        {result ? (
          <div className="py-8 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-[#8BBB92] mx-auto animate-bounce" />
            <h4 className="text-base font-bold text-white">Database Cleared Successfully!</h4>
            <p className="text-xs text-[#7ea698]">
              All reviews, products, and jobs have been wiped and tables reset.
            </p>
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {/* Warning Alert */}
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-700/60 text-rose-200 text-xs flex items-start space-x-3">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-rose-100">This action will permanently delete:</p>
                <ul className="list-disc list-inside space-y-0.5 text-rose-200/90 text-[11px]">
                  <li>
                    All verified reviews (<strong className="text-white">{stats.totalReviews ?? 0}</strong> records)
                  </li>
                  <li>
                    All smartphone models (<strong className="text-white">{stats.totalProducts ?? 0}</strong> catalog devices)
                  </li>
                  <li>
                    All web scraper jobs (<strong className="text-white">{stats.totalJobs ?? 0}</strong> historical tasks)
                  </li>
                  <li>All Kaggle dataset import jobs and aspect metadata</li>
                </ul>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-700 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Confirmation Input */}
            <div className="space-y-3 pt-1">
              <label className="block text-xs text-[#7ea698]">
                Type <span className="font-bold font-mono text-white bg-[#030c0e] px-1.5 py-0.5 rounded border border-[#12544F]">CLEAR</span> below to confirm:
              </label>
              <input
                type="text"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                placeholder="CLEAR"
                disabled={isLoading}
                className="w-full px-3.5 py-2.5 bg-[#030c0e] border border-rose-900/70 focus:border-rose-500 rounded-xl text-sm font-mono text-white placeholder-rose-900/50 focus:outline-none transition-colors"
              />
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-[#12544F]/50">
              <button
                type="button"
                onClick={handleClose}
                disabled={isLoading}
                className="px-4 py-2.5 rounded-xl bg-[#030c0e] border border-[#12544F]/70 text-xs font-semibold text-[#7ea698] hover:text-white hover:bg-[#12544F]/30 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleClear}
                disabled={!isConfirmed || isLoading}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-40 disabled:hover:bg-rose-600 text-white text-xs font-bold transition-all shadow-lg shadow-rose-950/50"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Wiping Database...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Permanently Clear Database</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
