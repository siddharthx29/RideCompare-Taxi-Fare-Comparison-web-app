import React, { useState } from 'react';
import { Info, X, Zap, ShieldAlert, Sparkles, Activity, Clock, MapPin } from 'lucide-react';
import type { RideProviderDetails, MarketConditionItem } from '../types/ride';

interface DemandBadgeProps {
  provider: RideProviderDetails;
  compact?: boolean;
}

export const getDemandConfig = (level?: string, score?: number) => {
  const norm = (level || '').toUpperCase().trim();
  if (norm.includes('VERY HIGH') || (score !== undefined && score >= 3.5)) {
    return {
      label: 'VERY HIGH',
      displayLabel: 'Very high demand',
      shortLabel: 'VERY HIGH',
      colorDot: 'bg-rose-500',
      badgeClass: 'text-rose-400 bg-rose-500/15 border-rose-500/30',
      iconClass: 'text-rose-500',
      description: 'Very high demand conditions detected across this zone.',
      emoji: '🔴',
      barPercent: 95
    };
  }
  if (norm.includes('HIGH') || (score !== undefined && score >= 2.5)) {
    return {
      label: 'HIGH',
      displayLabel: 'High demand',
      shortLabel: 'HIGH',
      colorDot: 'bg-red-500',
      badgeClass: 'text-red-400 bg-red-500/15 border-red-500/30',
      iconClass: 'text-red-500',
      description: 'High demand conditions detected. Pricing may be elevated.',
      emoji: '🔴',
      barPercent: 75
    };
  }
  if (norm.includes('SLIGHTLY HIGH') || norm.includes('MODERATE') || (score !== undefined && score >= 1.5)) {
    return {
      label: 'SLIGHTLY HIGH',
      displayLabel: 'Slightly high demand',
      shortLabel: 'SLIGHTLY HIGH',
      colorDot: 'bg-amber-500',
      badgeClass: 'text-amber-400 bg-amber-500/15 border-amber-500/30',
      iconClass: 'text-amber-500',
      description: 'Moderate demand detected. Pricing may be slightly elevated.',
      emoji: '🟠',
      barPercent: 50
    };
  }
  if (norm.includes('LOW') || (score !== undefined && score < 0.5)) {
    return {
      label: 'LOW',
      displayLabel: 'Low demand',
      shortLabel: 'LOW',
      colorDot: 'bg-sky-400',
      badgeClass: 'text-sky-400 bg-sky-500/15 border-sky-500/30',
      iconClass: 'text-sky-400',
      description: 'Low demand conditions detected. Pricing likely at baseline.',
      emoji: '🟡',
      barPercent: 15
    };
  }
  // Default NORMAL
  return {
    label: 'NORMAL',
    displayLabel: 'Normal demand',
    shortLabel: 'NORMAL',
    colorDot: 'bg-emerald-500',
    badgeClass: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30',
    iconClass: 'text-emerald-500',
    description: 'Demand currently appears normal. Standard market conditions.',
    emoji: '🟢',
    barPercent: 28
  };
};

export const DemandIntelligenceBadge: React.FC<DemandBadgeProps> = ({ provider, compact = false }) => {
  const [showModal, setShowModal] = useState(false);

  const level = provider.demand_level || provider.demandLevel || 'NORMAL';
  const score = provider.pricing_pressure_score ?? provider.pricingPressureScore ?? 1.0;
  const cfg = getDemandConfig(level, score);

  const confidence = provider.confidence_text || (provider.confidence ? `${Math.round(provider.confidence * 100)}% confidence` : '80% confidence');
  const isLimited = confidence.toLowerCase().includes('limited') || (provider.confidence !== undefined && provider.confidence < 0.5);
  const reason = provider.reason || provider.demandReason || 'Standard market demand for this zone and hour.';
  const sourceType = provider.source_type || provider.sourceType || 'ml_estimate';
  const zone = provider.pickup_zone || provider.pickupZone || 'H3 Geographic Zone';

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowModal(true);
  };

  return (
    <>
      <div
        onClick={handleClick}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98] ${cfg.badgeClass}`}
        title="Click to view RideCompare Pricing Pressure & Demand Intelligence explanation"
      >
        <span className={`w-2 h-2 rounded-full ${cfg.colorDot} animate-pulse shrink-0`} />
        <span className="text-[11px] font-bold tracking-tight">
          {cfg.displayLabel}
        </span>
        <span className="text-[10px] opacity-75 font-semibold hidden xs:inline">
          • Pricing pressure: {cfg.shortLabel}
        </span>
        <span className="text-[10px] font-semibold text-slate-300 dark:text-slate-400 ml-0.5">
          ({isLimited ? 'Limited data' : confidence})
        </span>
        <Info size={11} className="opacity-60 ml-0.5" />
      </div>

      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fade-in"
          onClick={(e) => {
            e.stopPropagation();
            setShowModal(false);
          }}
        >
          <div
            className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-5 text-white shadow-2xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xl">{cfg.emoji}</span>
                <div>
                  <h3 className="font-extrabold text-base text-white">
                    {provider.provider} — Pricing Pressure
                  </h3>
                  <span className="text-xs text-slate-400 font-medium">
                    RideCompare Independent Demand Intelligence
                  </span>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Standardized Pricing Pressure Scale Meter */}
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-300">Standardized Scale:</span>
                <span className="font-extrabold text-indigo-400">
                  {score.toFixed(1)} / 4.0 ({cfg.label})
                </span>
              </div>
              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden relative">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-500"
                  style={{ width: `${cfg.barPercent}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] font-bold text-slate-400">
                <span>0: LOW</span>
                <span>1: NORMAL</span>
                <span>2: SLIGHTLY HIGH</span>
                <span>3: HIGH</span>
                <span>4: VERY HIGH</span>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-start gap-2">
                <Activity size={14} className="text-indigo-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-bold text-slate-200 block">Condition Detected</span>
                  <p className="text-slate-300 text-[11px] mt-0.5">
                    {cfg.description}
                  </p>
                  <p className="text-slate-400 text-[11px] mt-1 italic">
                    Reason: {reason}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-semibold block">Confidence Level</span>
                  <span className="font-extrabold text-white">
                    {isLimited ? 'Limited data' : confidence}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-semibold block">Source Layer</span>
                  <span className="font-extrabold text-white capitalize">
                    {sourceType.replace('_', ' ')}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-semibold block">Geographic Zone</span>
                  <span className="font-mono text-[10px] text-indigo-300 truncate block">
                    {zone}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-semibold block">Pricing Impact</span>
                  <span className="font-extrabold text-emerald-400">
                    No fabricated exact prices
                  </span>
                </div>
              </div>
            </div>

            {/* Mandatory Disclaimers per user specification */}
            <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-800/50 text-[11px] space-y-1.5 text-indigo-200/90 leading-relaxed">
              <div className="flex items-center gap-1.5 font-bold text-indigo-300">
                <ShieldAlert size={13} className="text-indigo-400" />
                <span>Transparent Methodology Note</span>
              </div>
              <p>
                RideCompare estimates pricing pressure using available real-time, historical, geographic and traffic signals. This does not represent the provider's proprietary surge multiplier.
              </p>
              {isLimited && (
                <p className="text-amber-300 font-medium">
                  ⚠️ Limited real-time data is available for this provider. This estimate may be less accurate.
                </p>
              )}
            </div>

            <button
              onClick={() => setShowModal(false)}
              className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs transition-colors cursor-pointer"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export const MarketConditionsSummaryBar: React.FC<{
  providers: RideProviderDetails[];
  marketConditions?: MarketConditionItem[];
  pickupZone?: string;
}> = ({ providers, marketConditions, pickupZone }) => {
  // Extract distinct providers and their demand levels
  const list = marketConditions && marketConditions.length > 0
    ? marketConditions
    : providers.map(p => ({
        provider: p.provider,
        demand_level: p.demand_level || p.demandLevel || 'NORMAL',
        pricing_pressure: p.pricing_pressure || p.pricingPressure || 'NORMAL',
        confidence: p.confidence || 0.8,
        confidence_text: p.confidence_text || '80% confidence',
        reason: p.reason || p.demandReason
      }));

  if (list.length === 0) return null;

  return (
    <div className="p-3.5 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white border border-indigo-900/60 shadow-md space-y-2.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-800/40 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-black uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
            <Activity size={13} className="text-indigo-400 animate-pulse" />
            RideCompare Market Conditions
          </span>
          {pickupZone && (
            <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10 hidden sm:inline">
              Zone: {pickupZone}
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-300 font-medium">
          Independent real-time pricing pressure indicators
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
        {list.slice(0, 4).map((item, idx) => {
          const cfg = getDemandConfig(item.demand_level);
          return (
            <div
              key={`${item.provider}-${idx}`}
              className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/10 text-xs font-semibold"
            >
              <span className="text-slate-200 font-bold truncate max-w-[130px]">
                {item.provider}
              </span>
              <div className="flex items-center gap-1.5">
                <span>{cfg.emoji}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${cfg.badgeClass}`}>
                  {cfg.shortLabel}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-[10px] text-slate-400 text-center sm:text-left flex items-center justify-between pt-1">
        <span>Demand indicators are RideCompare estimates based on available market signals.</span>
        <span className="hidden sm:inline text-indigo-400 font-medium">Click any indicator for details</span>
      </div>
    </div>
  );
};
