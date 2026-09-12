import React, { useState } from 'react';
import { Play, ShieldCheck, Clock, Layers, AlertCircle, Globe, Cpu } from 'lucide-react';
import { api } from '../api/client';

const DEMO_PRESETS = [
  { name: 'Apple iPhone 15 Pro', brand: 'Apple', url: 'demo://iphone-15-pro' },
  { name: 'Samsung Galaxy S24 Ultra', brand: 'Samsung', url: 'demo://galaxy-s24-ultra' },
  { name: 'Google Pixel 8 Pro', brand: 'Google', url: 'demo://pixel-8-pro' },
];

const GSMARENA_PRESETS = [
  { name: 'Apple iPhone 15 Pro', brand: 'Apple', url: 'https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php' },
  { name: 'Samsung Galaxy S24 Ultra', brand: 'Samsung', url: 'https://www.gsmarena.com/samsung_galaxy_s24_ultra-reviews-12771.php' },
  { name: 'Google Pixel 8 Pro', brand: 'Google', url: 'https://www.gsmarena.com/google_pixel_8_pro-reviews-12540.php' },
];

export default function ScraperLauncher({ onJobLaunched }) {
  const [adapterType, setAdapterType] = useState('demo'); // 'demo' | 'gsmarena'
  const [targetUrl, setTargetUrl] = useState(DEMO_PRESETS[0].url);
  const [productName, setProductName] = useState(DEMO_PRESETS[0].name);
  const [brand, setBrand] = useState(DEMO_PRESETS[0].brand);
  const [pageMode, setPageMode] = useState('limited'); // 'limited' | 'unlimited'
  const [maxPages, setMaxPages] = useState('5'); // Default: 5
  const [maxReviews, setMaxReviews] = useState('20');
  const [delaySeconds, setDelaySeconds] = useState(1.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleAdapterChange = (type) => {
    setAdapterType(type);
    const defaultPreset = type === 'demo' ? DEMO_PRESETS[0] : GSMARENA_PRESETS[0];
    setTargetUrl(defaultPreset.url);
    setProductName(defaultPreset.name);
    setBrand(defaultPreset.brand);
  };

  const handleSelectPreset = (preset) => {
    setTargetUrl(preset.url);
    setProductName(preset.name);
    setBrand(preset.brand);
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
        scraper_type: adapterType,
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

  const currentPresets = adapterType === 'demo' ? DEMO_PRESETS : GSMARENA_PRESETS;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <span>Dispatch Scraping Job</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Collect smartphone reviews with polite delays, limits, and 3-tier deduplication
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-full font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Ethical Scraper Policy</span>
          </span>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Source Adapter Selector */}
      <div className="mt-5">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
          Select Review Source Adapter
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => handleAdapterChange('demo')}
            className={`p-3.5 rounded-xl border text-left transition-all flex items-start space-x-3 ${
              adapterType === 'demo'
                ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-lg shadow-indigo-500/10'
                : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <div className="p-2 rounded-lg bg-indigo-900/40 border border-indigo-700/50 mt-0.5">
              <Cpu className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="font-semibold text-sm">Demo / Local Fixture</div>
              <div className="text-xs text-slate-400 mt-0.5">
                Deterministic HTML fixtures for offline testing & viva demonstrations
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleAdapterChange('gsmarena')}
            className={`p-3.5 rounded-xl border text-left transition-all flex items-start space-x-3 ${
              adapterType === 'gsmarena'
                ? 'border-emerald-500 bg-emerald-950/40 text-white shadow-lg shadow-emerald-500/10'
                : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <div className="p-2 rounded-lg bg-emerald-900/40 border border-emerald-700/50 mt-0.5">
              <Globe className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="font-semibold text-sm flex items-center space-x-1.5">
                <span>GSM Arena</span>
                <span className="text-[10px] bg-emerald-900/60 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-700/50">
                  Public Source
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                Live user opinions from gsmarena.com (No login/CAPTCHA required)
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Quick Presets (Optional Shortcuts) */}
      <div className="mt-5">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Quick Presets <span className="text-slate-500 font-normal lowercase">(optional shortcuts)</span>
          </label>
          <span className="text-[11px] text-slate-500">Clicking populates URL & metadata</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {currentPresets.map((preset) => {
            const isSelected = targetUrl.trim() === preset.url.trim();
            return (
              <button
                key={preset.url}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-md shadow-indigo-500/10'
                    : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="font-medium text-sm truncate">{preset.name}</div>
                <div className="text-xs text-slate-400 flex items-center justify-between mt-1">
                  <span>{preset.brand}</span>
                  <span className="font-mono text-[10px] bg-slate-800 px-1.5 py-0.5 rounded">
                    {adapterType === 'demo' ? 'Fixture' : 'GSM Arena'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-300">
                Target Source URL <span className="text-indigo-400 text-[11px] font-normal">(Authoritative Input)</span>
              </label>
              {currentPresets.find((p) => p.url.trim() === targetUrl.trim()) ? (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-700/60 text-indigo-300 font-medium">
                  Preset: {currentPresets.find((p) => p.url.trim() === targetUrl.trim()).name}
                </span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-700/60 text-emerald-300 font-medium">
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
                placeholder={
                  adapterType === 'demo'
                    ? 'demo://local-catalog/...'
                    : 'https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php'
                }
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono pr-20"
              />
              {targetUrl && (
                <button
                  type="button"
                  onClick={() => {
                    setTargetUrl('');
                    setProductName('');
                    setBrand('');
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {adapterType === 'demo'
                ? 'Accepts demo fixture schemes (e.g. demo://iphone-15-pro)'
                : 'Accepts ANY GSM Arena smartphone review or user opinion URL'}
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-300">
                Product Name & Brand
              </label>
              <span className="text-[11px] text-slate-500 font-normal">Optional (auto-derived if empty)</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Product Name (optional)"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <input
                type="text"
                placeholder="Brand (optional)"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              If left blank, product metadata will be automatically extracted from the review page.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Max Pages</span>
              </label>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={() => setPageMode('limited')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    pageMode === 'limited'
                      ? 'bg-indigo-600 text-white font-bold'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Limited
                </button>
                <button
                  type="button"
                  onClick={() => setPageMode('unlimited')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    pageMode === 'unlimited'
                      ? 'bg-purple-600 text-white font-bold shadow-sm shadow-purple-500/20'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
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
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <div className="flex items-center space-x-1 mt-1.5">
                  {[5, 10, 25, 50, 100].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setMaxPages(String(num))}
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        maxPages === String(num)
                          ? 'bg-indigo-900/60 border border-indigo-600 text-indigo-200'
                          : 'bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-300'
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-2.5 rounded-lg bg-purple-950/30 border border-purple-800/40 text-[11px] text-purple-300">
                <span className="font-semibold block">Unlimited Mode Active</span>
                <span className="text-slate-400 text-[10px]">
                  Crawls until no next page, loop detected, or empty page.
                </span>
              </div>
            )}
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                <span>Inter-Page Delay</span>
              </label>
              <span className="text-xs font-bold text-indigo-400 font-mono">{delaySeconds}s</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.5"
              value={delaySeconds}
              onChange={(e) => setDelaySeconds(e.target.value)}
              className="w-full accent-indigo-500 bg-slate-800 rounded-lg h-2"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">
              Max Reviews Cap
            </label>
            <input
              type="number"
              min="1"
              max="200"
              placeholder="e.g. 20 (empty = unlimited)"
              value={maxReviews}
              onChange={(e) => setMaxReviews(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        <div className="pt-3 flex items-center justify-between">
          <div className="text-[11px] text-slate-400 hidden sm:block">
            * 3-Tier Deduplication: Source Review ID → Review Permalink URL → Deterministic SHA256(Product + Source + Content)
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 transition-all duration-200 disabled:opacity-50 ml-auto"
          >
            <Play className={`w-4 h-4 fill-current ${isSubmitting ? 'animate-spin' : ''}`} />
            <span>{isSubmitting ? 'Dispatching...' : 'Start Scrape Job'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
