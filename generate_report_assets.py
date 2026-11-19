import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import joblib

# Set styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['figure.titlesize'] = 14

charts_dir = os.path.join('report_assets', 'charts')
ui_dir = os.path.join('report_assets', 'ui')
os.makedirs(charts_dir, exist_ok=True)
os.makedirs(ui_dir, exist_ok=True)

# Load dataset and metadata
data_path = os.path.join('ml', 'data', 'raw', 'historical_fares.csv')
meta_path = os.path.join('ml', 'models', 'saved', 'model_metadata.json')

df = pd.read_csv(data_path)
with open(meta_path, 'r') as f:
    meta = json.load(f)

print(f"Loaded dataset: {len(df)} records")

# 1. Figure 6.1: Fare Distribution
plt.figure(figsize=(10, 5), dpi=300)
palette = {'Cab': '#2563EB', 'Auto': '#10B981', 'Bike': '#F59E0B'}
sns.histplot(data=df[df['actual_fare'] <= 1200], x='actual_fare', hue='vehicle_type',
             palette=palette, kde=True, bins=50, alpha=0.6, element='step')
plt.title('Figure 6.1: Empirical Distribution of Actual Fares by Vehicle Class (≤ ₹1,200)')
plt.xlabel('Observed Fare (INR ₹)')
plt.ylabel('Trip Frequency')
plt.axvline(df['actual_fare'].median(), color='#DC2626', linestyle='--', linewidth=1.5, label=f'Overall Median: ₹{df["actual_fare"].median():.1f}')
plt.legend(title='Vehicle Class')
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_6_1_fare_distribution.png'))
plt.close()
print("Saved figure_6_1_fare_distribution.png")

# 2. Figure 6.2: Fare vs Distance
plt.figure(figsize=(10, 5), dpi=300)
for v_type, color in palette.items():
    sub = df[df['vehicle_type'] == v_type].sample(n=min(800, len(df[df['vehicle_type'] == v_type])), random_state=42)
    plt.scatter(sub['distance_km'], sub['actual_fare'], label=v_type, color=color, alpha=0.45, s=20)
    z = np.polyfit(sub['distance_km'], sub['actual_fare'], 1)
    p = np.poly1d(z)
    x_vals = np.linspace(sub['distance_km'].min(), sub['distance_km'].max(), 100)
    plt.plot(x_vals, p(x_vals), color=color, linewidth=2, linestyle='-')

plt.title('Figure 6.2: Observed Fare vs. Journey Distance with Category Rate Gradients')
plt.xlabel('Trip Distance (km)')
plt.ylabel('Observed Fare (INR ₹)')
plt.xlim(0, 50)
plt.ylim(0, 1600)
plt.legend(title='Vehicle Class')
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_6_2_fare_vs_distance.png'))
plt.close()
print("Saved figure_6_2_fare_vs_distance.png")

# 3. Figure 6.3: Surge Multiplier & Fares across Time of Day
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
order = ['Morning Peak', 'Evening Peak', 'Night', 'Regular']

sns.boxplot(data=df, x='time_of_day', y='surge_multiplier', order=order, ax=ax1, palette='Blues_r', showmeans=True)
ax1.set_title('(a) Surge Multiplier across Diurnal Windows')
ax1.set_xlabel('Time Period')
ax1.set_ylabel('Surge Multiplier (x Base)')

sns.boxplot(data=df[df['actual_fare'] <= 1000], x='time_of_day', y='actual_fare', order=order, ax=ax2, palette='Purples_r', showmeans=True)
ax2.set_title('(b) Fare Distribution across Diurnal Windows')
ax2.set_xlabel('Time Period')
ax2.set_ylabel('Observed Fare (INR ₹)')

fig.suptitle('Figure 6.3: Impact of Temporal Commute Periods on Dynamic Pricing and Fare Levels', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_6_3_surge_by_time_of_day.png'))
plt.close()
print("Saved figure_6_3_surge_by_time_of_day.png")

# 4. Figure 6.4: Cost Per KM across Providers
plt.figure(figsize=(10, 5), dpi=300)
df['cost_per_km'] = df['actual_fare'] / df['distance_km']
prov_stats = df.groupby('provider')['cost_per_km'].median().sort_values()
bars = plt.barh(prov_stats.index, prov_stats.values, color='#3B82F6', alpha=0.85, edgecolor='#1E40AF')
plt.title('Figure 6.4: Median Cost per Kilometer across Evaluated Provider Tiers')
plt.xlabel('Effective Rate (₹ / km)')
plt.ylabel('Provider & Tier')
for bar in bars:
    w = bar.get_width()
    plt.text(w + 0.5, bar.get_y() + bar.get_height()/2, f'₹{w:.1f}/km', va='center', ha='left', fontsize=9, fontweight='bold')
plt.xlim(0, max(prov_stats.values) * 1.15)
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_6_4_provider_cost_per_km.png'))
plt.close()
print("Saved figure_6_4_provider_cost_per_km.png")

# 5. Figure 8.1: K-Means Clustering Pricing Regimes
plt.figure(figsize=(10, 6), dpi=300)
cluster_cols = ['distance_km', 'duration_min', 'actual_fare', 'fare_per_km', 'fare_per_min', 'surge_multiplier', 'traffic_level']
from ml.inference.normalizer import engineer_features
df_feat = engineer_features(df)
scaler = joblib.load('ml/models/saved/kmeans_scaler.joblib')
kmeans = joblib.load('ml/models/saved/kmeans_cluster.joblib')
X_scaled = scaler.transform(df_feat[cluster_cols])
cluster_labels = kmeans.predict(X_scaled)

pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)

cluster_names = {
    0: 'Cluster 0: Peak Hour Surge (23.8%)',
    1: 'Cluster 1: Standard City Transit (64.9%)',
    2: 'Cluster 2: Long-Distance Transit (11.3%)'
}
cluster_colors = {0: '#EF4444', 1: '#10B981', 2: '#6366F1'}

sample_idx = np.random.RandomState(42).choice(len(X_pca), 3000, replace=False)
for c_id in [1, 0, 2]:
    mask = cluster_labels[sample_idx] == c_id
    plt.scatter(X_pca[sample_idx][mask, 0], X_pca[sample_idx][mask, 1],
                c=cluster_colors[c_id], label=cluster_names[c_id], alpha=0.5, s=25)

centers_pca = pca.transform(kmeans.cluster_centers_)
plt.scatter(centers_pca[:, 0], centers_pca[:, 1], c='black', marker='X', s=160, edgecolor='white', linewidth=2, label='Cluster Centroids')

plt.title('Figure 8.1: Unsupervised K-Means Pricing Regime Discovery (PCA 2D Projection)')
plt.xlabel(f'Principal Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}% Variance)')
plt.ylabel(f'Principal Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}% Variance)')
plt.legend(frameon=True, loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_8_1_kmeans_clusters.png'))
plt.close()
print("Saved figure_8_1_kmeans_clusters.png")

from matplotlib.patches import FancyBboxPatch

# 6. Figure 8.2: Silhouette Score Evaluation
plt.figure(figsize=(8, 4.5), dpi=300)
sil_dict = meta['silhouette_evaluations']
k_vals = [int(k) for k in sil_dict.keys()]
scores = [sil_dict[str(k)] for k in k_vals]
plt.plot(k_vals, scores, marker='o', linewidth=2.5, markersize=8, color='#4F46E5')
plt.scatter([3], [sil_dict['3']], color='#DC2626', s=150, zorder=5, label='Optimal K=3 (Silhouette = 0.3323)')
for k, s in zip(k_vals, scores):
    plt.text(k, s + 0.003, f'{s:.4f}', ha='center', fontweight='bold', fontsize=9)
plt.title('Figure 8.2: Silhouette Coefficient Analysis across Candidate Cluster Counts K in [3, 6]')
plt.xlabel('Cluster Count (K)')
plt.ylabel('Mean Silhouette Coefficient')
plt.ylim(0.25, 0.36)
plt.xticks(k_vals)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_8_2_silhouette_analysis.png'))
plt.close()
print("Saved figure_8_2_silhouette_analysis.png")

# 7. Figure 9.1: Supervised Model Comparison (RF vs GBR)
fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
models = ['Random Forest Regressor', 'Gradient Boosting Regressor (Selected)']
mae_vals = [23.50, 20.66]
rmse_vals = [42.11, 34.30]
mape_vals = [6.41, 5.96]
r2_vals = [0.9703, 0.9803]

x = np.arange(len(models))
width = 0.22

rects1 = ax.bar(x - 1.5*width, mae_vals, width, label='MAE (Rs)', color='#60A5FA')
rects2 = ax.bar(x - 0.5*width, rmse_vals, width, label='RMSE (Rs)', color='#34D399')
rects3 = ax.bar(x + 0.5*width, mape_vals, width, label='MAPE (%)', color='#FBBF24')
rects4 = ax.bar(x + 1.5*width, [v*100 for v in r2_vals], width, label='R2 Score (x100)', color='#A78BFA')

ax.set_ylabel('Metric Value')
ax.set_title('Figure 9.1: Model Selection & Holdout Validation Benchmark (Random Forest vs. Gradient Boosting)')
ax.set_xticks(x)
ax.set_xticklabels(models, fontweight='bold')
ax.legend()

for rect in list(rects1) + list(rects2) + list(rects3) + list(rects4):
    h = rect.get_height()
    ax.annotate(f'{h:.2f}',
                xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=8, rotation=0)

plt.ylim(0, 115)
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_9_1_model_comparison.png'))
plt.close()
print("Saved figure_9_1_model_comparison.png")

# 8. Figure 9.2: Residual Analysis (Actual vs Predicted)
from sklearn.model_selection import train_test_split
gbr_pipe = joblib.load('ml/models/saved/fare_regressor.joblib')
num_cols = meta['regression_features']['numerical']
cat_cols = meta['regression_features']['categorical']
df_features = df_feat.copy()
df_features['cluster_id'] = cluster_labels
clean_df = df_features[df_features.get('is_anomaly', False) == False].copy()
X = clean_df[num_cols + cat_cols]
y = clean_df['actual_fare'].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
y_pred = gbr_pipe.predict(X_test)
residuals = y_test - y_pred

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
ax1.scatter(y_pred, y_test, alpha=0.35, s=15, color='#2563EB')
min_val = min(y_test.min(), y_pred.min())
max_val = max(y_test.max(), y_pred.max())
ax1.plot([min_val, max_val], [min_val, max_val], color='#DC2626', linestyle='--', linewidth=2, label='Ideal Fit (1:1)')
ax1.set_title('(a) Predicted Fare vs. Observed Actual Fare (R2 = 0.9803)')
ax1.set_xlabel('Predicted Fare (INR Rs)')
ax1.set_ylabel('Observed Fare (INR Rs)')
ax1.legend()

sns.histplot(residuals, bins=50, kde=True, ax=ax2, color='#10B981', element='step')
ax2.axvline(0, color='#DC2626', linestyle='--', linewidth=1.5)
ax2.set_title(f'(b) Prediction Error Residuals (Mean: Rs {np.mean(residuals):.2f}, Std: Rs {np.std(residuals):.2f})')
ax2.set_xlabel('Residual Error (Observed - Predicted Rs)')
ax2.set_ylabel('Frequency')
ax2.set_xlim(-150, 150)

fig.suptitle('Figure 9.2: Gradient Boosting Regressor Residual Error Diagnostics', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_9_2_residual_analysis.png'))
plt.close()
print("Saved figure_9_2_residual_analysis.png")

# 9. Figure 9.3: Anomaly Detection Scatter
plt.figure(figsize=(10, 5.5), dpi=300)
normal_mask = ~df['is_anomaly']
anom_mask = df['is_anomaly']

plt.scatter(df[normal_mask]['distance_km'], df[normal_mask]['actual_fare'],
            color='#3B82F6', alpha=0.35, s=20, label='Normal Pricing Pattern (97.0%)')
plt.scatter(df[anom_mask]['distance_km'], df[anom_mask]['actual_fare'],
            color='#EF4444', marker='x', s=60, linewidth=1.5, label='Flagged Pricing Anomalies (3.0% Contamination)')

plt.title('Figure 9.3: Isolation Forest Multivariate Anomaly & Surge Spike Detection')
plt.xlabel('Trip Distance (km)')
plt.ylabel('Observed Fare (INR Rs)')
plt.xlim(0, 50)
plt.ylim(0, 3500)
plt.legend(frameon=True, loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(charts_dir, 'figure_9_3_anomaly_scatter.png'))
plt.close()
print("Saved figure_9_3_anomaly_scatter.png")

# 10. Figure 5.1: Architecture Diagram
fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
ax.axis('off')

boxes = [
    {'title': 'PRESENTATION LAYER (Frontend UI)', 'sub': 'React 19 • TypeScript • Vite • Tailwind CSS\n• Autocomplete Search • Leaflet Geospatial Map\n• Multi-Provider Comparison Cards • Price Sparklines\n• ML & Telemetry Analytics Hub • PWA Installability', 'xy': (0.05, 0.70), 'wh': (0.90, 0.22), 'color': '#DBEAFE', 'edge': '#1E40AF'},
    {'title': 'APPLICATION & GATEWAY LAYER (FastAPI Backend)', 'sub': 'FastAPI Gateway (Port 5000) • Pydantic v2 • Nominatim Geocoding Proxy\n• Project-OSRM Road Routing Engine • Async Quote Orchestrator (15s Window)\n• Circuit Breakers & Timeout Handlers • Route Hashing & Volatility Tracker', 'xy': (0.05, 0.38), 'wh': (0.50, 0.25), 'color': '#DCFCE7', 'edge': '#15803D'},
    {'title': 'IN-PROCESS ML INTELLIGENCE SUBSYSTEM', 'sub': 'Fare Normalizer & Continuous Feature Pipeline\n• K-Means Regime Profiler (K=3, Silhouette=0.3323)\n• Gradient Boosting Regressor Baseline (R2=0.9803)\n• Isolation Forest Surge Anomaly Detector (Contam=3%)\n• Multi-Factor Smart Utility Scorer', 'xy': (0.58, 0.38), 'wh': (0.37, 0.25), 'color': '#FEF3C7', 'edge': '#B45309'},
    {'title': 'EXTERNAL SERVICES & DATA SOURCES', 'sub': '• OSM Nominatim Geocoder\n• Project-OSRM Road Routing Engine\n• Regulatory Rate Cards & Gazette Tariffs\n• Provider Deep-Linking Engines', 'xy': (0.05, 0.06), 'wh': (0.50, 0.24), 'color': '#F3E8FF', 'edge': '#6B21A8'},
    {'title': 'DATA PERSISTENCE LAYER', 'sub': 'PostgreSQL / SQLite Database Fallback\n• searches • historical_fares (12,000 records)\n• fare_snapshots (Volatility tracker)\n• analytics (Telemetry & Click log)', 'xy': (0.58, 0.06), 'wh': (0.37, 0.24), 'color': '#F1F5F9', 'edge': '#334155'}
]

for b in boxes:
    rect = FancyBboxPatch(b['xy'], b['wh'][0], b['wh'][1], boxstyle="round,pad=0.02",
                          facecolor=b['color'], edgecolor=b['edge'], linewidth=2,
                          transform=ax.transAxes, zorder=2)
    ax.add_patch(rect)
    ax.text(b['xy'][0] + 0.02, b['xy'][1] + b['wh'][1] - 0.04, b['title'], fontsize=11, fontweight='bold', color='#0F172A', transform=ax.transAxes)
    ax.text(b['xy'][0] + 0.02, b['xy'][1] + 0.03, b['sub'], fontsize=9, color='#1E293B', transform=ax.transAxes, va='bottom')

ax.annotate('', xy=(0.30, 0.63), xytext=(0.30, 0.70), arrowprops=dict(arrowstyle='<|-|>', lw=2, color='#1E3A8A'))
ax.text(0.31, 0.66, 'REST API / JSON Payload', fontsize=8, color='#1E3A8A', fontweight='bold')

ax.annotate('', xy=(0.58, 0.50), xytext=(0.55, 0.50), arrowprops=dict(arrowstyle='<|-|>', lw=2, color='#B45309'))
ax.text(0.552, 0.52, 'In-Process ML Call', fontsize=8, color='#B45309', fontweight='bold')

ax.annotate('', xy=(0.30, 0.31), xytext=(0.30, 0.38), arrowprops=dict(arrowstyle='<|-|>', lw=2, color='#6B21A8'))
ax.text(0.31, 0.34, 'HTTP / Lat-Lng Route', fontsize=8, color='#6B21A8', fontweight='bold')

ax.annotate('', xy=(0.76, 0.31), xytext=(0.76, 0.38), arrowprops=dict(arrowstyle='<|-|>', lw=2, color='#334155'))
ax.text(0.77, 0.34, 'SQLAlchemy ORM', fontsize=8, color='#334155', fontweight='bold')

plt.title('Figure 5.1: High-Level Three-Tier Modular System Architecture of RideCompare', fontsize=14, fontweight='bold', y=0.97)
plt.tight_layout()
plt.savefig(os.path.join(ui_dir, 'figure_5_1_system_architecture.png'))
plt.close()
print("Saved figure_5_1_system_architecture.png")

# 11. Figure 13.1: UI Overview Diagram
fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
ax.axis('off')

panels = [
    {'title': 'PANEL A: ROUTE SEARCH & GEOCODING AUTOCOMPLETE', 'sub': '• Nominatim Real-Time Location Typeahead\n• Instant Distance & Straight-Line Validation (<300km)\n• City Corridor Auto-Detection (Bangalore, Delhi, Mumbai, etc.)\n• Departure Time & Surge Status Overrides', 'xy': (0.04, 0.53), 'wh': (0.44, 0.40), 'color': '#EFF6FF', 'edge': '#3B82F6'},
    {'title': 'PANEL B: INTERACTIVE LEAFLET ROUTING MAP', 'sub': '• Turn-by-Turn Road Polyline Geometry from OSRM\n• Origin & Destination Custom Location Pins\n• Distance & Duration Floating Marker Badges\n• Dynamic Viewport Auto-Fit and Smooth Panning', 'xy': (0.52, 0.53), 'wh': (0.44, 0.40), 'color': '#F0FDF4', 'edge': '#22C55E'},
    {'title': 'PANEL C: MULTI-PROVIDER COMPARISON CARDS', 'sub': '• Side-by-side Cards: Uber Go, Ola Mini, Rapido Bike/Auto, Local Taxi\n• Highlight Badges: "Cheapest", "Fastest", "Best Value", "Zero Surge"\n• In-Process ML Expected Fare Baseline (+Rs Difference & % Surge Markup)\n• Pricing Regime Tag ("Peak Hour Surge", "Standard", "Long-Distance")\n• One-Tap Direct App Deep Linking (Auto-prefilling Coordinates)', 'xy': (0.04, 0.05), 'wh': (0.44, 0.44), 'color': '#FFFBEB', 'edge': '#F59E0B'},
    {'title': 'PANEL D: ML INTELLIGENCE & ANALYTICS DASHBOARD', 'sub': '• Multi-Factor Smart Score Utility Breakdown (Price, ETA, Reliability)\n• Corridor Price Volatility Sparklines (Rising, Falling, Stable Trends)\n• 7-Day Search Volume & Aggregated User Savings Metrics\n• Live Model Health Telemetry (R2=0.9803, Silhouette=0.3323, 28 Tests Passing)\n• One-Click On-Demand Model Retraining Trigger', 'xy': (0.52, 0.05), 'wh': (0.44, 0.44), 'color': '#FAF5FF', 'edge': '#A855F7'}
]

for p in panels:
    rect = FancyBboxPatch(p['xy'], p['wh'][0], p['wh'][1], boxstyle="round,pad=0.02",
                          facecolor=p['color'], edgecolor=p['edge'], linewidth=2,
                          transform=ax.transAxes, zorder=2)
    ax.add_patch(rect)
    ax.text(p['xy'][0] + 0.02, p['xy'][1] + p['wh'][1] - 0.05, p['title'], fontsize=10, fontweight='bold', color='#0F172A', transform=ax.transAxes)
    ax.text(p['xy'][0] + 0.02, p['xy'][1] + 0.04, p['sub'], fontsize=8.5, color='#334155', transform=ax.transAxes, va='bottom')

plt.title('Figure 13.1: Comprehensive User Interface Layout & Functional Panels of RideCompare', fontsize=14, fontweight='bold', y=0.97)
plt.tight_layout()
plt.savefig(os.path.join(ui_dir, 'figure_13_1_ui_overview.png'))
plt.close()
print("Saved figure_13_1_ui_overview.png")

print("All figures successfully generated in report_assets/!")
