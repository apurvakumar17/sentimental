import React, { useState } from 'react';
import { Play, ShieldCheck, Clock, Layers, AlertCircle, Globe, Plus } from 'lucide-react';
import { api } from '../api/client';

const PRESETS = [
  { name: 'Apple iPhone 15 Pro', brand: 'Apple', url: 'https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php' },
  { name: 'Samsung Galaxy S24 Ultra', brand: 'Samsung', url: 'https://www.gsmarena.com/samsung_galaxy_s24_ultra-reviews-12771.php' },
  { name: 'Google Pixel 8 Pro', brand: 'Google', url: 'https://www.gsmarena.com/google_pixel_8_pro-reviews-12540.php' },
];

export default function ScraperLauncher({ onJobLaunched }) {
  const [targetUrl, setTargetUrl] = useState(PRESETS[0].url);
  const [productName, setProductName] = useState(PRESETS[0].name);
  const [brand, setBrand] = useState(PRESETS[0].brand);
  const [pageMode, setPageMode] = useState('limited'); // 'limited' | 'unlimited'
  const [maxPages, setMaxPages] = useState('5'); // Default: 5
  const [maxReviews, setMaxReviews] = useState('20');
  const [delaySeconds, setDelaySeconds] = useState(1.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSelectPreset = (preset) => {
    setTargetUrl(preset.url);
    setProductName(preset.name);
    setBrand(preset.brand);
  };

  const handleSelectCustom = () => {
    setTargetUrl('');
    setProductName('');
    setBrand('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      let parsedMaxPages = null;
      if (pageMode === 'limited') {
        parsedMaxPages = parseInt(maxPages, 10);
        if (isNaN(parsedMaxPages) || parsedMaxPages < 1) {
          setError('Max Pages must be a positive integer (>= 1)');
          setIsSubmitting(false);
          return;
        }
      }

      const payload = {
        target_url: targetUrl.trim(),
        scraper_type: 'gsmarena',
        product_name: productName.trim() || null,
        brand: brand.trim() || null,
        max_pages: parsedMaxPages,
        max_reviews: maxReviews ? parseInt(maxReviews, 10) : null,
        delay_seconds: parseFloat(delaySeconds),
      };

      const res = await api.triggerScrape(payload);
      if (onJobLaunched) {
        onJobLaunched(res);
      }
    } catch (err) {
      setError(err.message || 'Failed to dispatch scraping job');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#12544F]/50">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <span>Dispatch Scraping Job</span>
          </h2>
          <p className="text-xs text-[#7ea698] mt-0.5">
            Collect smartphone reviews with polite delays, limits, and deduplication
          </p>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3.5 rounded-xl bg-rose-950/60 border border-rose-700/60 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Quick Presets (Optional Shortcuts) */}
      <div className="mt-5">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-[#8BBB92]">
            Quick Presets <span className="text-[#649182] font-normal lowercase">(optional shortcuts)</span>
          </label>
          <span className="text-[11px] text-[#649182]">Clicking populates URL & metadata</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {PRESETS.map((preset) => {
            const isSelected = targetUrl.trim() === preset.url.trim();
            return (
              <button
                key={preset.url}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-[#2A835F] bg-[#12544F]/40 text-white shadow-md shadow-[#2A835F]/20'
                    : 'border-[#12544F]/40 bg-[#030c0e]/80 text-[#7ea698] hover:border-[#2A835F]/50 hover:text-[#f2fbf6]'
                }`}
              >
                <div className="font-semibold text-sm truncate">{preset.name}</div>
                <div className="text-xs text-[#7ea698] flex items-center justify-between mt-1">
                  <span>{preset.brand}</span>
                  <span className="text-[10px] bg-[#030c0e] border border-[#12544F]/60 text-[#8BBB92] px-1.5 py-0.5 rounded  ">
                    GSM Arena
                  </span>
                </div>
              </button>
            );
          })}

          {/* Custom Empty Preset */}
          <button
            type="button"
            onClick={handleSelectCustom}
            className={`p-3 rounded-xl border text-left transition-all ${
              !PRESETS.some((p) => p.url.trim() === targetUrl.trim())
                ? 'border-[#2A835F] bg-[#12544F]/40 text-white shadow-md shadow-[#2A835F]/20'
                : 'border-[#12544F]/40 bg-[#030c0e]/80 text-[#7ea698] hover:border-[#2A835F]/50 hover:text-[#f2fbf6]'
            }`}
          >
            <div className="font-semibold text-sm flex items-center space-x-1.5 truncate">
              <Plus className="w-3.5 h-3.5 text-[#8BBB92] shrink-0" />
              <span>Custom URL</span>
            </div>
            <div className="text-xs text-[#7ea698] flex items-center justify-between mt-1">
              <span>User Defined</span>
              <span className="text-[10px] bg-[#030c0e] border border-[#12544F]/60 text-[#8BBB92] px-1.5 py-0.5 rounded  ">
                GSM Arena
              </span>
            </div>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-[#f2fbf6]">
                Target Source URL <span className="text-[#8BBB92] text-[11px] font-normal">(Authoritative Input)</span>
              </label>
              {PRESETS.find((p) => p.url.trim() === targetUrl.trim()) ? (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#12544F]/60 border border-[#2A835F]/50 text-[#8BBB92] font-medium">
                  Preset: {PRESETS.find((p) => p.url.trim() === targetUrl.trim()).name}
                </span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#2A835F]/30 border border-[#2A835F]/80 text-[#8BBB92] font-medium">
                  Custom URL Active
                </span>
              )}
            </div>
            <div className="relative">
              <input
                type="text"
                required
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php"
                className="w-full px-3 py-2 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-sm text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] pr-20 transition-colors"
              />
              {targetUrl && (
                <button
                  type="button"
                  onClick={() => {
                    setTargetUrl('');
                    setProductName('');
                    setBrand('');
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] px-2 py-1 rounded bg-[#0d2a2e] hover:bg-[#12544F] text-[#8BBB92] hover:text-white transition-colors border border-[#12544F]/60"
                >
                  Clear
                </button>
              )}
            </div>
            <p className="text-[11px] text-[#649182] mt-1">
              Accepts ANY GSM Arena smartphone review or user opinion URL
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-[#f2fbf6]">
                Product Name & Brand
              </label>
              <span className="text-[11px] text-[#649182] font-normal">Optional (auto-derived if empty)</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Product Name (optional)"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="w-full px-3 py-2 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-sm text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
              />
              <input
                type="text"
                placeholder="Brand (optional)"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full px-3 py-2 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-sm text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
              />
            </div>
            <p className="text-[11px] text-[#649182] mt-1">
              If left blank, product metadata will be automatically extracted from the review page.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-medium text-[#f2fbf6] flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-[#8BBB92]" />
                <span>Max Pages</span>
              </label>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={() => setPageMode('limited')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    pageMode === 'limited'
                      ? 'bg-[#2A835F] text-white font-bold shadow-sm shadow-[#2A835F]/20'
                      : 'bg-[#030c0e] border border-[#12544F]/50 text-[#7ea698] hover:text-[#f2fbf6]'
                  }`}
                >
                  Limited
                </button>
                <button
                  type="button"
                  onClick={() => setPageMode('unlimited')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    pageMode === 'unlimited'
                      ? 'bg-[#12544F] border border-[#2A835F] text-[#8BBB92] font-bold shadow-sm shadow-[#2A835F]/20'
                      : 'bg-[#030c0e] border border-[#12544F]/50 text-[#7ea698] hover:text-[#f2fbf6]'
                  }`}
                >
                  ∞ Unlimited
                </button>
              </div>
            </div>

            {pageMode === 'limited' ? (
              <div>
                <input
                  type="number"
                  min="1"
                  step="1"
                  required
                  placeholder="e.g. 10, 20, 50, 100"
                  value={maxPages}
                  onChange={(e) => setMaxPages(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
                />
                <div className="flex items-center space-x-1 mt-1.5">
                  {[5, 10, 25, 50, 100].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setMaxPages(String(num))}
                      className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                        maxPages === String(num)
                          ? 'bg-[#12544F] border border-[#2A835F] text-[#8BBB92] font-semibold'
                          : 'bg-[#030c0e] border border-[#12544F]/40 text-[#7ea698] hover:bg-[#12544F]/30 hover:text-[#f2fbf6]'
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-2.5 rounded-lg bg-[#030c0e] border border-[#2A835F]/40 text-[11px] text-[#8BBB92]">
                <span className="font-semibold block">Unlimited Mode Active</span>
                <span className="text-[#7ea698] text-[10px]">
                  Crawls until no next page, loop detected, or empty page.
                </span>
              </div>
            )}
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-medium text-[#f2fbf6] flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-[#8BBB92]" />
                <span>Inter-Page Delay</span>
              </label>
              <span className="text-xs font-bold text-[#8BBB92]">{delaySeconds}s</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.5"
              value={delaySeconds}
              onChange={(e) => setDelaySeconds(e.target.value)}
              className="w-full accent-[#2A835F] bg-[#030c0e] rounded-lg h-2"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-[#f2fbf6] block mb-1.5">
              Max Reviews Cap
            </label>
            <input
              type="number"
              min="1"
              max="200"
              placeholder="e.g. 20 (empty = unlimited)"
              value={maxReviews}
              onChange={(e) => setMaxReviews(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
            />
          </div>
        </div>

        <div className="pt-3 flex items-center justify-between">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#2A835F] via-[#2A835F] to-[#12544F] hover:from-[#329b71] hover:to-[#186a64] text-white font-bold text-sm shadow-lg shadow-[#2A835F]/25 transition-all duration-200 disabled:opacity-50 ml-auto hover:scale-[1.01] active:scale-[0.99]"
          >
            <Play className={`w-4 h-4 fill-current ${isSubmitting ? 'animate-spin' : ''}`} />
            <span>{isSubmitting ? 'Dispatching...' : 'Start Scrape Job'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
