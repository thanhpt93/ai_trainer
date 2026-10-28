import React from 'react';
import { LucideIcon, Sparkles, Layers, Cpu, LineChart, Boxes, PenTool, CheckCircle, Clock } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  phase: string;
  description: string;
  icon: LucideIcon;
  plannedFeatures: string[];
  architectureNotes: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  phase,
  description,
  icon: Icon,
  plannedFeatures,
  architectureNotes,
}) => {
  return (
    <div className="max-w-4xl mx-auto py-8 space-y-6">
      {/* Header Card */}
      <div className="p-8 rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-800 text-center relative overflow-hidden">
        <div className="absolute top-4 right-4">
          <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-semibold">
            {phase} • Planned Module
          </span>
        </div>

        <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-500/10">
          <Icon className="w-7 h-7" />
        </div>

        <h1 className="text-2xl font-bold text-white tracking-tight">{title}</h1>
        <p className="text-sm text-slate-400 max-w-xl mx-auto mt-2 leading-relaxed">
          {description}
        </p>

        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">
          <Clock className="w-3.5 h-3.5 text-indigo-400" />
          <span>Foundation completed in Phase 1. Implementation scheduled for {phase}.</span>
        </div>
      </div>

      {/* Grid: Planned Capabilities & Architectural Readiness */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Planned Capabilities */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold">Planned Capabilities</h2>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-300">
            {plannedFeatures.map((feat, idx) => (
              <li key={idx} className="flex items-start gap-2.5">
                <CheckCircle className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Backend & Architectural Design */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Layers className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-bold">Architecture Readiness</h2>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {architectureNotes}
          </p>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-400">
            <span>Status: </span>
            <span className="text-amber-400">Extensible adapter interfaces defined in Phase 1</span>
          </div>
        </div>
      </div>
    </div>
  );
};
