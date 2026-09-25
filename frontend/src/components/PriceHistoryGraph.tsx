import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

interface PriceHistoryGraphProps {
  providers: any[];
  routeHash?: string;
}

export const PriceHistoryGraph: React.FC<PriceHistoryGraphProps> = ({ providers }) => {
  // Collect history series from providers
  const providersWithHistory = providers.filter(p => p.volatility && p.volatility.recent_history && p.volatility.recent_history.length > 0);

  if (providersWithHistory.length === 0) {
    return null;
  }

  // Find min and max for scaling
  let allFares: number[] = [];
  providersWithHistory.forEach(p => {
    allFares = allFares.concat(p.volatility.recent_history);
  });

  const minFare = Math.max(0, Math.min(...allFares) * 0.9);
  const maxFare = Math.max(...allFares) * 1.1 || 100;
  const range = maxFare - minFare || 1;

  const svgWidth = 460;
  const svgHeight = 120;
  const paddingX = 35;
  const paddingY = 20;
  const plotWidth = svgWidth - paddingX * 2;
  const plotHeight = svgHeight - paddingY * 2;

  const getProviderStroke = (name: string) => {
    const l = name.toLowerCase();
    if (l.includes('uber')) return '#6366f1';
    if (l.includes('ola')) return '#10b981';
    if (l.includes('rapido')) return '#f59e0b';
    return '#8b5cf6';
  };

  return (
    <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
            <Activity size={14} />
          </div>
          <div>
            <h5 className="font-bold text-xs text-[var(--text-primary)]">
              Live Observed Price Movement & Volatility
            </h5>
            <span className="text-[10px] text-[var(--text-secondary)] font-medium">
              Observed fare fluctuations over recent searches for this corridor.
            </span>
          </div>
        </div>
      </div>

      {/* SVG Sparkline Chart */}
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-28 select-none">
          {/* Grid lines */}
          <line x1={paddingX} y1={paddingY} x2={svgWidth - paddingX} y2={paddingY} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
          <line x1={paddingX} y1={paddingY + plotHeight / 2} x2={svgWidth - paddingX} y2={paddingY + plotHeight / 2} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
          <line x1={paddingX} y1={paddingY + plotHeight} x2={svgWidth - paddingX} y2={paddingY + plotHeight} stroke="currentColor" strokeOpacity={0.1} />

          {/* Y Axis Labels */}
          <text x={paddingX - 6} y={paddingY + 4} textAnchor="end" className="text-[9px] fill-slate-400 font-bold">
            {(providersWithHistory[0]?.currencySymbol || '₹')}{Math.round(maxFare)}
          </text>
          <text x={paddingX - 6} y={paddingY + plotHeight} textAnchor="end" className="text-[9px] fill-slate-400 font-bold">
            {(providersWithHistory[0]?.currencySymbol || '₹')}{Math.round(minFare)}
          </text>

          {/* Provider Polylines */}
          {providersWithHistory.map((p) => {
            const hist: number[] = p.volatility.recent_history;
            if (hist.length < 2) {
              const y = paddingY + plotHeight - ((hist[0] - minFare) / range) * plotHeight;
              return (
                <circle
                  key={p.provider}
                  cx={svgWidth / 2}
                  cy={y}
                  r={4}
                  fill={getProviderStroke(p.provider)}
                />
              );
            }

            const step = plotWidth / (hist.length - 1);
            const points = hist.map((fare, idx) => {
              const x = paddingX + idx * step;
              const y = paddingY + plotHeight - ((fare - minFare) / range) * plotHeight;
              return `${x},${y}`;
            }).join(' ');

            return (
              <g key={p.provider}>
                <polyline
                  fill="none"
                  stroke={getProviderStroke(p.provider)}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={points}
                />
                {hist.map((fare, idx) => {
                  const x = paddingX + idx * step;
                  const y = paddingY + plotHeight - ((fare - minFare) / range) * plotHeight;
                  return (
                    <circle
                      key={idx}
                      cx={x}
                      cy={y}
                      r={idx === hist.length - 1 ? 4 : 2}
                      fill={getProviderStroke(p.provider)}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Volatility Legend & Trend Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 border-t border-[var(--border-color)]">
        {providersWithHistory.slice(0, 3).map((p) => {
          const vol = p.volatility || {};
          const trend = vol.price_trend || 'STABLE';
          const stroke = getProviderStroke(p.provider);

          return (
            <div key={p.provider} className="p-2 bg-[var(--bg-primary)]/50 border border-[var(--border-color)] rounded-xl flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-1.5 truncate">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: stroke }} />
                <span className="font-bold text-[var(--text-primary)] truncate">{p.provider}</span>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {trend === 'RISING' && <TrendingUp size={12} className="text-amber-500" />}
                {trend === 'FALLING' && <TrendingDown size={12} className="text-emerald-500" />}
                {trend === 'STABLE' && <Minus size={12} className="text-slate-400" />}
                <span className="text-[10px] font-semibold text-[var(--text-secondary)]">
                  {vol.volatility_score || 'LOW'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PriceHistoryGraph;
