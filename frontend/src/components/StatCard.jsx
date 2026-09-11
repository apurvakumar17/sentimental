import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'indigo' }) {
  const colorMap = {
    indigo: 'from-indigo-500/20 to-indigo-900/10 border-indigo-500/30 text-indigo-400 shadow-indigo-500/5',
    emerald: 'from-emerald-500/20 to-emerald-900/10 border-emerald-500/30 text-emerald-400 shadow-emerald-500/5',
    amber: 'from-amber-500/20 to-amber-900/10 border-amber-500/30 text-amber-400 shadow-amber-500/5',
    purple: 'from-purple-500/20 to-purple-900/10 border-purple-500/30 text-purple-400 shadow-purple-500/5',
    rose: 'from-rose-500/20 to-rose-900/10 border-rose-500/30 text-rose-400 shadow-rose-500/5',
  };

  const style = colorMap[color] || colorMap.indigo;

  return (
    <div className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br p-5 shadow-xl backdrop-blur-md transition-all duration-300 hover:scale-[1.01] ${style}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
        </div>
        {Icon && (
          <div className="rounded-xl bg-slate-900/80 p-3 border border-slate-700/50">
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </div>
  );
}
