import React, { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, XCircle, AlertTriangle, FileText, Copy, Database, ShieldAlert } from 'lucide-react';
import { api } from '../api/client';

export default function JobTracker({ initialJob, onJobCompleted }) {
  const [job, setJob] = useState(initialJob);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    setJob(initialJob);
  }, [initialJob]);

  useEffect(() => {
    if (!job?.job_id) return;
    if (job.status === 'COMPLETED' || job.status === 'FAILED') return;

    setIsPolling(true);
    const interval = setInterval(async () => {
      try {
        const updated = await api.getJob(job.job_id);
        setJob(updated);
        if (updated.status === 'COMPLETED' || updated.status === 'FAILED') {
          clearInterval(interval);
          setIsPolling(false);
          if (onJobCompleted) onJobCompleted(updated);
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [job?.job_id, job?.status]);

  if (!job) return null;

  const statusColors = {
    PENDING: 'bg-amber-950/70 text-amber-300 border-amber-700/60',
    RUNNING: 'bg-[#12544F]/80 text-[#8BBB92] border-[#2A835F] shadow-sm shadow-[#2A835F]/20',
    COMPLETED: 'bg-[#2A835F]/30 text-[#8BBB92] border-[#2A835F]/70',
    FAILED: 'bg-rose-950/70 text-rose-300 border-rose-700/60',
  };

  const statusIcons = {
    PENDING: RefreshCw,
    RUNNING: RefreshCw,
    COMPLETED: CheckCircle,
    FAILED: XCircle,
  };

  const StatusIcon = statusIcons[job.status] || AlertTriangle;

  return (
    <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-6 backdrop-blur-xl shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#12544F]/50">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-white">Job Monitor</h3>
            <span className="   text-xs px-2 py-0.5 rounded bg-[#030c0e] text-[#8BBB92] border border-[#12544F]/70">
              {job.job_id.slice(0, 8)}...
            </span>
          </div>
          <p className="text-xs text-[#7ea698] mt-0.5">
            Target: <span className="text-[#8BBB92]   ">{job.target_url}</span>
            {job.product_name && ` (${job.product_name})`}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusColors[job.status]}`}>
            <StatusIcon className={`w-3.5 h-3.5 ${job.status === 'RUNNING' ? 'animate-spin' : ''}`} />
            <span>{job.status}</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
        <div className="p-3.5 rounded-xl bg-[#030c0e] border border-[#12544F]/60">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#7ea698]">Pages Processed</span>
            {job.max_pages === null || job.max_pages === undefined ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#12544F] border border-[#2A835F]/60 text-[#8BBB92]   ">
                Unlimited
              </span>
            ) : (
              <span className="text-[10px] text-[#649182]   ">
                Cap: {job.max_pages}
              </span>
            )}
          </div>
          <p className="text-xl font-bold text-white mt-1   ">
            {job.successful_pages} <span className="text-xs text-[#649182]">/ {job.pages_attempted}</span>
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#030c0e] border border-[#12544F]/60">
          <span className="text-xs text-[#7ea698]">Reviews Found</span>
          <p className="text-xl font-bold text-[#8BBB92] mt-1   ">
            {job.reviews_discovered}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#030c0e] border border-[#12544F]/60">
          <span className="text-xs text-[#7ea698]">New Saved</span>
          <p className="text-xl font-bold text-[#8BBB92] mt-1   ">
            {job.inserted_reviews}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#030c0e] border border-[#12544F]/60">
          <span className="text-xs text-[#7ea698]">Duplicates Filtered</span>
          <p className="text-xl font-bold text-amber-300 mt-1   ">
            {job.duplicate_reviews}
          </p>
        </div>
      </div>

      {job.error_log && (
        <div className="mt-4 p-3 rounded-xl bg-rose-950/40 border border-rose-700/60 text-rose-300 text-xs flex items-start space-x-2">
          <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <pre className="   text-xs whitespace-pre-wrap">{job.error_log}</pre>
        </div>
      )}
    </div>
  );
}
