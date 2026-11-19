import React, { useState } from 'react';
import { Play, ShieldCheck, Clock, Layers, AlertCircle, Globe, Plus, ShoppingBag } from 'lucide-react';
import { api } from '../api/client';

const GSMARENA_PRESETS = [
  { name: 'Apple iPhone 15 Pro', brand: 'Apple', url: 'https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php', source: 'gsmarena' },
  { name: 'Samsung Galaxy S24 Ultra', brand: 'Samsung', url: 'https://www.gsmarena.com/samsung_galaxy_s24_ultra-reviews-12771.php', source: 'gsmarena' },
  { name: 'Google Pixel 8 Pro', brand: 'Google', url: 'https://www.gsmarena.com/google_pixel_8_pro-reviews-12540.php', source: 'gsmarena' },
  { name: 'GSM Arena Demo Fixture', brand: 'Apple', url: 'gsmarena://sample', source: 'gsmarena', isDemo: true },
];

const FLIPKART_PRESETS = [
  { name: 'Apple iPhone 15 (128 GB)', brand: 'Apple', url: 'https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W', source: 'flipkart' },
  { name: 'Samsung Galaxy S24 Ultra', brand: 'Samsung', url: 'https://www.flipkart.com/samsung-galaxy-s24-ultra-5g-titanium-gray-256-gb/product-reviews/itm46ea38992160b?pid=MOBGWGX6FHKFNHZH', source: 'flipkart' },
  { name: 'Realme 12 Pro 5G', brand: 'Realme', url: 'https://www.flipkart.com/realme-12-pro-5g-navigator-beige-128-gb/product-reviews/itm69fa1da42a037?pid=MOBGYVZZFDFGFHZU', source: 'flipkart' },
  { name: 'Flipkart Demo Fixture', brand: 'Apple', url: 'flipkart://sample', source: 'flipkart', isDemo: true },
];

export default function ScraperLauncher({ onJobLaunched }) {
  const [scraperType, setScraperType] = useState('gsmarena'); // 'gsmarena' | 'flipkart'
  const [targetUrl, setTargetUrl] = useState(GSMARENA_PRESETS[0].url);
  const [productName, setProductName] = useState(GSMARENA_PRESETS[0].name);
  const [brand, setBrand] = useState(GSMARENA_PRESETS[0].brand);
  const [pageMode, setPageMode] = useState('limited'); // 'limited' | 'unlimited'
  const [maxPages, setMaxPages] = useState('5'); // Default: 5
  const [maxReviews, setMaxReviews] = useState('20');
  const [delaySeconds, setDelaySeconds] = useState(1.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const activePresets = scraperType === 'flipkart' ? FLIPKART_PRESETS : GSMARENA_PRESETS;

  const handleSwitchScraperType = (type) => {
    setScraperType(type);
    const presets = type === 'flipkart' ? FLIPKART_PRESETS : GSMARENA_PRESETS;
    setTargetUrl(presets[0].url);
    setProductName(presets[0].name);
    setBrand(presets[0].brand);
    setError(null);
  };

  const handleSelectPreset = (preset) => {
    setTargetUrl(preset.url);
    setProductName(preset.name);
    setBrand(preset.brand);
    setScraperType(preset.source);
  };

  const handleSelectCustom = () => {
    setTargetUrl('');
    setProductName('');
    setBrand('');
  };

  const handleUrlChange = (newUrl) => {
    setTargetUrl(newUrl);
    // Auto-detect scraper type based on URL input
    const lower = newUrl.toLowerCase();
    if (lower.includes('flipkart.com') || lower.startsWith('flipkart://')) {
      if (scraperType !== 'flipkart') setScraperType('flipkart');
    } else if (lower.includes('gsmarena.com') || lower.startsWith('gsmarena://')) {
      if (scraperType !== 'gsmarena') setScraperType('gsmarena');
    }
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

      // Auto-resolve scraper type from URL
      let resolvedScraper = scraperType;
      const lower = targetUrl.toLowerCase();
      if (lower.includes('flipkart.com') || lower.startsWith('flipkart://')) {
        resolvedScraper = 'flipkart';
      } else if (lower.includes('gsmarena.com') || lower.startsWith('gsmarena://')) {
        resolvedScraper = 'gsmarena';
      }

      const payload = {
        target_url: targetUrl.trim(),
        scraper_type: resolvedScraper,
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

        {/* Source Switcher Toggle */}
        <div className="flex items-center space-x-1.5 p-1 bg-[#030c0e] rounded-xl border border-[#12544F]/70">
          <button
            type="button"
            onClick={() => handleSwitchScraperType('gsmarena')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              scraperType === 'gsmarena'
                ? 'bg-[#2A835F] text-white shadow-md shadow-[#2A835F]/25'
                : 'text-[#7ea698] hover:text-white'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>GSM Arena</span>
          </button>
          <button
            type="button"
            onClick={() => handleSwitchScraperType('flipkart')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              scraperType === 'flipkart'
                ? 'bg-[#2A835F] text-white shadow-md shadow-[#2A835F]/25'
                : 'text-[#7ea698] hover:text-white'
            }`}
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Flipkart</span>
          </button>
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
            {scraperType === 'flipkart' ? 'Flipkart Presets' : 'GSM Arena Presets'}{' '}
            <span className="text-[#649182] font-normal lowercase">(optional shortcuts)</span>
          </label>
          <span className="text-[11px] text-[#649182]">Clicking populates URL & metadata</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {activePresets.map((preset) => {
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
                <div className="font-semibold text-xs truncate">{preset.name}</div>
                <div className="text-[11px] text-[#7ea698] flex items-center justify-between mt-1">
                  <span>{preset.brand}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                    preset.isDemo
                      ? 'bg-amber-950/40 border-amber-700/60 text-amber-300'
                      : 'bg-[#030c0e] border-[#12544F]/60 text-[#8BBB92]'
                  }`}>
                    {preset.isDemo ? 'Offline Demo' : scraperType === 'flipkart' ? 'Flipkart' : 'GSM Arena'}
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
              !activePresets.some((p) => p.url.trim() === targetUrl.trim())
                ? 'border-[#2A835F] bg-[#12544F]/40 text-white shadow-md shadow-[#2A835F]/20'
                : 'border-[#12544F]/40 bg-[#030c0e]/80 text-[#7ea698] hover:border-[#2A835F]/50 hover:text-[#f2fbf6]'
            }`}
          >
            <div className="font-semibold text-xs flex items-center space-x-1.5 truncate">
              <Plus className="w-3.5 h-3.5 text-[#8BBB92] shrink-0" />
              <span>Custom URL</span>
            </div>
            <div className="text-[11px] text-[#7ea698] flex items-center justify-between mt-1">
              <span>User Defined</span>
              <span className="text-[10px] bg-[#030c0e] border border-[#12544F]/60 text-[#8BBB92] px-1.5 py-0.5 rounded">
                Custom
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
              {activePresets.find((p) => p.url.trim() === targetUrl.trim()) ? (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#12544F]/60 border border-[#2A835F]/50 text-[#8BBB92] font-medium">
                  Preset: {activePresets.find((p) => p.url.trim() === targetUrl.trim()).name}
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
                onChange={(e) => handleUrlChange(e.target.value)}
                placeholder={
                  scraperType === 'flipkart'
                    ? 'https://www.flipkart.com/.../product-reviews/... or flipkart://sample'
                    : 'https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php'
                }
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
              {scraperType === 'flipkart'
                ? 'Accepts Flipkart product-reviews URLs or offline demo fixture flipkart://sample'
                : 'Accepts GSM Arena smartphone review or user opinion URLs or gsmarena://sample'}
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
                  placeholder="e.g. 5, 10, 20"
                  value={maxPages}
                  onChange={(e) => setMaxPages(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[#030c0e] border border-[#12544F]/70 rounded-lg text-xs text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
                />
                <div className="flex items-center space-x-1 mt-1.5">
                  {[5, 10, 25, 50].map((num) => (
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
