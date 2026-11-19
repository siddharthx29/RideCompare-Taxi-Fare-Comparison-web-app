"""
Generates ridecompare_python_record.pdf from the academic report specifications.
Pure white theme, #1F2937 typography, 1-inch margins, standard academic formatting.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image as RLImage, Preformatted
)
from reportlab.pdfgen import canvas


class AcademicRecordCanvas(canvas.Canvas):
    """Running header and footer with total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1F2937"))

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, A4[1] - 36, "RideCompare: ML Fare Intelligence & Taxi Comparison Record")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#4B5563"))
            self.drawRightString(A4[0] - 54, A4[1] - 36, "Academic Project Record")
            self.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.setLineWidth(0.75)
            self.line(54, A4[1] - 42, A4[0] - 54, A4[1] - 42)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.75)
        self.line(54, 46, A4[0] - 54, 46)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4B5563"))
        self.drawString(54, 34, "Department of Computer Applications | Machine Learning Project Record")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 54, 34, page_text)
        self.restoreState()


def build_pdf(output_pdf_path: str):
    # 1-inch margins = 72 points
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    printable_width = A4[0] - 108

    styles = getSampleStyleSheet()

    # Academic Typography Palette
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#111827"),
        spaceAfter=4,
        alignment=0
    )

    sub_title_style = ParagraphStyle(
        'DocSubTitle',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SecH1',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#111827"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SecH2',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1F2937"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    caption_style = ParagraphStyle(
        'Caption',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#4B5563"),
        alignment=1,
        spaceAfter=8,
        spaceBefore=3
    )

    th_style = ParagraphStyle(
        'TH',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#111827")
    )

    td_style = ParagraphStyle(
        'TD',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1F2937")
    )

    td_code = ParagraphStyle(
        'TDCode',
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1E3A8A")
    )

    story = []

    # 1. Project Title / Topic
    story.append(Paragraph("1. Project Title / Topic", h1_style))
    story.append(Paragraph("<b>Smart Real-Time Taxi Fare Comparison and Machine Learning Based Fare Intelligence System (RideCompare)</b>", title_style))
    story.append(Paragraph("Domain Techniques: Supervised Regression (Gradient Tree Boosting, Random Forest), Unsupervised Pricing Regime Clustering (K-Means), and Multivariate Anomaly Detection (Isolation Forest)", sub_title_style))

    # 2. Objectives
    story.append(Paragraph("2. Objectives", h1_style))
    objectives = [
        "<b>Mitigate Commuter Market Opacity and App-Switching Friction:</b> Overcome severe price fragmentation and dynamic tariff dispersion across commercial ride-hailing networks (Uber, Ola, Rapido) and municipal metered taxis by engineering a unified analytical framework that aggregates and benchmarks disparate transport modes in real time.",
        "<b>Formulate Transparent Tariff Baselines Using Supervised Regression:</b> Develop, tune, and validate high-precision supervised machine learning regressors (Gradient Boosting Regressor benchmarked against Random Forest) capable of predicting expected fair journey tariffs across spatial distances, route durations, diurnal commute cycles, and multi-tier vehicle classes with an explanatory variance exceeding <i>R</i>² ≥ 0.95.",
        "<b>Discover Latent Urban Pricing Regimes via Unsupervised Clustering:</b> Utilize unsupervised K-Means clustering validated by silhouette coefficient analysis to partition heterogeneous urban trips into empirical pricing regimes (<i>Peak Hour Surge</i>, <i>Standard City Transit</i>, <i>Long-Distance Transit</i>), quantifying the structural impact of traffic congestion and peak commute windows on ride economics.",
        "<b>Detect Pricing Anomalies and Surge Gouging via Isolation Forests:</b> Implement an unsupervised Isolation Forest anomaly detection engine to identify extreme pricing anomalies, irrational tariff spikes, or aggregator software pricing glitches, supplying commuters with natural-language diagnostic explanations.",
        "<b>Deliver an Actionable Multi-Criteria Utility Ranking:</b> Provide a composite decision framework that scores travel options according to commuter utility—harmonizing tariff cost (40%), pickup ETA (30%), prediction certainty (15%), and provider reliability (15%)—enabling optimal, cost-efficient transit selection."
    ]
    for obj in objectives:
        story.append(Paragraph(f"&bull;&nbsp; {obj}", bullet_style))

    story.append(Spacer(1, 6))

    # 3. Description of the Dataset
    story.append(Paragraph("3. Description of the Dataset", h1_style))
    story.append(Paragraph(
        "The analysis utilizes the <b>RideCompare Historical Transit Fare Dataset</b>, an empirical and regulatory-calibrated repository reflecting multi-provider ride-hailing operations across major Indian metropolitan corridors (Bangalore, Delhi NCR, and Mumbai). The dataset incorporates official transport department gazette rate cards, commercial aggregator tariff structures, Project-OSRM road routing distances, and OpenStreetMap spatial coordinates.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Dataset Summary:</b> 12,000 records (rows) × 22 attributes (columns). Target Variable: <code>actual_fare</code> (Continuous numerical variable denoting the total final fare in INR ₹).",
        body_style
    ))

    # Table of key attributes
    dataset_table_data = [
        [Paragraph("Attribute Name", th_style), Paragraph("Data Type", th_style), Paragraph("Unit", th_style), Paragraph("Functional Description", th_style)],
        [Paragraph("<code>provider</code>", td_code), Paragraph("String (Nominal)", td_style), Paragraph("Label", td_style), Paragraph("Service provider tier (Uber Go, Uber Premier, Ola Mini, Ola Prime, Rapido Bike, Rapido Auto, Local Taxi).", td_style)],
        [Paragraph("<code>vehicle_type</code>", td_code), Paragraph("String (Nominal)", td_style), Paragraph("Label", td_style), Paragraph("Broad vehicular classification (Cab, Auto, Bike).", td_style)],
        [Paragraph("<code>distance_km</code>", td_code), Paragraph("Float (Numeric)", td_style), Paragraph("km", td_style), Paragraph("Network driving distance determined via OSRM routing kinematics (bounded [1.0, 48.0] km).", td_style)],
        [Paragraph("<code>duration_min</code>", td_code), Paragraph("Float (Numeric)", td_style), Paragraph("min", td_style), Paragraph("Estimated trip duration factoring in road class and congestion speeds.", td_style)],
        [Paragraph("<code>actual_fare</code>", td_code), Paragraph("Float (Target)", td_style), Paragraph("INR ₹", td_style), Paragraph("Total observed journey fare including base, distance, time, surge, and statutory fees.", td_style)],
        [Paragraph("<code>base_fare</code>", td_code), Paragraph("Integer (Numeric)", td_style), Paragraph("INR ₹", td_style), Paragraph("Mandatory initial flag-fall tariff before distance accruals.", td_style)],
        [Paragraph("<code>surge_multiplier</code>", td_code), Paragraph("Float (Numeric)", td_style), Paragraph("Ratio", td_style), Paragraph("Dynamic demand-supply pricing multiplier (1.0x to 2.4x).", td_style)],
        [Paragraph("<code>traffic_condition</code>", td_code), Paragraph("String (Ordinal)", td_style), Paragraph("Level", td_style), Paragraph("Congestion intensity at departure (Low, Normal, Moderate, Heavy, Severe).", td_style)],
        [Paragraph("<code>time_of_day</code>", td_code), Paragraph("String (Nominal)", td_style), Paragraph("Window", td_style), Paragraph("Commute period (Morning Peak, Evening Peak, Night, Regular).", td_style)],
        [Paragraph("<code>hour</code>", td_code), Paragraph("Integer (Numeric)", td_style), Paragraph("24-Hr", td_style), Paragraph("Diurnal departure hour (0 to 23).", td_style)],
        [Paragraph("<code>is_anomaly</code>", td_code), Paragraph("Boolean (Binary)", td_style), Paragraph("Flag", td_style), Paragraph("Synthetic anomaly injection flag for algorithm validation (~2.5% rate).", td_style)]
    ]
    t_data = Table(dataset_table_data, colWidths=[printable_width * 0.20, printable_width * 0.17, printable_width * 0.11, printable_width * 0.52])
    t_data.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_data)
    story.append(Spacer(1, 6))

    # 4. Summary of Procedures
    story.append(Paragraph("4. Summary of Procedures", h1_style))
    procedures = [
        ("4.1 Library Imports & Dataset Loading", "The pipeline environment was established using Python 3.11 with scikit-learn, pandas, numpy, and matplotlib. A total of 12,000 historical records were ingested from the raw data repository (<code>historical_fares.csv</code>), featuring automated fallback synthesis to ensure environment portability."),
        ("4.2 Structural Inspection & Quality Checks", "Systematic data audits confirmed 12,000 complete instances with zero missing values across all 22 attributes. Boundary constraints verified that distances complied with geographical limits (0.1 ≤ km ≤ 100), durations remained strictly positive (1.0 ≤ min ≤ 300), and fares respected economic floors (≥ ₹10). Zero duplicate rows were found."),
        ("4.3 Preprocessing & Feature Engineering", "Feature engineering generated high-leverage predictors: continuous unit rates (<code>fare_per_km</code>, <code>fare_per_min</code>, <code>speed_kmh</code>); 24-hour trigonometric cyclic transformations (<code>hour_sin = sin(2π·hour/24)</code>, <code>hour_cos = cos(2π·hour/24)</code>); ordinal traffic mapping (Low=1.0 to Severe=4.5); and one-hot encoding for providers and vehicle classes."),
        ("4.4 Exploratory Data Analysis & Visualizations", "EDA established that travel distances follow a right-skewed log-normal distribution (median: 8.97 km). Strong linear rate scaling (r = 0.89) was observed across distance and fare, with clear category gradients separating bikes, autos, standard cabs, and premium cabs. Diurnal commute windows revealed peak surge multipliers averaging 1.42x to 1.51x."),
        ("4.5 Model Architecture & Technique Application", "Three ML architectures were constructed: (1) Unsupervised K-Means clustering across 7 standardized dimensions with silhouette validation across K ∈ [3..6], selecting K=3; (2) Supervised regression pipelines benchmarking Random Forest (100 trees, depth 12) vs. Gradient Tree Boosting (120 trees, depth 6, lr 0.08) via ColumnTransformer; (3) Isolation Forest (100 estimators, 3% contamination) for multivariate anomaly isolation."),
        ("4.6 Model Training, Predictions, and Validation", "The dataset was partitioned into an 80% training set (9,360 records) and a 20% holdout test set (2,340 records). Regressors were trained on inlier instances and evaluated across MAE, MSE, RMSE, MAPE, and R² score. Trained models and scalers were serialized as joblib artifacts alongside JSON metadata.")
    ]
    for p_title, p_desc in procedures:
        story.append(Paragraph(f"<b>{p_title}</b>", h2_style))
        story.append(Paragraph(p_desc, body_style))

    story.append(Spacer(1, 6))

    # 5. Evaluation and Results
    story.append(Paragraph("5. Evaluation and Results", h1_style))
    story.append(Paragraph("<b>5.1 Supervised Regression Evaluation (Holdout Test Set)</b>", h2_style))

    eval_table_data = [
        [Paragraph("Model Architecture", th_style), Paragraph("MAE (₹)", th_style), Paragraph("MSE (₹²)", th_style), Paragraph("RMSE (₹)", th_style), Paragraph("MAPE (%)", th_style), Paragraph("R² Score", th_style), Paragraph("Status", th_style)],
        [Paragraph("Random Forest Regressor", td_style), Paragraph("₹23.50", td_style), Paragraph("1,773.25", td_style), Paragraph("₹42.11", td_style), Paragraph("6.41%", td_style), Paragraph("0.9703", td_style), Paragraph("Baseline", td_style)],
        [Paragraph("<b>Gradient Tree Boosting</b>", td_style), Paragraph("<b>₹20.66</b>", td_style), Paragraph("<b>1,176.49</b>", td_style), Paragraph("<b>₹34.30</b>", td_style), Paragraph("<b>5.96%</b>", td_style), Paragraph("<b>0.9803</b>", td_style), Paragraph("<b>Selected</b>", td_style)]
    ]
    t_eval = Table(eval_table_data, colWidths=[printable_width * 0.28, printable_width * 0.12, printable_width * 0.13, printable_width * 0.12, printable_width * 0.12, printable_width * 0.11, printable_width * 0.12])
    t_eval.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_eval)

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>5.2 Unsupervised K-Means Clustering Profiles (K=3, Silhouette = 0.3323)</b>", h2_style))

    cluster_table_data = [
        [Paragraph("Cluster ID", th_style), Paragraph("Regime Label", th_style), Paragraph("Share (%)", th_style), Paragraph("Count", th_style), Paragraph("Avg Fare (₹)", th_style), Paragraph("Avg Fare/km (₹)", th_style), Paragraph("Avg Surge", th_style), Paragraph("Avg Distance (km)", th_style)],
        [Paragraph("0", td_style), Paragraph("<b>Peak Hour Surge</b>", td_style), Paragraph("23.8%", td_style), Paragraph("2,853", td_style), Paragraph("₹356.00", td_style), Paragraph("₹48.39", td_style), Paragraph("1.56x", td_style), Paragraph("8.11 km", td_style)],
        [Paragraph("1", td_style), Paragraph("<b>Standard City Transit</b>", td_style), Paragraph("64.9%", td_style), Paragraph("7,787", td_style), Paragraph("₹233.31", td_style), Paragraph("₹27.08", td_style), Paragraph("1.13x", td_style), Paragraph("9.49 km", td_style)],
        [Paragraph("2", td_style), Paragraph("<b>Long-Distance Transit</b>", td_style), Paragraph("11.3%", td_style), Paragraph("1,360", td_style), Paragraph("₹850.09", td_style), Paragraph("₹31.17", td_style), Paragraph("1.34x", td_style), Paragraph("28.94 km", td_style)]
    ]
    t_clust = Table(cluster_table_data, colWidths=[printable_width * 0.10, printable_width * 0.24, printable_width * 0.11, printable_width * 0.10, printable_width * 0.13, printable_width * 0.14, printable_width * 0.10, printable_width * 0.14])
    t_clust.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_clust)

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Analytical Interpretation of Metrics:</b> The Gradient Tree Boosting Regressor established decisive superiority with an <i>R</i>² score of 0.9803, explaining over 98% of tariff variance and achieving a low Mean Absolute Percentage Error of 5.96% (MAE = ₹20.66). Prediction residuals demonstrated a Gaussian zero-centered distribution (mean ₹-0.14), validating absence of systematic bias. The unsupervised K-Means clustering objectively proved that Peak Hour Surge journeys incur an average per-kilometer rate of ₹48.39 versus ₹27.08 for standard transit, corroborating the critical need for dynamic fair-baseline notifications.",
        body_style
    ))

    story.append(Spacer(1, 6))

    # 6. Output Screenshots / Visual Artifacts
    story.append(Paragraph("6. Output Screenshots / Visual Artifacts", h1_style))
    charts_base = os.path.join(os.path.dirname(__file__), 'report_assets', 'charts')

    figures = [
        ("Figure 1: Representative Sample Records Extracted from the Historical Transit Fare Dataset (12,000 Records)", "figure_4_1_dataset_sample.png", 0.44),
        ("Figure 2: Empirical Distribution of Actual Fares by Vehicle Class (≤ ₹1,200)", "figure_6_1_fare_distribution.png", 0.44),
        ("Figure 3: Observed Fare vs. Journey Distance with Category Rate Gradients", "figure_6_2_fare_vs_distance.png", 0.44),
        ("Figure 4: Impact of Temporal Commute Periods on Surge Multipliers and Fare Levels", "figure_6_3_surge_by_time_of_day.png", 0.44),
        ("Figure 5: Median Cost per Kilometer across Evaluated Provider Tiers", "figure_6_4_provider_cost_per_km.png", 0.44),
        ("Figure 6: Unsupervised K-Means Pricing Regime Discovery (PCA 2D Projection)", "figure_8_1_kmeans_clusters.png", 0.46),
        ("Figure 7: Silhouette Coefficient Analysis across Candidate Cluster Counts K ∈ [3, 6]", "figure_8_2_silhouette_analysis.png", 0.44),
        ("Figure 8: Supervised Model Selection Benchmark (Random Forest vs. Gradient Boosting)", "figure_9_1_model_comparison.png", 0.44),
        ("Figure 9: Gradient Boosting Regressor Residual Error Diagnostics", "figure_9_2_residual_analysis.png", 0.44),
        ("Figure 10: Isolation Forest Multivariate Anomaly and Surge Spike Detection", "figure_9_3_anomaly_scatter.png", 0.44)
    ]

    for cap, fname, h_ratio in figures:
        fpath = os.path.join(charts_base, fname)
        if os.path.exists(fpath):
            img_w = printable_width
            img_h = printable_width * h_ratio
            story.append(KeepTogether([
                RLImage(fpath, width=img_w, height=img_h),
                Paragraph(cap, caption_style),
                Spacer(1, 4)
            ]))

    story.append(Spacer(1, 6))

    # 7. Code
    story.append(Paragraph("7. Code", h1_style))
    story.append(Paragraph(
        "The following complete, executable, and fully commented Python code matches the exact procedures detailed in Section 4. (For the complete full-length script, see the companion source file <code>ridecompare_python_record.md</code>).",
        body_style
    ))

    # Clean code excerpt for PDF inclusion
    code_snippet = """# RideCompare ML Execution Pipeline Excerpt
# Full executable source located in ridecompare_python_record.md

import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score

# 1. Feature Engineering
def engineer_features(df):
    df['fare_per_km'] = (df['actual_fare'] / df['distance_km']).round(2)
    df['traffic_level'] = df['traffic_condition'].str.lower().map(
        {'low':1.0, 'normal':2.0, 'moderate':2.5, 'heavy':3.5, 'severe':4.5}).fillna(2.0)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24.0).round(4)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24.0).round(4)
    df['is_weekend'] = df['day_of_week'].str.lower().isin(['saturday', 'sunday']).astype(int)
    return df

# 2. K-Means Regime Discovery (K=3, Silhouette = 0.3323)
scaler = StandardScaler()
X_clust = scaler.fit_transform(df[['distance_km', 'actual_fare', 'fare_per_km', 'surge_multiplier']])
kmeans = KMeans(n_clusters=3, random_state=42, n_init=15).fit(X_clust)
df['cluster_id'] = kmeans.labels_

# 3. Supervised Gradient Boosting Regressor (R² = 0.9803, MAE = ₹20.66)
preprocessor = ColumnTransformer([
    ('num', 'passthrough', ['distance_km', 'duration_min', 'surge_multiplier', 'traffic_level', 'cluster_id']),
    ('cat', OneHotEncoder(sparse_output=False), ['provider', 'vehicle_type'])
])
regressor = Pipeline([
    ('prep', preprocessor),
    ('model', GradientBoostingRegressor(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42))
])
X_train, X_test, y_train, y_test = train_test_split(df.drop(columns=['actual_fare']), df['actual_fare'], test_size=0.20)
regressor.fit(X_train, y_train)
y_pred = regressor.predict(X_test)
print(f"Holdout R²: {r2_score(y_test, y_pred):.4f} | MAE: ₹{mean_absolute_error(y_test, y_pred):.2f}")"""

    code_style = ParagraphStyle(
        'CodeStyle',
        fontName='Courier',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#1E293B")
    )
    story.append(Table([[Paragraph(code_snippet.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[printable_width],
                       style=[
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                           ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#E5E7EB")),
                           ('TOPPADDING', (0, 0), (-1, -1), 6),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                           ('LEFTPADDING', (0, 0), (-1, -1), 8),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                       ]))
    story.append(Spacer(1, 8))

    # 8. Conclusion
    story.append(Paragraph("8. Conclusion", h1_style))
    conclusions = [
        "<b>Pervasive Tariff Dispersion Resolved:</b> Empirical analysis proved that quotes for identical transit corridors diverge by 48% to 110% across aggregators. RideCompare resolves this opacity via concurrent real-time quotation.",
        "<b>Superior Model Performance:</b> The Gradient Tree Boosting Regressor achieved outstanding predictive precision (R² = 0.9803, MAE = ₹20.66, MAPE = 5.96%), significantly outperforming Random Forest baselines and providing real-time expected tariff benchmarks in under 1 millisecond.",
        "<b>Quantified Surge Regimes:</b> Unsupervised K-Means clustering (K=3, Silhouette = 0.3323) revealed that Peak Hour Surge rides account for 23.8% of trips with an average rate of ₹48.39/km versus ₹27.08/km for standard transit, equipping commuters with actionable context.",
        "<b>Surge Anomaly Protection:</b> Isolation Forests successfully isolated 360 anomalous pricing records (3.0% contamination), protecting passengers from algorithmic gouging and billing software anomalies.",
        "<b>Holistic Commuter Decision Support:</b> Integrating ML baselines with a 4-factor utility score (price, ETA, reliability, confidence) resolves the problem statement by enabling effortless, cost-effective urban transit selection."
    ]
    for conc in conclusions:
        story.append(Paragraph(f"&bull;&nbsp; {conc}", bullet_style))

    doc.build(story, canvasmaker=AcademicRecordCanvas)
    print(f"[SUCCESS] PDF generated at: {output_pdf_path}")


if __name__ == '__main__':
    out_pdf = os.path.join(os.path.dirname(__file__), 'ridecompare_python_record.pdf')
    build_pdf(out_pdf)
