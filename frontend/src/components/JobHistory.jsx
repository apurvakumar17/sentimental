import React from 'react';
import { Clock, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function JobHistory({ jobs, onSelectJob }) {
  if (!jobs || jobs.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center backdrop-blur-md">
        <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <p className="text-slate-400 text-sm">No scraping jobs recorded yet</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden backdrop-blur-xl shadow-2xl">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Scraping Job Execution Logs
        </h3>
        <span className="text-xs text-slate-400 font-mono">
          {jobs.length} total runs
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-3 px-4 font-semibold">Job ID</th>
              <th className="py-3 px-4 font-semibold">Target & Product</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold text-center">Pages</th>
              <th className="py-3 px-4 font-semibold text-center">Discovered</th>
              <th className="py-3 px-4 font-semibold text-center">Saved</th>
              <th className="py-3 px-4 font-semibold text-center">Duplicates</th>
              <th className="py-3 px-4 font-semibold">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {jobs.map((job) => {
              const statusBadge = {
                COMPLETED: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60',
                RUNNING: 'bg-indigo-950/60 text-indigo-400 border-indigo-800/60 animate-pulse',
                PENDING: 'bg-amber-950/60 text-amber-400 border-amber-800/60',
                FAILED: 'bg-rose-950/60 text-rose-400 border-rose-800/60',
              }[job.status] || 'bg-slate-800 text-slate-300';

              return (
                <tr
                  key={job.id}
                  onClick={() => onSelectJob && onSelectJob(job)}
                  className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-indigo-400">
                    {job.job_id.slice(0, 8)}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-slate-200 truncate max-w-[200px]">
                      {job.product_name || job.target_url}
                    </div>
                    <div className="text-[10px] text-slate-400 truncate max-w-[200px] font-mono">
                      {job.target_url}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusBadge}`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center font-mono text-slate-300">
                    {job.successful_pages}/{job.pages_attempted}
                  </td>
                  <td className="py-3 px-4 text-center font-mono text-indigo-300 font-bold">
                    {job.reviews_discovered}
                  </td>
                  <td className="py-3 px-4 text-center font-mono text-emerald-400 font-bold">
                    {job.inserted_reviews}
                  </td>
                  <td className="py-3 px-4 text-center font-mono text-amber-400 font-bold">
                    {job.duplicate_reviews}
                  </td>
                  <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                    {new Date(job.created_at).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
