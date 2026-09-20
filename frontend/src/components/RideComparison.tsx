import React, { useState } from 'react';
import {
  Zap, ArrowUpRight, TrendingUp, Info, ShieldCheck, ChevronDown, ChevronUp,
  AlertCircle, Trophy, Compass, Wallet, Sparkles, Layers,
  AlertTriangle
} from 'lucide-react';
import type { RideProviderDetails, ComparisonResult } from '../../../backend/src/services/types';

interface RideComparisonProps {
  comparison: ComparisonResult;
  onBooking: (providerName: string, fare: number) => void;
}

export const RideComparison: React.FC<RideComparisonProps> = ({ comparison, onBooking }) => {
  const {
    providers, recommendations, insights, detectedCity, surgeRuleName,
    straightLineDistance, detourDistance, pricingRegime, fareSpread, spreadPercentage, anomalyCount
  } = comparison;

  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'smart' | 'price' | 'eta'>('smart');

  const toggleExpand = (providerName: string) => {
    setExpandedProvider(prev => prev === providerName ? null : providerName);
  };

  // Sorting
  const sortedProviders = [...providers].sort((a, b) => {
    if (sortBy === 'smart') {
      return (b.smartScore || b.efficiencyScore) - (a.smartScore || a.efficiencyScore);
    } else if (sortBy === 'price') {
      return (a.actualFare || a.estimatedFare) - (b.actualFare || b.estimatedFare);
    } else {
      return a.etaMinutes - b.etaMinutes;
    }
  });

  const getProviderIcon = (name: string) => {
    const lowercaseName = name.toLowerCase();
    if (lowercaseName.includes('uber')) {
      return (
        <div className="w-10 h-10 bg-slate-950 text-white rounded-xl flex flex-col items-center justify-center font-black text-base border border-slate-800 shadow shrink-0 select-none">
          U
          <span className="text-[6px] font-bold uppercase tracking-wider text-slate-400 -mt-1">Ride</span>
        </div>
      );
    }
    if (lowercaseName.includes('ola')) {
      return (
        <div className="w-10 h-10 bg-lime-400 text-slate-950 rounded-xl flex flex-col items-center justify-center font-black text-base border border-lime-500 shadow shrink-0 select-none">
          O
          <span className="text-[6px] font-bold uppercase tracking-wider text-slate-700 -mt-1">Cabs</span>
        </div>
      );
    }
    if (lowercaseName.includes('rapido')) {
      return (
        <div className="w-10 h-10 bg-amber-400 text-slate-900 rounded-xl flex flex-col items-center justify-center font-black text-sm italic border border-amber-500 shadow shrink-0 select-none">
          R
          <span className="text-[5px] font-bold uppercase tracking-wider text-slate-700 -mt-1">Fast</span>
        </div>
      );
    }
    return (
      <div className="w-10 h-10 bg-gradient-to-b from-yellow-400 to-black text-white rounded-xl flex flex-col items-center justify-center font-black border border-slate-700 shadow shrink-0 select-none">
        <span className="text-yellow-400 text-[8px] tracking-tight font-extrabold uppercase leading-none">TAXI</span>
        <span className="text-white text-[7px] font-bold lowercase tracking-wider leading-none">local</span>
      </div>
    );
  };

  const handleBook = (p: RideProviderDetails) => {
    onBooking(p.provider, p.actualFare || p.estimatedFare);
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const destinationUrl = isMobile ? p.appDeepLink : p.webLink;
    window.open(destinationUrl, '_blank', 'noopener,noreferrer');
  };

  const recommendedProvider = providers.find(p => p.provider === recommendations.mostEfficient) || providers[0];
  const cheapestProvider = providers.find(p => p.isCheapest) || providers[0];

  return (
    <div className="space-y-6">

      {/* 1. SMART INSIGHT BANNER */}
      <div className="p-5 bg-gradient-to-r from-indigo-900/90 via-indigo-950 to-slate-900 text-white rounded-2xl border border-indigo-500/30 shadow-xl shadow-indigo-950/20 relative overflow-hidden">
        <div className="absolute -right-6 -bottom-6 w-36 h-36 bg-indigo-500/10 rounded-full filter blur-2xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                <Sparkles size={11} className="text-amber-300" /> ML Fare Intelligence
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                <Layers size={10} /> {pricingRegime || 'Standard Pricing'}
              </span>
            </div>
            <h3 className="text-lg font-black text-white flex items-center gap-2 pt-1">
              <span>{cheapestProvider?.provider} has the lowest current fare</span>
              <span className="text-amber-400 font-extrabold">₹{cheapestProvider?.actualFare || cheapestProvider?.estimatedFare}</span>
            </h3>
            <p className="text-xs text-indigo-200/80 font-medium">
              Save up to <strong className="text-emerald-400">₹{fareSpread || 0} ({spreadPercentage || 0}%)</strong> across available options in {detectedCity}. Top ranked option: <strong className="text-white">{recommendedProvider?.provider}</strong> ({recommendedProvider?.smartScore || recommendedProvider?.efficiencyScore}/100 smart score).
            </p>
          </div>

          {anomalyCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/20 border border-amber-500/40 rounded-xl text-amber-200 text-xs font-bold animate-pulse">
              <AlertTriangle size={16} className="text-amber-400 shrink-0" />
              <span>{anomalyCount} Unusual Fare Spike Detected</span>
            </div>
          )}
        </div>
      </div>

      {/* 2. Route Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl shadow-sm">
        <div className="space-y-0.5">
          <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] tracking-wider block">Road Distance</span>
          <h4 className="text-sm font-black text-[var(--text-primary)] flex items-center gap-1">
            <Compass size={14} className="text-indigo-500" />
            {comparison.distanceKm.toFixed(1)} km
          </h4>
        </div>
        <div className="space-y-0.5">
          <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] tracking-wider block">Detour Distance</span>
          <h4 className="text-sm font-black text-[var(--text-primary)] flex items-center gap-1" title={`Direct straight-line distance is ${straightLineDistance.toFixed(1)} km`}>
            <TrendingUp size={14} className="text-amber-500" />
            {detourDistance.toFixed(1)} km
          </h4>
        </div>
        <div className="space-y-0.5">
          <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] tracking-wider block">Fare Spread</span>
          <h4 className="text-sm font-black text-[var(--text-primary)] flex items-center gap-1">
            <Wallet size={14} className="text-emerald-500" />
            ₹{fareSpread || 0} variance
          </h4>
        </div>
        <div className="space-y-0.5">
          <span className="text-[9px] uppercase font-bold text-[var(--text-secondary)] tracking-wider block">Active Surge</span>
          <h4 className="text-sm font-black text-[var(--text-primary)] flex items-center gap-1">
            <Zap size={14} className={surgeRuleName !== 'Standard' ? 'text-amber-500 animate-pulse' : 'text-slate-400'} />
            {surgeRuleName !== 'Standard' ? surgeRuleName : 'None'}
          </h4>
        </div>
      </div>

      {/* 3. Ranked Comparison Table */}
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl overflow-hidden shadow-sm">
        {/* Toolbar */}
        <div className="px-5 py-4 border-b border-[var(--border-color)] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[var(--bg-primary)]/20">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-extrabold text-sm text-[var(--text-primary)]">Real-Time Fare Comparison & ML Intelligence</h3>
              <span className="px-2 py-0.5 rounded text-[9px] font-extrabold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                Transparent ML Scoring
              </span>
            </div>
            <p className="text-[10px] text-[var(--text-secondary)] font-medium">
              Comparing live provider quotes with ML expected estimates and anomaly boundaries.
            </p>
          </div>

          {/* Sorting controls */}
          <div className="flex bg-[var(--bg-primary)] border border-[var(--border-color)] p-1 rounded-xl text-[10px] font-bold text-[var(--text-secondary)] self-stretch sm:self-auto justify-center">
            <button
              onClick={() => setSortBy('smart')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${sortBy === 'smart' ? 'bg-[var(--bg-secondary)] text-indigo-600 dark:text-indigo-400 shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
            >
              Smart Rank
            </button>
            <button
              onClick={() => setSortBy('price')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${sortBy === 'price' ? 'bg-[var(--bg-secondary)] text-indigo-600 dark:text-indigo-400 shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
            >
              Cheapest
            </button>
            <button
              onClick={() => setSortBy('eta')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${sortBy === 'eta' ? 'bg-[var(--bg-secondary)] text-indigo-600 dark:text-indigo-400 shadow-sm' : 'hover:text-[var(--text-primary)]'}`}
            >
              Fastest ETA
            </button>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[720px]">
            <thead>
              <tr className="border-b border-[var(--border-color)] text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider bg-[var(--bg-primary)]/40">
                <th className="py-3.5 pl-5 w-16 text-center">Rank</th>
                <th className="py-3.5">Provider & Type</th>
                <th className="py-3.5">Actual Provider Fare</th>
                <th className="py-3.5">ML Estimated Fare</th>
                <th className="py-3.5">Prediction Delta</th>
                <th className="py-3.5">ETA & Confidence</th>
                <th className="py-3.5 text-center">Smart Score</th>
                <th className="py-3.5 pr-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)] font-medium text-[var(--text-primary)]">
              {sortedProviders.map((p, idx) => {
                const rank = idx + 1;
                const isExpanded = expandedProvider === p.provider;
                const actualFare = p.actualFare || p.estimatedFare;
                const predFare = p.predictedFare || actualFare;
                const diff = p.predictionDiff !== undefined ? p.predictionDiff : (actualFare - predFare);
                const confScore = p.confidenceScore || 90;

                // Highlight Badge
                let rowBadge = null;
                if (p.isCheapest) {
                  rowBadge = <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[8px] font-bold bg-yellow-400 text-slate-950 border border-yellow-500">💰 Cheapest</span>;
                } else if (p.isFastest) {
                  rowBadge = <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[8px] font-bold bg-blue-500 text-white border border-blue-600">⚡ Fastest</span>;
                } else if (p.isBestValue) {
                  rowBadge = <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[8px] font-bold bg-indigo-600 text-white border border-indigo-700">🏆 Best Choice</span>;
                }

                return (
                  <React.Fragment key={p.provider}>
                    <tr className={`hover:bg-[var(--bg-primary)]/30 transition-all ${p.isBestValue ? 'bg-indigo-500/5 dark:bg-indigo-950/20' : ''}`}>
                      {/* Rank Column */}
                      <td className="py-4 pl-5 text-center font-black text-sm">
                        {p.isBestValue ? (
                          <div className="flex justify-center text-indigo-500"><Trophy size={16} /></div>
                        ) : (
                          `#${rank}`
                        )}
                      </td>

                      {/* Provider Column */}
                      <td className="py-4">
                        <div className="flex items-center gap-3">
                          {getProviderIcon(p.provider)}
                          <div className="flex flex-col">
                            <span className="font-black text-sm flex items-center gap-1.5">
                              {p.provider}
                              {p.isAnomaly && (
                                <span className="px-1.5 py-0.5 rounded text-[7px] font-bold bg-amber-500 text-slate-950 border border-amber-600 flex items-center gap-0.5" title={p.anomalyReason}>
                                  <AlertTriangle size={8} /> Anomaly
                                </span>
                              )}
                            </span>
                            <div className="flex items-center gap-1.5 text-[9px] text-[var(--text-secondary)] font-bold">
                              <span className="uppercase tracking-wider">{p.vehicleType}</span>
                              <span>•</span>
                              <span>{p.clusterLabel || 'Standard'}</span>
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Actual Provider Fare */}
                      <td className="py-4">
                        <div className="flex flex-col">
                          <span className="text-[var(--text-primary)] font-black text-base flex items-baseline gap-1">
                            ₹{actualFare}
                            <span className="text-[8px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/60 px-1 py-0.2 rounded border border-emerald-300 dark:border-emerald-800">
                              Actual
                            </span>
                          </span>
                          <span className="text-[8px] text-[var(--text-secondary)] font-bold">
                            ₹{p.costPerKm}/km • ₹{p.costPerMin}/min
                          </span>
                        </div>
                      </td>

                      {/* ML Estimated Fare */}
                      <td className="py-4">
                        <div className="flex flex-col">
                          <span className="text-indigo-600 dark:text-indigo-400 font-extrabold text-sm flex items-baseline gap-1">
                            ₹{predFare}
                            <span className="text-[8px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300 bg-indigo-100 dark:bg-indigo-950/60 px-1 py-0.2 rounded border border-indigo-300 dark:border-indigo-800">
                              ML Estimate
                            </span>
                          </span>
                          <span className="text-[8px] text-[var(--text-secondary)] font-medium">
                            Gradient Boosting Regressor
                          </span>
                        </div>
                      </td>

                      {/* Prediction Delta */}
                      <td className="py-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          Math.abs(diff) < 15
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : diff > 0
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-300'
                        }`}>
                          {diff >= 0 ? `+₹${diff}` : `-₹${Math.abs(diff)}`}
                          <span className="text-[8px] opacity-80">({p.predictionDiffPct || 0}%)</span>
                        </span>
                      </td>

                      {/* ETA & Confidence */}
                      <td className="py-4">
                        <div className="flex flex-col">
                          <strong className="text-[var(--text-primary)] font-extrabold text-xs">
                            {p.etaMinutes} mins
                          </strong>
                          <span className="text-[9px] font-bold text-slate-500 flex items-center gap-1">
                            <ShieldCheck size={10} className={confScore >= 80 ? 'text-emerald-500' : 'text-amber-500'} />
                            Confidence: {confScore}% ({p.confidenceLevel || p.confidence})
                          </span>
                        </div>
                      </td>

                      {/* Smart Score */}
                      <td className="py-4 text-center">
                        <div className="flex flex-col items-center">
                          <span className={`text-sm font-black ${p.isBestValue ? 'text-indigo-600 dark:text-indigo-400' : 'text-[var(--text-primary)]'}`}>
                            {p.smartScore || p.efficiencyScore}
                            <span className="text-[9px] text-[var(--text-secondary)]">/100</span>
                          </span>
                          {rowBadge && <div className="mt-1">{rowBadge}</div>}
                        </div>
                      </td>

                      {/* Action */}
                      <td className="py-4 pr-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => toggleExpand(p.provider)}
                            className="p-1.5 hover:bg-[var(--bg-primary)] border border-transparent hover:border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-lg transition-colors cursor-pointer"
                            title="Fare breakdown & ML details"
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                          <button
                            onClick={() => handleBook(p)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 font-bold text-xs tracking-wide rounded-xl shadow-sm transition-all hover:scale-102 cursor-pointer ${
                              p.isBestValue
                                ? 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white shadow-md shadow-indigo-600/10'
                                : 'bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white'
                            }`}
                          >
                            <span>Book</span>
                            <ArrowUpRight size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Breakdown Drawer */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} className="bg-[var(--bg-primary)]/70 p-5 border-b border-[var(--border-color)] animate-fade-in">
                          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-semibold text-[var(--text-secondary)]">
                            
                            {/* Fare Breakdown */}
                            <div className="space-y-1.5 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
                              <span className="text-[8px] uppercase font-extrabold tracking-wider block text-indigo-600 dark:text-indigo-400">
                                🧾 Fare Decomposition
                              </span>
                              <div className="space-y-1 text-[11px]">
                                <div className="flex justify-between">
                                  <span>Base Fare:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.baseFare}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Distance Rate:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.distanceFare}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Time Duration:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.durationFare}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Platform Fee:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.platformFee}</strong>
                                </div>
                              </div>
                            </div>

                            {/* Volatilities & Toll */}
                            <div className="space-y-1.5 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
                              <span className="text-[8px] uppercase font-extrabold tracking-wider block text-amber-600 dark:text-amber-400">
                                ⚡ Demand & Toll Factors
                              </span>
                              <div className="space-y-1 text-[11px]">
                                <div className="flex justify-between">
                                  <span>Surge Multiplier:</span>
                                  <strong className="text-[var(--text-primary)]">{p.surgeMultiplier > 1.0 ? `${p.surgeMultiplier}x` : '1.0x (Standard)'}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Airport Toll:</span>
                                  <strong className="text-[var(--text-primary)]">{p.tollEstimate > 0 ? `₹${p.tollEstimate}` : 'None'}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Cost per Km:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.costPerKm}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Cost per Min:</span>
                                  <strong className="text-[var(--text-primary)]">₹{p.costPerMin}</strong>
                                </div>
                              </div>
                            </div>

                            {/* ML Diagnostic */}
                            <div className="space-y-1.5 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
                              <span className="text-[8px] uppercase font-extrabold tracking-wider block text-emerald-600 dark:text-emerald-400">
                                🧠 ML Pricing Intelligence
                              </span>
                              <div className="space-y-1 text-[11px]">
                                <div className="flex justify-between">
                                  <span>Discovered Regime:</span>
                                  <strong className="text-[var(--text-primary)]">{p.clusterLabel || 'Standard'}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>ML Expected Fare:</span>
                                  <strong className="text-indigo-600 dark:text-indigo-400">₹{predFare}</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Anomaly Status:</span>
                                  <strong className={p.isAnomaly ? 'text-amber-500' : 'text-emerald-500'}>
                                    {p.isAnomaly ? 'Flagged Outlier' : 'Standard Envelope'}
                                  </strong>
                                </div>
                                {p.isAnomaly && (
                                  <p className="text-[9px] text-amber-600 dark:text-amber-400 pt-1 leading-tight">
                                    {p.anomalyReason}
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Transparent Score Breakdown */}
                            <div className="space-y-1.5 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
                              <span className="text-[8px] uppercase font-extrabold tracking-wider block text-purple-600 dark:text-purple-400">
                                ⚖️ Multi-Factor Score (100)
                              </span>
                              <div className="space-y-1 text-[11px]">
                                <div className="flex justify-between">
                                  <span>Price Score (40%):</span>
                                  <strong className="text-[var(--text-primary)]">{p.scoreBreakdown?.priceScore || Math.round(p.efficiencyScore * 0.4)}/40</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>ETA Score (30%):</span>
                                  <strong className="text-[var(--text-primary)]">{p.scoreBreakdown?.etaScore || Math.round(p.efficiencyScore * 0.3)}/30</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Confidence (15%):</span>
                                  <strong className="text-[var(--text-primary)]">{p.scoreBreakdown?.confidenceScore || 14}/15</strong>
                                </div>
                                <div className="flex justify-between">
                                  <span>Reliability (15%):</span>
                                  <strong className="text-[var(--text-primary)]">{p.scoreBreakdown?.reliabilityScore || 14}/15</strong>
                                </div>
                              </div>
                            </div>

                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. AI Travel Advisory Insights */}
      {insights && insights.length > 0 && (
        <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-2">
          <h4 className="text-[10px] uppercase font-bold text-indigo-900 dark:text-indigo-300 tracking-wider flex items-center gap-1.5">
            <Sparkles size={12} className="text-amber-500" /> AI Route Insights & Advisory
          </h4>
          <ul className="space-y-1.5">
            {insights.map((insight, idx) => (
              <li key={idx} className="flex gap-2 items-start text-xs font-semibold text-[var(--text-primary)]">
                <span className="p-0.5 bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 rounded mt-0.5 shrink-0">
                  <Info size={11} />
                </span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 5. Academic & Integrity Disclaimer */}
      <div className="p-4 bg-amber-500/5 border border-amber-500/10 rounded-2xl flex gap-3 items-start text-xs font-semibold text-[var(--text-secondary)] italic">
        <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
        <span>
          Data Integrity Notice: "Actual Provider Fare" represents the ground-truth provider quote. "ML Estimated Fare" is generated by supervised regression for analytical comparison. K-Means clustering is utilized for unsupervised pricing pattern discovery.
        </span>
      </div>

    </div>
  );
};

export default RideComparison;
