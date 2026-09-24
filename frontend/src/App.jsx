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
    <div className="min-h-screen bg-[#030c0e] text-[#f2fbf6] flex flex-col selection:bg-[#2A835F] selection:text-white">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Collected Reviews"
            value={totalReviews}
            subtitle="Validated & Deduplicated"
            icon={Database}
            color="teal"
          />
          <StatCard
            title="Monitored Devices"
            value={products.length}
            subtitle="Smartphone Catalog"
            icon={Smartphone}
            color="green"
          />
          <StatCard
            title="Scraper Jobs"
            value={jobs.length}
            subtitle="Background Tasks"
            icon={Cpu}
            color="lightGreen"
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
            <div className="relative overflow-hidden rounded-2xl border border-[#12544F]/60 bg-gradient-to-r from-[#071b1f] via-[#0d2a2e] to-[#071b1f] p-6 sm:p-7 backdrop-blur-xl shadow-2xl">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                <div className="space-y-1.5 max-w-2xl">
                  <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Smartphone Review Data Collection
                  </h1>
                  <p className="text-sm text-[#7ea698] leading-relaxed">
                    Automated review scraping with 3-tier deduplication, polite rate-limiting, and SQLite persistence.
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => setActiveTab('scraper')}
                    className="group inline-flex items-center space-x-2.5 px-6 py-3.5 rounded-xl bg-gradient-to-r from-[#2A835F] via-[#2A835F] to-[#12544F] hover:from-[#329b71] hover:to-[#186a64] text-white font-bold text-sm shadow-xl shadow-[#2A835F]/25 hover:shadow-[#2A835F]/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
                  >
                    <span>Launch New Scraper Job</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <button
                    onClick={() => setActiveTab('reviews')}
                    className="inline-flex items-center space-x-2 px-4 py-3.5 rounded-xl bg-[#030c0e] border border-[#12544F]/70 hover:bg-[#12544F]/40 hover:text-white text-[#8BBB92] font-semibold text-xs transition-colors"
                  >
                    <span>Browse Reviews</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Smartphone Catalog Summary */}
            <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/90 p-6 backdrop-blur-xl shadow-2xl">
              <div className="flex items-center justify-between pb-4 border-b border-[#12544F]/50">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <Smartphone className="w-4 h-4 text-[#8BBB92]" />
                  <span>Active Smartphone Catalog</span>
                </h3>
                <span className="text-xs text-[#8BBB92] font-medium">
                  {products.length} Products
                </span>
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#030c0e]/95 text-[#8BBB92] border-b border-[#12544F]/50">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Device Model</th>
                      <th className="py-2.5 px-4 font-semibold">Brand</th>
                      <th className="py-2.5 px-4 font-semibold text-center">Reviews</th>
                      <th className="py-2.5 px-4 font-semibold text-center">Avg Rating</th>
                      <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#12544F]/25">
                    {products.map((p) => (
                      <tr key={p.id} className="hover:bg-[#12544F]/20 transition-colors">
                        <td className="py-3 px-4 font-medium text-white">{p.name}</td>
                        <td className="py-3 px-4 text-[#7ea698]">{p.brand || '—'}</td>
                        <td className="py-3 px-4 text-center font-mono font-bold text-[#8BBB92]">
                          {p.review_count}
                        </td>
                        <td className="py-3 px-4 text-center font-mono">
                          {p.average_rating ? (
                            <span className="text-amber-400 font-semibold">★ {p.average_rating}</span>
                          ) : (
                            <span className="text-[#649182]">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setActiveTab('reviews')}
                            className="text-xs text-[#8BBB92] hover:text-white font-medium hover:underline transition-colors"
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
      <footer className="border-t border-[#12544F]/40 bg-[#030c0e] py-6 text-center text-xs text-[#649182]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SmartReview — Aspect-Based Sentiment Analysis & Recommendation System</span>
        </div>
      </footer>
    </div>
  );
}
