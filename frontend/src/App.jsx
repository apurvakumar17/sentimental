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

        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <div className="relative overflow-hidden rounded-2xl border border-indigo-500/25 bg-gradient-to-r from-slate-900/90 via-indigo-950/40 to-slate-900/90 p-6 sm:p-7 backdrop-blur-xl shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                <div className="space-y-1.5 max-w-2xl">
                  <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Smartphone Review Data Collection
                  </h1>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    Automated review scraping with 3-tier deduplication, polite rate-limiting, and SQLite persistence.
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => setActiveTab('scraper')}
                    className="group inline-flex items-center space-x-2.5 px-6 py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 hover:shadow-indigo-500/50 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
                  >
                    <span>Launch New Scraper Job</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <button
                    onClick={() => setActiveTab('reviews')}
                    className="inline-flex items-center space-x-2 px-4 py-3.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:bg-slate-800 hover:text-white text-slate-300 font-semibold text-xs transition-colors"
                  >
                    <span>Browse Reviews</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Smartphone Catalog Summary */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl shadow-2xl">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <Smartphone className="w-4 h-4 text-indigo-400" />
                  <span>Active Smartphone Catalog</span>
                </h3>
                <span className="text-xs text-slate-400">
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
        </div>
      </footer>
    </div>
  );
}
