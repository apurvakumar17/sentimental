import React from 'react';
import { Database, Cpu, Layers } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const tabs = [
    { id: 'dashboard', label: 'Overview', icon: Layers },
    { id: 'scraper', label: 'Scraper Engine', icon: Cpu },
    { id: 'reviews', label: 'Review Warehouse', icon: Database },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-[#12544F]/40 bg-[#030c0e]/90 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 flex items-center justify-center shrink-0">
              <img
                src="/logo.png"
                alt="Sentimental Logo"
                className="w-full h-full object-contain filter drop-shadow-[0_2px_12px_rgba(42,131,95,0.4)]"
              />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-[#8BBB92] to-[#2A835F]">
                  Sentimental
                </span>
              </div>
              <p className="text-xs text-[#8BBB92]/80 hidden sm:block">
                Smartphone Aspect Based Sentiment Analysis
              </p>
            </div>
          </div>

          <nav className="flex space-x-1 sm:space-x-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-[#12544F]/60 text-[#8BBB92] border border-[#2A835F]/70 shadow-sm shadow-[#2A835F]/20 font-semibold'
                      : 'text-[#7ea698] hover:text-[#f2fbf6] hover:bg-[#12544F]/30 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#8BBB92]' : 'text-[#649182]'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
