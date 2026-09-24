import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'teal' }) {
  const colorMap = {
    teal: {
      card: 'from-teal-600/25 via-[#12544F]/30 to-[#071b1f]/95 border-teal-500/50 shadow-lg shadow-teal-500/10 hover:border-teal-400/80',
      title: 'text-teal-400',
      subtitle: 'text-teal-300/70',
      iconBox: 'bg-teal-950/80 border-teal-500/50 text-teal-300',
      glow: 'bg-teal-400/20',
    },
    green: {
      card: 'from-[#2A835F]/35 via-emerald-900/30 to-[#071b1f]/95 border-emerald-500/50 shadow-lg shadow-emerald-500/10 hover:border-emerald-400/80',
      title: 'text-emerald-400',
      subtitle: 'text-emerald-300/70',
      iconBox: 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300',
      glow: 'bg-emerald-400/20',
    },
    lightGreen: {
      card: 'from-[#8BBB92]/30 via-[#12544F]/30 to-[#071b1f]/95 border-[#8BBB92]/50 shadow-lg shadow-[#8BBB92]/10 hover:border-[#8BBB92]/80',
      title: 'text-[#8BBB92]',
      subtitle: 'text-[#8BBB92]/70',
      iconBox: 'bg-[#0d3430]/80 border-[#8BBB92]/50 text-[#8BBB92]',
      glow: 'bg-[#8BBB92]/20',
    },
    amber: {
      card: 'from-amber-500/25 via-amber-950/30 to-[#071b1f]/95 border-amber-500/50 shadow-lg shadow-amber-500/10 hover:border-amber-400/80',
      title: 'text-amber-400',
      subtitle: 'text-amber-300/70',
      iconBox: 'bg-amber-950/80 border-amber-500/50 text-amber-300',
      glow: 'bg-amber-400/20',
    },
  };

  colorMap.indigo = colorMap.teal;
  colorMap.emerald = colorMap.green;
  colorMap.purple = colorMap.lightGreen;

  const conf = colorMap[color] || colorMap.teal;

  return (
    <div className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br p-5 shadow-xl backdrop-blur-md transition-all duration-300 hover:scale-[1.01] ${conf.card}`}>
      {/* Corner ambient glow */}
      <div className={`absolute -right-6 -top-6 w-28 h-28 rounded-full blur-2xl pointer-events-none ${conf.glow}`} />

      <div className="relative flex items-center justify-between">
        <div>
          <p className={`text-xs font-bold uppercase tracking-wider ${conf.title}`}>{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{value}</p>
          {subtitle && <p className={`mt-1 text-xs font-medium ${conf.subtitle}`}>{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`rounded-xl p-3 border shadow-inner ${conf.iconBox}`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </div>
  );
}
