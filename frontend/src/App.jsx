import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Smartphone, 
  CheckCircle2, 
  Layers, 
  Cpu, 
  TrendingUp, 
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { api } from './api/client';
import Navbar from './components/Navbar';
import StatCard from './components/StatCard';
import ScraperLauncher from './components/ScraperLauncher';
import JobTracker from './components/JobTracker';
import JobHistory from './components/JobHistory';
import ReviewExplorer from './components/ReviewExplorer';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    try {
      const [healthRes, prodsRes, jobsRes] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getProducts().catch(() => []),
        api.getJobs().catch(() => ({ items: [] }))
      ]);
      setHealth(healthRes);
      setProducts(prodsRes || []);
      const jobList = jobsRes.items || [];
      setJobs(jobList);

      // Set active job if there is a running one, or most recent
      const runningJob = jobList.find(j => j.status === 'RUNNING' || j.status === 'PENDING');
      if (runningJob) {
        setActiveJob(runningJob);
      } else if (jobList.length > 0 && !activeJob) {
        setActiveJob(jobList[0]);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleJobLaunched = (newJob) => {
    setActiveJob(newJob);
    setJobs(prev => [newJob, ...prev]);
    setActiveTab('scraper');
  };

  const handleJobCompleted = () => {
    loadData();
  };

  const totalReviews = products.reduce((acc, p) => acc + (p.review_count || 0), 0);
  const totalDuplicates = jobs.reduce((acc, j) => acc + (j.duplicate_reviews || 0), 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Collected Reviews"
            value={totalReviews}
            subtitle="Validated & Deduplicated"
            icon={Database}
            color="indigo"
          />
          <StatCard
            title="Monitored Devices"
            value={products.length}
            subtitle="Smartphone Catalog"
            icon={Smartphone}
            color="purple"
          />
          <StatCard
            title="Scraper Jobs"
            value={jobs.length}
            subtitle="Background Tasks"
            icon={Cpu}
            color="emerald"
          />
          <StatCard
            title="Duplicates Filtered"
            value={totalDuplicates}
            subtitle="SHA256 Hash Guard"
            icon={ShieldCheck}
            color="amber"
          />
        </div>

        {/* Tab 1: Overview Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Pipeline Architecture Banner */}
            <div className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-slate-950 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
              <div className="max-w-3xl">
                <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Module 1 Active Foundation</span>
                </span>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  Smartphone Review Data Collection & Web Scraping System
                </h1>
                <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                  Ingests smartphone reviews with strict deduplication, schema validation, ethical delay policies, 
                  and persistent storage in SQLite. Designed as the unyielding data foundation for subsequent 
                  Aspect-Based Sentiment Analysis and Recommendation pipelines.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    onClick={() => setActiveTab('scraper')}
                    className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/25 transition-all"
                  >
                    <span>Launch New Scraper Job</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setActiveTab('reviews')}
                    className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 font-semibold text-xs transition-all"
                  >
                    <span>Browse Collected Reviews</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Smartphone Catalog Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl shadow-2xl">
                <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                  <h3 className="text-base font-bold text-white flex items-center space-x-2">
                    <Smartphone className="w-4 h-4 text-indigo-400" />
                    <span>Active Smartphone Catalog</span>
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">
                    {products.length} Products
                  </span>
                </div>

                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-4 font-semibold">Device Model</th>
                        <th className="py-2.5 px-4 font-semibold">Brand</th>
                        <th className="py-2.5 px-4 font-semibold text-center">Reviews</th>
                        <th className="py-2.5 px-4 font-semibold text-center">Avg Rating</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {products.map((p) => (
                        <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="py-3 px-4 font-medium text-white">{p.name}</td>
                          <td className="py-3 px-4 text-slate-400">{p.brand || '—'}</td>
                          <td className="py-3 px-4 text-center font-mono font-bold text-indigo-400">
                            {p.review_count}
                          </td>
                          <td className="py-3 px-4 text-center font-mono">
                            {p.average_rating ? (
                              <span className="text-amber-400 font-semibold">★ {p.average_rating}</span>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => setActiveTab('reviews')}
                              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                            >
                              Explore
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* System Architecture Roadmap */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl shadow-2xl space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Future Pipeline Roadmap
                </h3>
                <div className="space-y-2.5 text-xs">
                  <div className="p-3 rounded-xl bg-indigo-950/50 border border-indigo-500/40 text-indigo-200 flex items-center justify-between">
                    <div>
                      <strong className="block text-white font-semibold">Module 1: Data Collection & Scraping</strong>
                      <span className="text-[11px] text-indigo-300">SQLite persistence, deduplication, FastAPI</span>
                    </div>
                    <span className="text-[10px] font-bold uppercase bg-indigo-500 text-white px-2 py-0.5 rounded">Active</span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-400">
                    <strong className="text-slate-300 block">Module 2: Text Preprocessing</strong>
                    <span className="text-[11px]">Tokenization, stopword removal, lemmatization</span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-400">
                    <strong className="text-slate-300 block">Module 3: Aspect Extraction</strong>
                    <span className="text-[11px]">Camera, battery, display, performance tags</span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-400">
                    <strong className="text-slate-300 block">Module 4: Aspect Sentiment</strong>
                    <span className="text-[11px]">Polarity classification per aspect</span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800 text-slate-400">
                    <strong className="text-slate-300 block">Modules 5–8: Scoring & Recommendation</strong>
                    <span className="text-[11px]">Comparison, multi-criteria scoring, UI</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Scraper Control Center */}
        {activeTab === 'scraper' && (
          <div className="space-y-6">
            <ScraperLauncher onJobLaunched={handleJobLaunched} />

            {activeJob && (
              <JobTracker
                initialJob={activeJob}
                onJobCompleted={handleJobCompleted}
              />
            )}

            <JobHistory
              jobs={jobs}
              onSelectJob={(job) => setActiveJob(job)}
            />
          </div>
        )}

        {/* Tab 3: Review Explorer */}
        {activeTab === 'reviews' && (
          <div>
            <ReviewExplorer products={products} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SmartReview — Aspect-Based Sentiment Analysis & Recommendation System</span>
          <span className="font-mono text-slate-400">Module 1: Data Collection & Web Scraping System</span>
        </div>
      </footer>
    </div>
  );
}
