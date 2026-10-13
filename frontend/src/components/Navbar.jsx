import React from 'react';
import {
  Database,
  Cpu,
  Layers,
  SlidersHorizontal,
  UploadCloud,
  Sparkles,
  Award
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const tabs = [
    { id: 'dashboard', label: 'Overview', icon: Layers },
    { id: 'scraper', label: 'Scraper', fullLabel: 'Scraper Engine', icon: Cpu },
    { id: 'reviews', label: 'Reviews', fullLabel: 'Review Warehouse', icon: Database },
    { id: 'datasets', label: 'Quality', fullLabel: 'Dataset & Quality', icon: SlidersHorizontal },
    { id: 'imports', label: 'Import', fullLabel: 'Dataset Import', icon: UploadCloud },
    { id: 'absa', label: 'ABSA', fullLabel: 'ABSA NLP', icon: Sparkles },
    { id: 'recommendations', label: 'Recommend', fullLabel: 'Recommendations', icon: Award, isHighlight: true },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-[#12544F]/50 bg-[#030c0e]/95 backdrop-blur-2xl shadow-lg shadow-black/40">
      <div className="w-full max-w-7xl mx-auto px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-2 lg:gap-4">
          
          {/* Brand Identity / Logo */}
          <div
            onClick={() => setActiveTab('dashboard')}
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
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[#2A835F]/20 text-[#8BBB92] border border-[#2A835F]/40 hidden sm:inline-block">
                  Phase 4
                </span>
              </div>
              <p className="text-[11px] text-[#7ea698] font-medium leading-none hidden 2xl:block">
                Aspect Sentiment & Smartphone Recommendations
              </p>
            </div>
          </div>

          {/* Segmented Navigation Dock */}
          <nav className="flex items-center min-w-0 shrink-0">
            <div className="flex items-center p-1 rounded-xl bg-[#071b1f]/90 border border-[#12544F]/60 backdrop-blur-md shadow-inner gap-0.5 sm:gap-1 overflow-x-auto no-scrollbar">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                const isHighlight = tab.isHighlight;

                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`relative flex items-center space-x-1 sm:space-x-1.5 px-2 sm:px-2.5 xl:px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-200 select-none ${
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
                    
                    {/* Responsive text label */}
                    <span className="whitespace-nowrap">
                      {tab.fullLabel ? (
                        <>
                          <span className="hidden 2xl:inline">{tab.fullLabel}</span>
                          <span className="2xl:hidden">{tab.label}</span>
                        </>
                      ) : (
                        <span>{tab.label}</span>
                      )}
                    </span>

                    {/* Subtle dot indicator on highlight tab */}
                    {isHighlight && !isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#8BBB92] animate-pulse hidden sm:inline-block" />
                    )}
                  </button>
                );
              })}
            </div>
          </nav>

        </div>
      </div>
    </header>
  );
}
