import React, { useState, useEffect } from 'react';
import {
  Cpu, CheckCircle2,
  Layers, Database, Sparkles, RefreshCw, Sliders, ShieldAlert,
  BarChart3, Lock, ChevronDown, ChevronUp
} from 'lucide-react';
import { apiFetch } from '../utils/api';

interface ModelMetrics {
  status: string;
  model_type: string;
  model_version: string;
  last_trained: string;
  total_training_records: number;
  prediction_accuracy: string;
  metrics: {
    mae: number;
    rmse: number;
    r2: number;
    mape: string;
    accuracy_pct: number;
  };
  regression_comparison?: Record<string, { mae: number; rmse: number; mape: number; r2: number }>;
  features: {
    numerical: string[];
    categorical: string[];
  };
  clustering: {
    optimal_k: number;
    silhouette_score: number;
    profiles: Record<string, {
      cluster_id: number;
      label: string;
      tag: string;
      description: string;
      size: number;
      percentage: number;
      avg_fare: number;
      avg_surge: number;
    }>;
  };
  anomaly_detection: {
    contamination: number;
    training_anomalies_detected: number;
    anomaly_rate_percent: number;
    features: string[];
  };
  pipeline_telemetry: {
    continuous_ingestion: boolean;
    db_ingested_observations: number;
    db_anomalies_detected: number;
    inference_mode: string;
  };
}

interface InferenceResult {
  predicted_fare: number;
  typical_fare_range: string;
  cluster_label: string;
  is_anomaly: boolean;
  price_anomaly: string;
  anomaly_reason: string;
  ml_insight: string;
}

interface InternalMLDashboardProps {
  onExit?: () => void;
}

export const InternalMLDashboard: React.FC<InternalMLDashboardProps> = ({ onExit }) => {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showSandbox, setShowSandbox] = useState(false);
  const [testDist, setTestDist] = useState(12.5);
  const [testDur, setTestDur] = useState(25);
  const [testSurge, setTestSurge] = useState(1.2);
  const [testProvider, setTestProvider] = useState('Uber Go');
  const [testResult, setTestResult] = useState<InferenceResult | null>(null);
  const [testingInference, setTestingInference] = useState(false);

  const refreshMetrics = async () => {
    try {
      setRefreshing(true);
      const res = await apiFetch('/api/admin/ml-metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Failed refreshing ML metrics:', err);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    apiFetch('/api/admin/ml-metrics')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!ignore) {
          if (data) setMetrics(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          console.error('Failed fetching ML metrics:', err);
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleTestInference = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setTestingInference(true);
      const res = await apiFetch('/api/admin/ml-predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: testProvider,
          vehicle_type: testProvider.includes('Bike') ? 'Bike' : testProvider.includes('Auto') ? 'Auto' : 'Cab',
          distance_km: Number(testDist),
          duration_min: Number(testDur),
          surge_multiplier: Number(testSurge),
          traffic_condition: testSurge > 1.3 ? 'Heavy' : 'Normal',
          time_of_day: testSurge > 1.3 ? 'Peak Hour' : 'Regular',
          day_of_week: 'Monday',
          city: 'Bangalore'
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult(data.result);
      }
    } catch (err) {
      console.error('Inference diagnostic test failed:', err);
    } finally {
      setTestingInference(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="h-8 w-64 bg-slate-200 dark:bg-slate-800 rounded-lg"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-200 dark:bg-slate-800 rounded-2xl"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-8 text-center text-sm font-semibold text-rose-500">
        Unable to load ML telemetry. Verify the backend ML service is operational.
      </div>
    );
  }

  const {
    model_type, model_version, last_trained, total_training_records,
    metrics: reg_metrics, regression_comparison, features, clustering,
    anomaly_detection, pipeline_telemetry
  } = metrics;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-wider uppercase bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1">
              <Lock size={11} /> Restricted Admin Console
            </span>
            <span className="text-[11px] font-semibold text-emerald-500 flex items-center gap-1">
              <CheckCircle2 size={12} /> Model Active ({model_version})
            </span>
          </div>
          <h2 className="text-xl font-black text-[var(--text-primary)] tracking-tight">
            Internal ML Pricing Intelligence & Model Telemetry
          </h2>
          <p className="text-xs text-[var(--text-secondary)] font-medium">
            Read-only evaluation benchmarks, continuous feature pipelines, and anomaly detection stats.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onExit && (
            <button
              onClick={onExit}
              className="px-3 py-1.5 rounded-xl border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] text-xs font-bold text-[var(--text-primary)] transition-all cursor-pointer"
            >
              ← Back to Analytics
            </button>
          )}
          <button
            onClick={refreshMetrics}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Model Overview & Core Accuracy Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">Model Architecture</span>
          <p className="text-sm font-black text-[var(--text-primary)] truncate">{model_type.replace(' Regressor', '')}</p>
          <span className="text-[10px] text-indigo-500 font-semibold block">{model_version}</span>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">R² Goodness of Fit</span>
          <p className="text-2xl font-black text-emerald-500">{reg_metrics.r2}</p>
          <span className="text-[10px] text-[var(--text-secondary)] font-semibold block">Variance explained</span>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">MAE (Mean Abs Error)</span>
          <p className="text-2xl font-black text-[var(--text-primary)]">₹{reg_metrics.mae}</p>
          <span className="text-[10px] text-[var(--text-secondary)] font-semibold block">Average fare delta</span>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">RMSE (Root MSE)</span>
          <p className="text-2xl font-black text-[var(--text-primary)]">₹{reg_metrics.rmse}</p>
          <span className="text-[10px] text-[var(--text-secondary)] font-semibold block">Penalty on large errors</span>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">MAPE Error Rate</span>
          <p className="text-2xl font-black text-indigo-500">{reg_metrics.mape}</p>
          <span className="text-[10px] text-emerald-500 font-semibold block">Accuracy: {reg_metrics.accuracy_pct}%</span>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
          <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)]">Training Samples</span>
          <p className="text-2xl font-black text-[var(--text-primary)]">{total_training_records.toLocaleString()}</p>
          <span className="text-[10px] text-[var(--text-secondary)] font-semibold block">Trained: {new Date(last_trained).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Grid: Feature Engineering & Clustering Profiles */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Feature Engineering Pipeline */}
        <div className="lg:col-span-5 p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
              <Sliders size={14} className="text-indigo-500" /> Feature Engineering Pipeline
            </h3>
            <span className="text-[10px] font-bold text-[var(--text-secondary)]">
              {features.numerical.length + features.categorical.length} Total Features
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)] block">Numerical Features (Transformed & Scaled)</span>
            <div className="flex flex-wrap gap-1.5">
              {features.numerical.map((feat: string) => (
                <span
                  key={feat}
                  className="px-2 py-1 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] font-mono text-[11px] font-semibold text-[var(--text-primary)]"
                >
                  {feat}
                </span>
              ))}
            </div>

            <span className="text-[10px] font-bold uppercase text-[var(--text-secondary)] block pt-2">Categorical Encodings</span>
            <div className="flex flex-wrap gap-1.5">
              {features.categorical.map((feat: string) => (
                <span
                  key={feat}
                  className="px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 font-mono text-[11px] font-bold text-indigo-500 dark:text-indigo-400"
                >
                  {feat} (One-Hot Encoded)
                </span>
              ))}
            </div>

            <div className="pt-3 border-t border-[var(--border-color)] space-y-1.5 text-[11px] text-[var(--text-secondary)]">
              <div className="flex justify-between font-medium">
                <span>Cyclical Time Encodings:</span>
                <span className="font-semibold text-[var(--text-primary)]">sin/cos(hour/24)</span>
              </div>
              <div className="flex justify-between font-medium">
                <span>Unit Economics Ratios:</span>
                <span className="font-semibold text-[var(--text-primary)]">fare_per_km, fare_per_min</span>
              </div>
              <div className="flex justify-between font-medium">
                <span>Traffic Level Normalization:</span>
                <span className="font-semibold text-[var(--text-primary)]">Weighted 1.0–3.5 density index</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Pricing Regimes & K-Means Clustering */}
        <div className="lg:col-span-7 p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
              <Layers size={14} className="text-emerald-500" /> K-Means Pricing Regimes (k={clustering.optimal_k})
            </h3>
            <span className="text-[10px] font-bold text-emerald-500 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full">
              Silhouette: {clustering.silhouette_score}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(clustering.profiles).map(([id, prof]) => (
              <div
                key={id}
                className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-500 dark:text-indigo-400">
                    Regime {prof.cluster_id}
                  </span>
                  <span className="text-[10px] font-bold text-[var(--text-secondary)]">{prof.percentage}%</span>
                </div>
                <h4 className="text-xs font-bold text-[var(--text-primary)]">{prof.label}</h4>
                <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed font-normal">{prof.description}</p>
                <div className="pt-2 border-t border-[var(--border-color)] text-[10px] space-y-0.5 text-[var(--text-secondary)] font-medium">
                  <div className="flex justify-between">
                    <span>Avg Fare:</span>
                    <span className="font-bold text-[var(--text-primary)]">₹{prof.avg_fare}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Surge:</span>
                    <span className="font-bold text-[var(--text-primary)]">{prof.avg_surge}x</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Anomaly Detection & Model Comparison Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Anomaly Detection */}
        <div className="lg:col-span-6 p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-amber-500" /> Isolation Forest Fare Anomaly Detection
            </h3>
            <span className="text-[10px] font-bold text-amber-500 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
              Contamination: {anomaly_detection.contamination * 100}%
            </span>
          </div>

          <p className="text-xs text-[var(--text-secondary)] font-medium leading-relaxed">
            Identifies dynamic fare price gouging, excessive surge spikes, or meter exploitation by isolating multi-dimensional outliers in distance, duration, and marginal cost.
          </p>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl">
              <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block">Training Anomalies</span>
              <span className="text-lg font-black text-amber-500">{anomaly_detection.training_anomalies_detected}</span>
              <span className="text-[10px] text-[var(--text-secondary)] block">({anomaly_detection.anomaly_rate_percent}% of dataset)</span>
            </div>
            <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl">
              <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block">Production Telemetry</span>
              <span className="text-lg font-black text-emerald-500">{pipeline_telemetry.db_anomalies_detected} Live</span>
              <span className="text-[10px] text-[var(--text-secondary)] block">Flagged in search history</span>
            </div>
          </div>
        </div>

        {/* Model Evaluation Comparison (Gradient Boosting vs Random Forest) */}
        <div className="lg:col-span-6 p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
              <BarChart3 size={14} className="text-indigo-500" /> Supervised Model Evaluation Comparison
            </h3>
            <span className="text-[10px] font-bold text-indigo-500 bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 rounded-full">
              Ensemble Evaluation
            </span>
          </div>

          <div className="overflow-x-auto text-xs">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[var(--border-color)] text-[10px] font-bold uppercase text-[var(--text-secondary)]">
                  <th className="py-2">Algorithm</th>
                  <th className="py-2">MAE</th>
                  <th className="py-2">RMSE</th>
                  <th className="py-2">MAPE</th>
                  <th className="py-2">R² Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]">
                {regression_comparison && Object.entries(regression_comparison).map(([alg, met]) => (
                  <tr key={alg} className={alg === 'gradient_boosting' ? 'font-bold text-emerald-500' : 'text-[var(--text-primary)]'}>
                    <td className="py-2.5 flex items-center gap-1">
                      {alg === 'gradient_boosting' ? 'Gradient Boosting (Selected)' : 'Random Forest Regressor'}
                    </td>
                    <td className="py-2.5">₹{met.mae}</td>
                    <td className="py-2.5">₹{met.rmse}</td>
                    <td className="py-2.5">{met.mape}%</td>
                    <td className="py-2.5">{met.r2}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Real-time Feature Pipeline & Continuous Ingestion Status */}
      <div className="p-5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-3">
        <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
          <Database size={14} className="text-sky-500" /> Real-Time Continuous Ingestion & Feature Pipeline
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)]">Pipeline Stage 1</span>
            <p className="font-bold text-[var(--text-primary)]">Provider Live API</p>
            <span className="text-[10px] text-emerald-500 block">Authoritative live fare</span>
          </div>

          <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)]">Pipeline Stage 2</span>
            <p className="font-bold text-[var(--text-primary)]">Observation Ingestion</p>
            <span className="text-[10px] text-indigo-500 block">{pipeline_telemetry.db_ingested_observations} Ingested observations</span>
          </div>

          <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)]">Pipeline Stage 3</span>
            <p className="font-bold text-[var(--text-primary)]">ML Feature Normalizer</p>
            <span className="text-[10px] text-sky-500 block">Feature engineering & regimes</span>
          </div>

          <div className="p-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-[var(--text-secondary)]">Pipeline Stage 4</span>
            <p className="font-bold text-[var(--text-primary)]">Comparison & Anomaly Engine</p>
            <span className="text-[10px] text-emerald-500 block">Enriched user insights</span>
          </div>
        </div>
      </div>

      {/* Collapsible Inference Diagnostic Sandbox (Hidden by default to prevent unauthorized/unnecessary exposure) */}
      <div className="p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu size={14} className="text-indigo-500" />
            <h3 className="text-xs font-black uppercase tracking-wider text-[var(--text-primary)]">
              Developer Inference Sandbox
            </h3>
            <span className="text-[10px] text-[var(--text-secondary)] font-medium">(Optional Diagnostic Tool)</span>
          </div>
          <button
            onClick={() => setShowSandbox(!showSandbox)}
            className="flex items-center gap-1 text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
          >
            {showSandbox ? (
              <>Hide Sandbox <ChevronUp size={14} /></>
            ) : (
              <>Open Sandbox <ChevronDown size={14} /></>
            )}
          </button>
        </div>

        {showSandbox && (
          <>
            <form onSubmit={handleTestInference} className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end text-xs pt-2">
          <div>
            <label className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block mb-1">Provider</label>
            <select
              value={testProvider}
              onChange={(e) => setTestProvider(e.target.value)}
              className="w-full p-2 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-semibold"
            >
              <option value="Uber Go">Uber Go</option>
              <option value="Uber Premier">Uber Premier</option>
              <option value="Ola Mini">Ola Mini</option>
              <option value="Rapido Bike">Rapido Bike</option>
              <option value="Rapido Auto">Rapido Auto</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block mb-1">Distance (km)</label>
            <input
              type="number"
              step="0.5"
              value={testDist}
              onChange={(e) => setTestDist(Number(e.target.value))}
              className="w-full p-2 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-semibold"
            />
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block mb-1">Duration (mins)</label>
            <input
              type="number"
              value={testDur}
              onChange={(e) => setTestDur(Number(e.target.value))}
              className="w-full p-2 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-semibold"
            />
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold text-[var(--text-secondary)] block mb-1">Surge Multiplier</label>
            <input
              type="number"
              step="0.1"
              value={testSurge}
              onChange={(e) => setTestSurge(Number(e.target.value))}
              className="w-full p-2 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-semibold"
            />
          </div>

          <button
            type="submit"
            disabled={testingInference}
            className="w-full p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold transition-all shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
          >
            <Sparkles size={13} />
            <span>{testingInference ? 'Running...' : 'Run Inference'}</span>
          </button>
        </form>

            {testResult && (
              <div className="p-4 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl space-y-2 animate-fade-in text-xs">
                <span className="text-[10px] uppercase font-bold text-emerald-500 block">Inference Output Result</span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <span className="text-[10px] text-[var(--text-secondary)] block">Predicted Typical Fare:</span>
                    <span className="text-base font-black text-[var(--text-primary)]">₹{testResult.predicted_fare}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[var(--text-secondary)] block">Typical Fare Range:</span>
                    <span className="text-sm font-bold text-indigo-500">{testResult.typical_fare_range}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[var(--text-secondary)] block">Pricing Regime:</span>
                    <span className="text-sm font-bold text-[var(--text-primary)]">{testResult.cluster_label}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[var(--text-secondary)] block">Anomaly Assessment:</span>
                    <span className={`text-sm font-bold ${testResult.is_anomaly ? 'text-amber-500' : 'text-emerald-500'}`}>
                      {testResult.price_anomaly} ({testResult.anomaly_reason})
                    </span>
                  </div>
                </div>
                <div className="pt-2 border-t border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] font-medium">
                  ML Insight: <em>"{testResult.ml_insight}"</em>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
export default InternalMLDashboard;
