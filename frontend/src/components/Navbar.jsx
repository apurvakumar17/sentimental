import React, { useState } from 'react';
import {
  Database,
  Cpu,
  Layers,
  UploadCloud,
  Sparkles,
  Award,
  Menu,
  X
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const tabs = [
    { id: 'dashboard', label: 'Overview', desc: 'System overview & catalog summary', icon: Layers },
    { id: 'scraper', label: 'Scraper', desc: 'Scraper Engine & background jobs', icon: Cpu },
    { id: 'reviews', label: 'Reviews', desc: 'Review Warehouse & text preview', icon: Database },
    { id: 'imports', label: 'Import', desc: 'Kaggle CSV dataset ingestion', icon: UploadCloud },
    { id: 'absa', label: 'ABSA', desc: 'Aspect-Based Sentiment Analysis', icon: Sparkles },
    { id: 'recommendations', label: 'Recommendations', shortLabel: 'Recommend', desc: 'Multi-criteria phone ranking', icon: Award, isHighlight: true },
  ];

  const handleTabSelect = (tabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[#12544F]/50 bg-[#030c0e]/95 backdrop-blur-2xl shadow-lg shadow-black/40">
      <div className="w-full max-w-7xl mx-auto px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-3">
          
          {/* Brand Identity / Logo */}
          <div
            onClick={() => handleTabSelect('dashboard')}
            className="flex items-center space-x-2.5 sm:space-x-3 cursor-pointer select-none group shrink-0"
          >
            <div className="relative w-9 h-9 sm:w-10 sm:h-10 flex items-center justify-center shrink-0 rounded-xl bg-gradient-to-br from-[#12544F]/60 to-[#071b1f] border border-[#2A835F]/40 group-hover:border-[#2A835F] group-hover:shadow-[0_0_15px_rgba(42,131,95,0.4)] transition-all duration-300">
              <img
                src="/logo.png"
                alt="Sentimental Logo"
                className="w-7 h-7 sm:w-8 sm:h-8 object-contain filter drop-shadow-[0_2px_8px_rgba(42,131,95,0.4)] group-hover:scale-105 transition-transform"
              />
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg sm:text-xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-[#8BBB92] to-[#2A835F] group-hover:from-white group-hover:to-[#8BBB92] transition-all">
                  Sentimental
                </span>
              </div>
              <p className="text-[11px] text-[#7ea698] font-medium leading-none hidden xl:block">
                Aspect Sentiment & Smartphone Recommendations
              </p>
            </div>
          </div>

          {/* Desktop Navigation Dock (md and up) */}
          <nav className="hidden md:flex items-center min-w-0">
            <div className="flex items-center p-1 rounded-xl bg-[#071b1f]/90 border border-[#12544F]/60 backdrop-blur-md shadow-inner gap-0.5 lg:gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                const isHighlight = tab.isHighlight;

                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabSelect(tab.id)}
                    title={`${tab.label}: ${tab.desc}`}
                    className={`relative flex items-center space-x-1 sm:space-x-1.5 px-2.5 lg:px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-200 select-none ${
                      isActive
                        ? isHighlight
                          ? 'bg-gradient-to-r from-[#12544F] via-[#2A835F] to-[#12544F] text-white shadow-md shadow-[#2A835F]/35 border border-[#8BBB92]/60'
                          : 'bg-[#12544F]/80 text-[#8BBB92] shadow-sm shadow-[#2A835F]/20 border border-[#2A835F]/70'
                        : isHighlight
                        ? 'text-[#8BBB92] hover:text-white hover:bg-[#12544F]/40 border border-[#2A835F]/30 hover:border-[#2A835F]/60'
                        : 'text-[#7ea698] hover:text-[#f2fbf6] hover:bg-[#12544F]/30 border border-transparent'
                    }`}
                  >
                    <Icon
                      className={`w-3.5 h-3.5 shrink-0 transition-transform ${
                        isActive
                          ? 'text-white scale-110'
                          : isHighlight
                          ? 'text-[#8BBB92]'
                          : 'text-[#649182]'
                      }`}
                    />
                    
                    {/* Responsive text label: compact on medium, full on large */}
                    <span>
                      {tab.shortLabel ? (
                        <>
                          <span className="hidden lg:inline">{tab.label}</span>
                          <span className="lg:hidden">{tab.shortLabel}</span>
                        </>
                      ) : (
                        <span>{tab.label}</span>
                      )}
                    </span>

                    {/* Subtle dot indicator on highlight tab */}
                    {isHighlight && !isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#8BBB92] animate-pulse hidden xl:inline-block" />
                    )}
                  </button>
                );
              })}
            </div>
          </nav>

          {/* Mobile Menu Button (< md) */}
          <div className="flex md:hidden items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl bg-[#071b1f] border border-[#12544F]/60 text-[#8BBB92] hover:text-white hover:bg-[#12544F]/40 transition-colors"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>

        {/* Mobile Dropdown Panel (< md) */}
        {mobileMenuOpen && (
          <div className="md:hidden py-3 px-2 border-t border-[#12544F]/40 space-y-1 bg-[#030c0e]/98 backdrop-blur-2xl">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              const isHighlight = tab.isHighlight;

              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabSelect(tab.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? isHighlight
                        ? 'bg-gradient-to-r from-[#12544F] to-[#2A835F] text-white shadow-md border border-[#8BBB92]/60'
                        : 'bg-[#12544F]/80 text-[#8BBB92] border border-[#2A835F]/70'
                      : 'text-[#7ea698] hover:text-[#f2fbf6] hover:bg-[#12544F]/30'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-[#8BBB92]'}`} />
                    <div className="text-left">
                      <div className="font-semibold">{tab.label}</div>
                      <div className="text-[10px] text-[#649182] font-normal">{tab.desc}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

      </div>
    </header>
  );
}
