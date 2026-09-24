import React from 'react';
import { Clock, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function JobHistory({ jobs, onSelectJob }) {
  if (!jobs || jobs.length === 0) {
    return (
      <div className="rounded-2xl border border-[#12544F]/40 bg-[#071b1f]/50 p-8 text-center backdrop-blur-md">
        <Clock className="w-8 h-8 text-[#649182] mx-auto mb-2" />
        <p className="text-[#649182] text-sm">No scraping jobs recorded yet</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 overflow-hidden backdrop-blur-xl shadow-2xl">
      <div className="p-4 border-b border-[#12544F]/50 flex items-center justify-between">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Scraping Job Execution Logs
        </h3>
        <span className="text-xs text-[#8BBB92]  ">
          {jobs.length} total runs
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#030c0e]/95 text-[#8BBB92] border-b border-[#12544F]/50">
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
          <tbody className="divide-y divide-[#12544F]/25">
            {jobs.map((job) => {
              const statusBadge = {
                COMPLETED: 'bg-[#2A835F]/25 text-[#8BBB92] border-[#2A835F]/60',
                RUNNING: 'bg-[#12544F]/80 text-[#8BBB92] border-[#2A835F] animate-pulse',
                PENDING: 'bg-amber-950/70 text-amber-300 border-amber-700/60',
                FAILED: 'bg-rose-950/70 text-rose-300 border-rose-700/60',
              }[job.status] || 'bg-[#12544F]/40 text-[#7ea698] border-[#12544F]/50';

              return (
                <tr
                  key={job.id}
                  onClick={() => onSelectJob && onSelectJob(job)}
                  className="hover:bg-[#12544F]/20 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4   text-[#8BBB92]">
                    {job.job_id.slice(0, 8)}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-[#f2fbf6] truncate max-w-[200px]">
                      {job.product_name || job.target_url}
                    </div>
                    <div className="text-[10px] text-[#649182] truncate max-w-[200px]  ">
                      {job.target_url}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusBadge}`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center   text-[#f2fbf6]">
                    <div>{job.successful_pages}/{job.pages_attempted}</div>
                    <div className="text-[10px] text-[#649182] font-sans">
                      {job.max_pages ? `Cap: ${job.max_pages}` : 'Unlimited'}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center   text-[#8BBB92] font-bold">
                    {job.reviews_discovered}
                  </td>
                  <td className="py-3 px-4 text-center   text-[#8BBB92] font-bold">
                    {job.inserted_reviews}
                  </td>
                  <td className="py-3 px-4 text-center   text-amber-300 font-bold">
                    {job.duplicate_reviews}
                  </td>
                  <td className="py-3 px-4 text-[#649182] whitespace-nowrap">
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
