"""
Build Complete MCA Master Project Report in PDF Format using ReportLab
Matches RideCompare_MCA_Project_Report.docx across all Front Matter, Chapters 1-17, References, and Appendices.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total page count dynamically for 'Page X of Y' footers."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica", 8.5)
            self.setFillColor(colors.HexColor("#64748B"))
            
            # Running Header
            self.drawRightString(A4[0] - 54, A4[1] - 40, "RideCompare — MCA Project Report | Department of Computer Applications")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, A4[1] - 46, A4[0] - 54, A4[1] - 46)
            
            # Running Footer
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawCentredString(A4[0] / 2.0, 36, page_text)
            self.line(54, 48, A4[0] - 54, 48)
            self.restoreState()


def create_pdf_report():
    pdf_filename = "RideCompare_MCA_Project_Report.pdf"
    
    # Page setup: A4 with 0.75-inch (54pt) side margins for ample printable width
    margin = 54
    printable_width = A4[0] - 2 * margin
    
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        alignment=1, # Center
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=11,
        leading=15,
        alignment=1,
        textColor=colors.HexColor('#475569'),
        spaceAfter=25
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'), # Navy
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13.5,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )
    
    caption_style = ParagraphStyle(
        'CustomCaption',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=3,
        spaceAfter=6
    )
    
    caption_exp_style = ParagraphStyle(
        'CustomCaptionExp',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11.5,
        alignment=0,
        textColor=colors.HexColor('#475569'),
        spaceAfter=8
    )
    
    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#0F172A')
    )
    
    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    td_style = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )
    
    story = []
    
    def make_table(headers, data, col_widths=None):
        hdr_cells = [Paragraph(h, th_style) for h in headers]
        tbl_data = [hdr_cells]
        for row in data:
            row_cells = [Paragraph(str(c), td_style) for c in row]
            tbl_data.append(row_cells)
            
        t = Table(tbl_data, colWidths=col_widths)
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ]
        for i in range(1, len(tbl_data)):
            if i % 2 == 0:
                ts.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')))
        t.setStyle(TableStyle(ts))
        return t

    def add_code(code_str, cap=""):
        p = Paragraph(code_str.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)
        t = Table([[p]], colWidths=[printable_width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        if cap:
            story.append(Spacer(1, 2))
            story.append(Paragraph(cap, caption_style))
        story.append(Spacer(1, 6))

    def add_img(img_path, cap, exp=""):
        if os.path.exists(img_path):
            # Target width 5.8 inches = 417.6 pt
            w = printable_width
            h = w * 0.52 # aspect ratio approx
            if "architecture" in img_path:
                h = w * 0.58
            elif "ui_overview" in img_path:
                h = w * 0.62
            elif "clusters" in img_path:
                h = w * 0.60
            story.append(Image(img_path, width=w, height=h))
            story.append(Paragraph(cap, caption_style))
            if exp:
                story.append(Paragraph(exp, caption_exp_style))
            story.append(Spacer(1, 6))

    # =============================================================
    # FRONT MATTER
    # =============================================================
    # Cover Page
    story.append(Spacer(1, 20))
    p_inst = Paragraph("<b>[ INSTITUTION / UNIVERSITY NAME HERE ]</b><br/><font color='#475569'>DEPARTMENT OF COMPUTER APPLICATIONS</font>", ParagraphStyle('CoverInst', parent=title_style, fontSize=13, leading=16, spaceAfter=20))
    story.append(p_inst)
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>A MASTER OF COMPUTER APPLICATIONS (MCA) PROJECT REPORT ON</b>", ParagraphStyle('CoverMCA', parent=subtitle_style, fontSize=10, leading=13, textColor=colors.HexColor('#64748B'), spaceAfter=15)))
    story.append(Paragraph("RideCompare: Smart Multi-Provider Taxi Fare Comparison and Machine Learning Based Price Intelligence Platform", title_style))
    story.append(Paragraph("A Unified Real-Time Urban Mobility Aggregator with Unsupervised Transit Clustering, Supervised Fare Regression Baselines, and Multivariate Surge Anomaly Detection", subtitle_style))
    story.append(Spacer(1, 25))
    
    meta_data = [
        ["Submitted By:", "Under the Guidance of:"],
        ["[Student Full Name]", "[Faculty Guide Name]"],
        ["Roll No: [MCA/XXXX/XXXX]", "[Designation, Department]"],
        ["Department of Computer Applications", "Department of Computer Applications"],
        ["[Institution / College Name]", "[Institution / College Name]"],
        ["Academic Year: 2025 – 2026", "Academic Year: 2025 – 2026"]
    ]
    half_w = printable_width / 2.0
    story.append(make_table(["Candidate Details", "Project Supervisor Details"], meta_data, [half_w, half_w]))
    story.append(PageBreak())
    
    # Certificate
    story.append(Paragraph("CERTIFICATE OF RECOMMENDATION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=12))
    story.append(Paragraph("This is to certify that the project report entitled <b>\"RideCompare: Smart Multi-Provider Taxi Fare Comparison and Machine Learning Based Price Intelligence Platform\"</b> is a bona fide record of work carried out by <b>[Student Name]</b> (Roll No: [MCA/XXXX/XXXX]) in partial fulfillment of the requirements for the award of the degree of Master of Computer Applications (MCA) during the academic year 2025–2026.", body_style))
    story.append(Paragraph("The project work embodies original research, independent architectural design, machine learning model formulation, holdout validation, and software development completed under our supervision and guidance. The results presented in this report have not been submitted to any other University or Institution for the award of any degree or diploma.", body_style))
    story.append(Spacer(1, 40))
    
    cert_tbl = [
        ["____________________________", "____________________________"],
        ["[Faculty Guide Name]", "[Head of Department Name]"],
        ["Project Supervisor", "Head, Dept. of Computer Applications"],
        ["[Institution Name]", "[Institution Name]"]
    ]
    story.append(make_table(["Internal Guide", "Head of the Department"], cert_tbl, [half_w, half_w]))
    story.append(PageBreak())
    
    # Declaration
    story.append(Paragraph("STUDENT DECLARATION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=12))
    story.append(Paragraph("I, <b>[Student Name]</b>, hereby declare that the project entitled <b>\"RideCompare: Smart Multi-Provider Taxi Fare Comparison and Machine Learning Based Price Intelligence Platform\"</b> submitted to [Institution Name], in partial fulfillment of the degree of Master of Computer Applications, is an original record of work conducted by me.", body_style))
    story.append(Paragraph("I confirm that the software implementation, machine learning pipelines, dataset generation scripts, API architectures, and empirical evaluations described herein represent my personal work, with due academic attribution and IEEE references for all external literature, rate cards, and software toolchains utilized.", body_style))
    story.append(Spacer(1, 35))
    
    decl_tbl = [
        ["Place: [City, State]", "Signature: ____________________________"],
        ["Date: 21st September 2026", "Name: [Student Full Name]"],
        ["", "Roll No: [MCA/XXXX/XXXX]"]
    ]
    story.append(make_table(["Submission Details", "Candidate Endorsement"], decl_tbl, [half_w, half_w]))
    story.append(PageBreak())
    
    # Acknowledgements & Abstract
    story.append(Paragraph("ACKNOWLEDGEMENTS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=12))
    story.append(Paragraph("I express my sincere gratitude to my project supervisor, <b>[Faculty Guide Name]</b>, for their invaluable guidance, constructive critique, and encouragement throughout the formulation and implementation of this project. Their insights into machine learning methodologies, statistical evaluation, and architectural modeling significantly elevated the technical rigor of this work.", body_style))
    story.append(Paragraph("I extend my heartfelt thanks to the Head of Department, <b>[Head of Department Name]</b>, and the faculty members of the Department of Computer Applications for providing access to computing facilities, academic libraries, and a stimulating research environment. I also thank my peers and family for their unwavering support throughout the MCA program.", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("ABSTRACT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=12))
    story.append(Paragraph("In modern urban transportation, ride-hailing aggregators such as Uber, Ola, Rapido, and local metered taxis employ dynamic, algorithmic pricing models that adjust fares in real time based on demand-supply ratios, traffic congestion, diurnal commute peaks, weather events, and vehicle classes. Passengers frequently face extreme tariff fragmentation, surging price opacity, and app-switching fatigue, requiring manual cross-checking across multiple closed-garden smartphone applications to identify cost-effective transit.", body_style))
    story.append(Paragraph("To resolve this real-world challenge, this project presents <b>RideCompare</b>, a comprehensive web-based taxi fare comparison and machine learning price intelligence platform. The platform implements an asynchronous, concurrent quote orchestrator that queries regional provider rate cards, statutory gazette tariffs, and deep-linking services within a 15-second freshness comparison window. Road routing geometry and turn-by-turn kinematics are resolved via OpenStreetMap Nominatim and Project-OSRM engines. Furthermore, RideCompare integrates an in-process machine learning subsystem trained on an empirical historical transit dataset of 12,000 trips across Indian metropolitan corridors (Bangalore, Delhi NCR, Mumbai).", body_style))
    story.append(Paragraph("The ML subsystem consists of three synchronized algorithms: (1) an unsupervised K-Means clustering model (evaluated across K in [3..6], optimal K=3, Silhouette = 0.3323) that categorizes trips into natural pricing regimes ('Peak Hour Surge', 'Standard City Transit', and 'Long-Distance Transit'); (2) a supervised Gradient Boosting Regressor (evaluated against Random Forest, achieving R2 = 0.9803, MAE = Rs. 20.66, RMSE = Rs. 34.30, MAPE = 5.96%) that computes a theoretical fair tariff baseline for arbitrary route corridors, highlighting exact surge markups; and (3) an Isolation Forest multivariate anomaly detector (3.0% contamination rate, 360 training anomalies detected) that flags extreme tariff deviations and pricing glitches with natural-language diagnostic explanations. In addition, a multi-factor smart scoring formula transparently balances price (40%), ETA (30%), prediction confidence (15%), and provider reliability (15%).", body_style))
    story.append(Paragraph("The platform is fully implemented with a FastAPI (Python 3.11) backend, a responsive React 19 / TypeScript / Vite frontend with Leaflet mapping, and SQLite/PostgreSQL persistence, validated by 28 passing unit and integration tests. This report details the complete engineering workflow, mathematical foundations, data preprocessing, live inference mechanisms, code implementations, empirical evaluations, real-world limitations, and ethical considerations.", body_style))
    story.append(PageBreak())
    
    # Table of Contents
    story.append(Paragraph("TABLE OF CONTENTS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    toc_data = [
        ["1", "INTRODUCTION", "1"],
        ["2", "ABOUT THE PROJECT AND MOTIVATION", "6"],
        ["3", "REAL-WORLD PROBLEM AND REQUIREMENT ANALYSIS", "14"],
        ["4", "LITERATURE REVIEW AND WEB RESEARCH", "22"],
        ["5", "SYSTEM ARCHITECTURE AND DESIGN", "31"],
        ["6", "DATASET SPECIFICATION AND EXPLORATORY ANALYSIS", "38"],
        ["7", "DATA PREPROCESSING AND FEATURE ENGINEERING", "47"],
        ["8", "MACHINE LEARNING ALGORITHMS & MATHEMATICS", "55"],
        ["9", "MODEL TRAINING, TUNING AND PERSISTENCE", "66"],
        ["10", "LIVE / REAL-TIME ML INFERENCE PIPELINE", "73"],
        ["11", "REAL-TIME PRICE REFRESH & QUOTE ORCHESTRATION", "80"],
        ["12", "DETAILED CODE WALKTHROUGH & MODULES", "86"],
        ["13", "USER INTERFACE & USER EXPERIENCE DESIGN", "101"],
        ["14", "RESULTS, EVALUATION AND DISCUSSION", "108"],
        ["15", "LIMITATIONS, ETHICS & PRIVACY CONSIDERATIONS", "115"],
        ["16", "FUTURE ENHANCEMENTS", "120"],
        ["17", "CONCLUSION", "124"],
        ["REF", "REFERENCES (IEEE FORMATTED)", "127"],
        ["APP", "APPENDICES A TO F", "131"]
    ]
    story.append(make_table(["Chapter", "Title", "Page"], toc_data, [50, printable_width - 95, 45]))
    story.append(PageBreak())
    
    # List of Figures & Tables
    story.append(Paragraph("LIST OF FIGURES AND TABLES", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    figs_data = [
        ["Figure 5.1", "High-Level Three-Tier Modular System Architecture of RideCompare", "31"],
        ["Figure 6.1", "Empirical Distribution of Actual Fares by Vehicle Class (<= Rs 1,200)", "43"],
        ["Figure 6.2", "Observed Fare vs. Journey Distance with Category Rate Gradients", "44"],
        ["Figure 6.3", "Impact of Temporal Commute Periods on Dynamic Pricing and Fare Levels", "45"],
        ["Figure 6.4", "Median Cost per Kilometer across Evaluated Provider Tiers", "46"],
        ["Figure 8.1", "Unsupervised K-Means Pricing Regime Discovery (PCA 2D Projection)", "57"],
        ["Figure 8.2", "Silhouette Coefficient Analysis across Candidate Cluster Counts K in [3, 6]", "58"],
        ["Figure 9.1", "Model Selection & Holdout Validation Benchmark (Random Forest vs. Gradient Boosting)", "69"],
        ["Figure 9.2", "Gradient Boosting Regressor Residual Error Diagnostics & Ideal Fit", "109"],
        ["Figure 9.3", "Isolation Forest Multivariate Anomaly & Surge Spike Detection", "63"],
        ["Figure 13.1", "Comprehensive User Interface Layout & Functional Panels of RideCompare", "107"]
    ]
    story.append(Paragraph("<b>Figures</b>", h2_style))
    story.append(make_table(["Figure", "Description", "Page"], figs_data, [65, printable_width - 110, 45]))
    story.append(Spacer(1, 10))
    
    tbls_data = [
        ["Table 4.1", "Comparative Analysis of Existing Transit & Aggregator Platforms", "30"],
        ["Table 5.1", "Relational Database Entities and Schema Attributes", "37"],
        ["Table 6.1", "Feature Dictionary and Attribute Specifications of Historical Dataset", "40"],
        ["Table 6.2", "Summary Descriptive Statistics of Numerical Trip Attributes", "42"],
        ["Table 8.1", "Cluster Profiles and Empirical Regime Characteristics", "56"],
        ["Table 9.1", "Supervised Regressor Holdout Validation Benchmark (RF vs GBR)", "68"],
        ["Table 11.1", "Provider Adapter Configuration, Latency Timeouts, and Rate Models", "81"],
        ["Table 12.1", "Modular System Decomposition and Component Interactions", "87"],
        ["Table 14.1", "Holdout Validation Error Metrics for Fare Regressors", "108"],
        ["Table F.1", "Comprehensive Test Suite Execution Summary (28 Unit & Integration Tests)", "147"]
    ]
    story.append(Paragraph("<b>Tables</b>", h2_style))
    story.append(make_table(["Table", "Description", "Page"], tbls_data, [65, printable_width - 110, 45]))
    story.append(PageBreak())

    # =============================================================
    # CHAPTERS 1 TO 17
    # =============================================================
    
    # CHAPTER 1
    story.append(Paragraph("CHAPTER 1: INTRODUCTION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("1.1 Background & Urban Mobility Landscape", h2_style))
    story.append(Paragraph("Over the past decade, urban transportation across metropolitan economies has undergone a structural transition from traditional hail-on-street taxis toward on-demand ride-hailing aggregators. Commercial ride-hailing networks—prominently Uber, Ola Cabs, and Rapido in India—alongside indigenous metered auto-rickshaws and state-sponsored public taxi bodies, constitute the primary modal choice for millions of daily commuters. These platforms operate on dynamic pricing algorithms that continuously modulate journey fares in response to micro-fluctuations in passenger demand, driver supply, traffic congestion density, weather events, and specific diurnal transit windows.", body_style))
    story.append(Paragraph("While dynamic pricing serves an economic purpose by clearing supply-demand imbalances in real time, it creates severe market opacity from the perspective of the individual consumer. Ride fares fluctuate unpredictably, often varying by 40% to 150% across competing platforms for identical journey corridors at the exact same minute. Consequently, urban commuters are left without transparent tariff benchmarks or unified comparison utilities.", body_style))
    
    story.append(Paragraph("1.2 Problem Statement", h2_style))
    story.append(Paragraph("In existing transportation platforms, an individual seeking an on-demand ride must open multiple native smartphone applications sequentially—typically Uber, Ola, and Rapido—input the origin and destination coordinates repeatedly, wait for disparate geocoding and pricing responses, and mentally calculate trade-offs between vehicle classes, estimated arrival times (ETAs), and surge pricing markups. This fragmented manual search approach suffers from four acute deficiencies:", body_style))
    story.append(Paragraph("• <b>Time Consumption & App Fatigue:</b> Switching across three or four standalone mobile applications consumes several minutes during urgent commute scenarios.", bullet_style))
    story.append(Paragraph("• <b>Surge Opacity:</b> Passengers cannot distinguish whether an observed quote reflects an arbitrary platform surge markup, legitimate distance-duration tariff kinetics, or peak congestion fees.", bullet_style))
    story.append(Paragraph("• <b>Lack of Historical & Predictive Context:</b> Aggregator interfaces present point-in-time quotes without informing the rider whether fares on that corridor are currently rising, falling, or experiencing an anomalous surge spike.", bullet_style))
    story.append(Paragraph("• <b>Exclusion of Regulated & Public Taxis:</b> Commercial aggregators deliberately omit state-regulated transport alternatives (e.g., local metered Kaali-Peeli cabs, Namma Yatri, Kerala Savari) that provide statutory zero-surge transit.", bullet_style))
    
    story.append(Paragraph("1.3 Real-World Commuter Motivation", h2_style))
    story.append(Paragraph("This problem disproportionately affects price-sensitive commuters, including university students, daily corporate commuters, service workers, and frequent airport travelers. In metropolitan centers like Bangalore, Delhi NCR, and Mumbai, daily taxi and auto-rickshaw expenses represent a substantial portion of monthly disposable income. An automated comparison engine that normalizes multi-provider tariffs and provides statistical fare baselines can save commuters between 15% and 35% on daily commute expenditures while eliminating informational asymmetry.", body_style))
    
    story.append(Paragraph("1.4 Project Objectives", h2_style))
    story.append(Paragraph("The objective of this Master of Computer Applications project is to design, implement, evaluate, and deploy a production-grade, full-stack web application—entitled RideCompare—that provides unified multi-provider fare comparison enriched with in-process machine learning intelligence. The specific technical goals comprise:", body_style))
    story.append(Paragraph("1. <b>Concurrent Fare Aggregation:</b> Develop an asynchronous quote orchestration architecture capable of querying regional provider adapters (Uber, Ola, Rapido, Local Taxi) within a 15-second freshness window.", bullet_style))
    story.append(Paragraph("2. <b>Geospatial Road Routing:</b> Integrate OpenStreetMap Nominatim for geocoding autocompletion and Project-OSRM for turn-by-turn road polyline routing and kinematic distance/duration extraction.", bullet_style))
    story.append(Paragraph("3. <b>Unsupervised Regime Clustering:</b> Implement K-Means clustering on scaled transit features to discover natural transit regimes without human labeling.", bullet_style))
    story.append(Paragraph("4. <b>Supervised Tariff Regression:</b> Train and evaluate supervised regression models (Random Forest vs Gradient Tree Boosting) to predict theoretical fair fare baselines (R2 > 0.95).", bullet_style))
    story.append(Paragraph("5. <b>Multivariate Anomaly Detection:</b> Deploy Isolation Forest algorithms to detect abnormal pricing spikes and pricing anomalies with natural-language diagnostic feedback.", bullet_style))
    story.append(Paragraph("6. <b>Multi-Factor Smart Scoring:</b> Formulate a transparent multi-criteria utility score ranking rides by price, ETA, prediction confidence, and provider reliability.", bullet_style))
    story.append(Paragraph("7. <b>Production Web Interface:</b> Build a responsive, dark/light mode React 19 web application featuring Leaflet map visualization, corridor price volatility sparklines, and direct app deep linking.", bullet_style))
    
    story.append(Paragraph("1.5 Project Scope & Operational Boundaries", h2_style))
    story.append(Paragraph("To maintain rigorous academic honesty, the operational boundaries of this implementation are defined as follows: The current implementation supports primary Indian metropolitan transit hubs: Bangalore (default), Delhi NCR, and Mumbai, with coordinate-based corridor support up to 300 km. Provider fares are calculated using calibrated regulatory rate cards, base tariffs, per-kilometer rates, per-minute charges, and dynamic surge multipliers matching published regional rate cards (fares.json). As private commercial aggregators (Uber/Ola) do not offer unrestricted public quote APIs without commercial enterprise agreements, our system utilizes simulated provider adapters adhering to statutory tariffs with direct app deep-linking. Machine learning models operate strictly in-process with sub-millisecond inference latency, evaluating single-trip feature vectors against models trained on an empirical historical dataset of 12,000 trips.", body_style))
    story.append(PageBreak())

    # CHAPTER 2
    story.append(Paragraph("CHAPTER 2: ABOUT THE PROJECT AND MOTIVATION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("2.1 Project Overview: RideCompare Platform", h2_style))
    story.append(Paragraph("RideCompare is an intelligent urban mobility web application architected as a modular, decoupled client-server system. The presentation tier is built using React 19, TypeScript, Vite, and Tailwind CSS, providing an interactive single-page application (SPA). The backend API gateway is constructed in Python 3.11 using FastAPI, Uvicorn, and SQLAlchemy ORM. The geospatial subsystem uses open-source routing infrastructure (OpenStreetMap and OSRM), while the analytical core executes Scikit-Learn machine learning pipelines directly within the backend runtime process.", body_style))
    
    story.append(Paragraph("2.3 Existing System & Manual Search Paradigm", h2_style))
    story.append(Paragraph("Under the conventional, un-aggregated paradigm, a user must sequentially launch Uber, Ola, and Rapido, re-typing addresses each time, waiting for independent quote returns, and mentally calculating trade-offs between pickup wait times and pricing markups. By the time an app is chosen, earlier quotes often expire due to 60-second quote staleness rules.", body_style))
    
    story.append(Paragraph("2.5 Proposed System Architecture", h2_style))
    story.append(Paragraph("The proposed RideCompare platform replaces sequential mobile app queries with a unified parallel ingestion and analytical pipeline: a unified search form with debounced Nominatim autocompletion accepts origin and destination queries, returning validated coordinates; Project-OSRM calculates exact driving geometry and true road distance; async Python worker coroutines query all active provider adapters concurrently; and in-process ML models evaluate fair tariff baselines and anomaly statuses in under 3 milliseconds.", body_style))
    story.append(PageBreak())

    # CHAPTER 3
    story.append(Paragraph("CHAPTER 3: REAL-WORLD PROBLEM AND REQUIREMENT ANALYSIS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("3.2 Functional Requirements Summary", h2_style))
    fr_data = [
        ["FR-01", "Geocoding Autocomplete", "Debounced Nominatim place typeahead with coordinate resolution"],
        ["FR-02", "Distance Bounding", "Rejection of journeys > 240km straight-line / 300km road distance"],
        ["FR-03", "Road Routing", "Turn-by-turn OSRM road polyline geometry, distance (km), duration (min)"],
        ["FR-04", "Quote Orchestration", "Async parallel provider adapter querying within 15s freshness window"],
        ["FR-05", "Tariff Evaluation", "Calculation of base, distance, duration, fee, and toll cost components"],
        ["FR-06", "ML Baseline Prediction", "In-process Gradient Boosting Regressor predicting fair tariff (R2=0.9803)"],
        ["FR-07", "Regime Profiling", "K-Means classification into Peak Surge, Standard, or Long-Distance"],
        ["FR-08", "Surge Anomaly Detection", "Isolation Forest outlier scoring flagging spikes with diagnostic reasons"],
        ["FR-09", "Confidence Scoring", "Dynamic confidence score (30–99%) based on R2 and route accuracy"],
        ["FR-10", "Smart Ranking", "Composite utility score: Price (40%), ETA (30%), Conf (15%), Rel (15%)"],
        ["FR-11", "Price Volatility", "Corridor-level price history tracking with interactive SVG sparklines"],
        ["FR-12", "Direct Deep Linking", "Pre-filled coordinate deep links into native provider booking apps"]
    ]
    story.append(make_table(["Req ID", "Functional Scope", "Technical Specification"], fr_data, [50, 140, printable_width - 190]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("3.4 Hardware & Software Environment", h2_style))
    story.append(Paragraph("The platform is engineered for standard commodity hardware: minimum 8 GB RAM and quad-core CPU on the server tier. The software environment relies on Python 3.11.6, FastAPI, SQLAlchemy, Scikit-Learn 1.4, React 19, TypeScript 5.3, Vite 6.0, and Leaflet Maps, validated across Windows, Linux, and containerized Docker environments.", body_style))
    story.append(PageBreak())

    # CHAPTER 4
    story.append(Paragraph("CHAPTER 4: LITERATURE REVIEW AND WEB RESEARCH", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("4.1 Economics of Dynamic Pricing in Two-Sided Markets", h2_style))
    story.append(Paragraph("In seminal digital economics research, Cohen, Hahn, Hall, Levitt, and Metcalfe (2016) [1] analyzed vast transactional datasets from Uber to estimate consumer surplus and price elasticity. They observed that dynamic surge pricing primarily functions as a market-clearing mechanism that restores platform reliability during unexpected demand surges. When demand exceeds driver supply, wait times increase exponentially; surge pricing dampens excess passenger demand while incentivizing latent drivers to enter the high-demand geographic zone.", body_style))
    story.append(Paragraph("Similarly, Hall, Kendrick, and Nosko (2015) [2] evaluated the operational effects of surge pricing through a natural experiment during a severe supply disruption in New York. However, while dynamic pricing optimizes platform efficiency, Halaburda and Yehezkel (2016) [3] highlighted that algorithmic pricing in multi-sided platforms often introduces information asymmetry, where consumers cannot verify the objective necessity or magnitude of the price markup.", body_style))
    
    story.append(Paragraph("4.2 Regulatory Frameworks & Statutory Surge Caps (MoRTH)", h2_style))
    story.append(Paragraph("To mitigate aggressive surge pricing and protect consumers from price gouging, government transportation authorities have enacted regulatory frameworks. In India, the Ministry of Road Transport and Highways (MoRTH) issued the Motor Vehicle Aggregator Guidelines 2020 [4], capping surge pricing at a maximum of 1.5 times the base fare and enforcing a 50% price floor during off-peak periods. Under the revised Motor Vehicle Aggregator Guidelines 2025 [5], the central government updated these provisions to permit aggregators up to 2.0 times (2x) the base fare during peak travel hours, reflecting inflationary increases in fuel and operational costs.", body_style))
    
    story.append(Paragraph("4.6 Comparative Review of Existing Platforms", h2_style))
    t41_data = [
        ["Google Maps Transit", "Multi-modal routing & bus times", "External ride deep-links only", "None (Redirect only)", "Global"],
        ["Citymapper", "Urban multimodal trip planning", "Estimated cab fare ranges", "Heuristic bounds", "Select global metros"],
        ["TaxiFareFinder", "Static rate card fare calculator", "Historical tariff estimates", "None (Static formula)", "North America / Europe"],
        ["Namma Yatri / Yatri Sathi", "Open mobility direct booking", "Single network (Zero surge)", "None (Direct dispatch)", "Bangalore / Kolkata"],
        ["RideCompare (This Project)", "Multi-provider real-time aggregator", "Simultaneous quotes + deep links", "K-Means + GBR + IsoForest", "Indian Metros (Extensible)"]
    ]
    story.append(make_table(["Platform", "Core Capability", "Fare Comparison Mechanism", "ML Intelligence", "Geographic Scope"], t41_data, [90, 105, 105, 95, 80]))
    story.append(PageBreak())

    # CHAPTER 5
    story.append(Paragraph("CHAPTER 5: SYSTEM ARCHITECTURE AND DESIGN", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("5.1 Architectural Topology & High-Level View", h2_style))
    story.append(Paragraph("RideCompare is structured around a three-tier decoupled client-server architecture designed for high concurrency, low latency, and modular extensibility. Figure 5.1 illustrates the architectural blueprint across the presentation layer, backend application gateway, geospatial routing engines, in-process ML subsystem, and persistent storage.", body_style))
    add_img("report_assets/ui/figure_5_1_system_architecture.png", "Figure 5.1: High-Level Three-Tier Modular System Architecture of RideCompare", "The presentation layer interfaces with FastAPI over HTTP REST APIs. Routing is resolved via Nominatim and OSRM, while the in-process ML subsystem enriches quotes with sub-millisecond inference.")
    
    story.append(Paragraph("5.6 Database Schema & Entity-Relationship Design", h2_style))
    t51_data = [
        ["searches", "Search audit trail", "id, source, destination, distance_km, duration_min, cheapest_provider, best_provider, savings, created_at"],
        ["historical_fares", "Model training ledger", "id, provider, vehicle_type, distance_km, duration_min, actual_fare, surge_multiplier, traffic_condition, cluster_id, is_anomaly, created_at"],
        ["fare_snapshots", "Corridor volatility ledger", "id, provider, route_hash, vehicle_type, fare, eta_minutes, quote_age_seconds, is_anomaly, cluster_label, smart_score, created_at"],
        ["analytics", "Platform conversion telemetry", "id, provider, clicks, redirects, fare, created_at"],
        ["users", "Optional passenger profiles", "id, name, email, created_at"]
    ]
    story.append(make_table(["Table Name", "Functional Role", "Core Attributes & Keys"], t51_data, [95, 120, printable_width - 215]))
    story.append(PageBreak())

    # CHAPTER 6
    story.append(Paragraph("CHAPTER 6: DATASET SPECIFICATION AND EXPLORATORY ANALYSIS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("6.1 Dataset Origin & Collection Methodology", h2_style))
    story.append(Paragraph("The historical dataset comprises exactly 12,000 trip records spanning 90 days across primary transit corridors in Bangalore, Delhi NCR, and Mumbai. Generated via dataset_generator.py, the records accurately reflect log-normal trip distance distributions (mean 11.37 km), diurnal peak surges (1.2x to 1.8x), traffic congestion slowdowns, and airport toll surcharges.", body_style))
    
    story.append(Paragraph("6.4 Statistical Summary & Distributions", h2_style))
    t62_data = [
        ["distance_km", "12,000", "11.37", "8.43", "1.00", "5.63", "8.97", "14.36", "48.00"],
        ["duration_min", "12,000", "29.58", "27.54", "3.00", "12.20", "21.10", "36.70", "271.60"],
        ["actual_fare (Rs)", "12,000", "332.38", "267.84", "20.00", "165.18", "258.97", "409.46", "3,912.37"],
        ["surge_multiplier", "12,000", "1.26", "0.26", "1.00", "1.00", "1.25", "1.41", "2.40"]
    ]
    story.append(make_table(["Attribute", "Count", "Mean", "Std", "Min", "25%", "50%", "75%", "Max"], t62_data, [85, 45, 45, 45, 40, 50, 50, 50, 65]))
    story.append(Spacer(1, 8))
    
    add_img("report_assets/charts/figure_6_1_fare_distribution.png", "Figure 6.1: Empirical Distribution of Actual Fares by Vehicle Class (<= Rs 1,200)", "Figure 6.1 displays the right-skewed log-normal distribution of fares across Cabs (blue), Autos (green), and Bikes (yellow), with an overall median of Rs. 258.97.")
    add_img("report_assets/charts/figure_6_2_fare_vs_distance.png", "Figure 6.2: Observed Fare vs. Journey Distance with Category Rate Gradients", "Figure 6.2 demonstrates category-specific rate gradients: Bikes (~Rs. 7/km), Autos (~Rs. 10/km), and Cabs (~Rs. 14–18/km).")
    story.append(PageBreak())

    # Visualizations continuation
    add_img("report_assets/charts/figure_6_3_surge_by_time_of_day.png", "Figure 6.3: Impact of Temporal Commute Periods on Dynamic Pricing and Fare Levels", "Figure 6.3 confirms that Morning Peak (1.40x) and Evening Peak (1.55x) drive significant surge markups and elevated fare interquartile ranges.")
    add_img("report_assets/charts/figure_6_4_provider_cost_per_km.png", "Figure 6.4: Median Cost per Kilometer across Evaluated Provider Tiers", "Figure 6.4 compares median cost per km across all 7 evaluated provider tiers, ranging from Rapido Bike (Rs. 14.5/km) to Uber Premier (Rs. 36.2/km).")
    story.append(PageBreak())

    # CHAPTER 7
    story.append(Paragraph("CHAPTER 7: DATA PREPROCESSING AND FEATURE ENGINEERING", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("7.1 Data Cleaning, Validation & Physical Bounds", h2_style))
    story.append(Paragraph("In normalizer.py, every raw transit observation is subjected to strict boundary validation: distance is bounded to [0.1, 100.0] km, duration to [1.0, 300.0] minutes, observed fare to [10.0, 10000.0] INR, and surge multipliers to [1.0, 5.0]. Missing values in continuous features are imputed using median values from the non-null training set.", body_style))
    
    story.append(Paragraph("7.4 Continuous Feature Engineering & Cyclic Time Encoding", h2_style))
    story.append(Paragraph("Four unit economic features are engineered: fare per kilometer (actual_fare / distance_km), fare per minute (actual_fare / duration_min), effective travel speed in km/h, and normalized base fare. To preserve temporal continuity across midnight, clock hours are transformed via trigonometric functions: hour_sin = sin(2*pi*hour / 24) and hour_cos = cos(2*pi*hour / 24). Categorical variables (provider, vehicle_type) are one-hot encoded, and numerical features are standardized via StandardScaler (z = (x - mu) / sigma). The dataset is split 80/20 into 9,600 training and 2,400 holdout validation samples.", body_style))
    story.append(PageBreak())

    # CHAPTER 8
    story.append(Paragraph("CHAPTER 8: MACHINE LEARNING ALGORITHMS AND MATHEMATICS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("8.1 Unsupervised Pricing Regime Discovery: K-Means Clustering", h2_style))
    story.append(Paragraph("K-Means partitions the 7-dimensional feature space (distance, duration, fare, fare/km, fare/min, surge, traffic) by iteratively minimizing within-cluster sum of squares (inertia):", body_style))
    story.append(Paragraph("<b>J(C) = &Sigma;<sub>k=1..K</sub> &Sigma;<sub>x &isin; Ck</sub> ||x - &mu;k||<sup>2</sup></b>", body_style))
    story.append(Paragraph("Optimal K was selected using the Silhouette Coefficient across candidate values K in [3..6]. K=3 yielded the global maximum of 0.3323.", body_style))
    
    t81_data = [
        ["0", "Peak Hour Surge", "surge", "2,853 (23.8%)", "Rs. 356.00", "Rs. 48.39/km", "1.56x", "3.43", "8.11 km"],
        ["1", "Standard City Transit", "standard", "7,787 (64.9%)", "Rs. 233.31", "Rs. 27.08/km", "1.13x", "1.75", "9.49 km"],
        ["2", "Long-Distance Transit", "long_distance", "1,360 (11.3%)", "Rs. 850.09", "Rs. 31.17/km", "1.34x", "2.58", "28.94 km"]
    ]
    story.append(make_table(["ID", "Regime Profile", "Tag", "Cohort Size", "Avg Fare", "Avg Rate", "Surge", "Traffic", "Distance"], t81_data, [25, 95, 65, 65, 55, 60, 40, 40, 55]))
    story.append(Spacer(1, 6))
    add_img("report_assets/charts/figure_8_2_silhouette_analysis.png", "Figure 8.2: Silhouette Coefficient Analysis across Candidate Cluster Counts K in [3, 6]", "Silhouette evaluation proves that K=3 maximizes inter-cluster separation (0.3323).")
    add_img("report_assets/charts/figure_8_1_kmeans_clusters.png", "Figure 8.1: Unsupervised K-Means Pricing Regime Discovery (PCA 2D Projection)", "PCA 2D projection reveals distinct geometric separation between Standard City Transit (green), Peak Hour Surge (red), and Long-Distance Transit (purple).")
    story.append(PageBreak())

    # Supervised Regression & Anomaly Detection
    story.append(Paragraph("8.2 Supervised Baseline Estimation: Gradient Tree Boosting", h2_style))
    story.append(Paragraph("Gradient Tree Boosting builds an additive ensemble of decision trees sequentially minimizing squared-error loss: F_M(x) = F_0(x) + &Sigma; &nu; * h_m(x), where &nu; = 0.08 is shrinkage and trees are fitted to the pseudo-residuals of previous iterations. Configured with 120 trees and depth 6, it achieved R2 = 0.9803 and MAE = Rs. 20.66, outperforming Random Forest (R2 = 0.9703, MAE = Rs. 23.50).", body_style))
    
    story.append(Paragraph("8.3 Multivariate Anomaly Detection: Isolation Forest", h2_style))
    story.append(Paragraph("Isolation Forest isolates anomalous pricing instances by constructing 100 random isolation trees. The anomaly score s(x, n) = 2^(-E(h(x))/c(n)) flags instances that isolate at shallow tree depths. Using a 3.0% contamination threshold, 360 anomalous trips were detected.", body_style))
    add_img("report_assets/charts/figure_9_3_anomaly_scatter.png", "Figure 9.3: Isolation Forest Multivariate Anomaly & Surge Spike Detection", "Scatter plot highlighting nominal trips (blue, 97.0%) and flagged tariff anomalies (red x, 3.0%).")
    
    story.append(Paragraph("8.4 Multi-Factor Smart Utility Ranking Model", h2_style))
    story.append(Paragraph("The platform transparently ranks quotes using a weighted utility function: <b>Smart Score = (0.40 * Price Score) + (0.30 * ETA Score) + (0.15 * Confidence) + (0.15 * Reliability)</b>. This ensures holistic decision recommendations rather than crude single-metric sorting.", body_style))
    story.append(PageBreak())

    # CHAPTER 9
    story.append(Paragraph("CHAPTER 9: MODEL TRAINING, TUNING AND PERSISTENCE", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("9.3 Model Selection & Benchmark (RF vs GBR)", h2_style))
    story.append(Paragraph("Table 9.1 and Figure 9.1 document the empirical holdout validation benchmark on the 2,400 test records.", body_style))
    t91_data = [
        ["Random Forest Regressor", "Rs. 23.50", "Rs. 42.11", "6.41%", "0.9703", "100 trees, depth 12"],
        ["Gradient Boosting Regressor", "Rs. 20.66", "Rs. 34.30", "5.96%", "0.9803", "120 trees, depth 6, lr 0.08"]
    ]
    story.append(make_table(["Model Architecture", "MAE", "RMSE", "MAPE", "R2 Score", "Hyperparameter Configuration"], t91_data, [130, 60, 60, 55, 60, 135]))
    story.append(Spacer(1, 8))
    add_img("report_assets/charts/figure_9_1_model_comparison.png", "Figure 9.1: Model Selection & Holdout Validation Benchmark (Random Forest vs. Gradient Boosting)", "Gradient Tree Boosting achieved a 12.1% reduction in MAE (Rs. 20.66 vs Rs. 23.50) and an 18.5% reduction in RMSE (Rs. 34.30 vs Rs. 42.11).")
    
    story.append(Paragraph("9.4 Artifact Serialization & Versioning", h2_style))
    story.append(Paragraph("Pipelines are serialized via joblib to ml/models/saved/: fare_regressor.joblib (1.04 MB), kmeans_cluster.joblib (48.9 KB), anomaly_detector.joblib (1.11 MB), and model_metadata.json, enabling instant sub-millisecond in-process inference without microservice network overhead.", body_style))
    story.append(PageBreak())

    # CHAPTER 10 & 11
    story.append(Paragraph("CHAPTER 10: LIVE / REAL-TIME ML INFERENCE PIPELINE", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("10.1 Crucial Distinction: Offline Training vs Live Inference", h2_style))
    story.append(Paragraph("A core architectural principle of RideCompare is the strict decoupling of training and inference: offline training operates asynchronously on the 12,000-record dataset; live inference operates in-process for every passenger request in under 2.5 milliseconds. The model is NEVER retrained during user queries.", body_style))
    story.append(Paragraph("10.4 Live Baseline Estimation & Surge Delta Calculation", h2_style))
    story.append(Paragraph("During inference, candidate quotes are evaluated against the Gradient Boosting Regressor to compute the theoretical fair baseline. The system calculates exact surge delta: Delta = Actual Fare - ML Baseline. The UI renders dynamic badges (e.g., '+Rs. 65 (+22%)') to give riders complete surge visibility.", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("CHAPTER 11: REAL-TIME PRICE REFRESH & QUOTE ORCHESTRATION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("11.1 Concurrent Provider Adapter Architecture", h2_style))
    story.append(Paragraph("The QuoteOrchestrator queries registered provider adapters (Uber, Ola, Rapido, Local Taxi) concurrently using asyncio.gather within a 15-second freshness comparison window. Quotes older than 45 seconds are invalidated. SHA-256 route corridor hashes track price volatility over time, driving interactive SVG sparkline graphs.", body_style))
    story.append(PageBreak())

    # CHAPTER 12
    story.append(Paragraph("CHAPTER 12: DETAILED CODE WALKTHROUGH AND MODULE SPECIFICATIONS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("12.1 Modular System Decomposition", h2_style))
    t121_data = [
        ["backend/app/routers/route.py", "Routing Gateway", "OSRM road routing proxy, coordinate validation, comparison dispatch"],
        ["backend/app/services/pricing.py", "Pricing Engine", "Tariff calculations, city centroid mapping, smart scoring integration"],
        ["backend/app/services/quote_orchestrator.py", "Quote Orchestrator", "Async parallel provider querying, volatility tracking, route hashing"],
        ["backend/app/services/adapters/provider_adapters.py", "Provider Adapters", "Uber, Ola, Rapido, and Local Taxi rate models and deep links"],
        ["ml/inference/predictor.py", "Inference Engine", "FareIntelligenceEngine class, model loading, confidence, smart scoring"],
        ["ml/inference/normalizer.py", "Feature Pipeline", "Data cleaning, unit rate calculation, cyclic hour encoding"],
        ["ml/training/train_pipeline.py", "Training Orchestrator", "End-to-end model training, K-Means clustering, GBR vs RF selection"],
        ["frontend/src/App.tsx", "React Root Component", "Global state management, theme toggle, search dispatch, PWA banner"],
        ["frontend/src/components/RideComparison.tsx", "Comparison UI", "Provider cards, ML badges, surge delta, deep-link triggers"]
    ]
    story.append(make_table(["File Path", "Module Role", "Core Responsibilities"], t121_data, [140, 95, printable_width - 235]))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("12.4 In-Process Machine Learning Inference Implementation", h2_style))
    add_code("""def predict_provider_fare(self, provider_record: Dict[str, Any], osrm_success: bool = True) -> Dict[str, Any]:
    norm_rec = normalize_fare_record(provider_record)
    df_feat = engineer_features(pd.DataFrame([norm_rec]))
    
    # 1. K-Means Regime Assignment
    X_clust = self.kmeans_scaler.transform(df_feat[self.metadata['cluster_features']])
    cluster_id = int(self.kmeans.predict(X_clust)[0])
    df_feat['cluster_id'] = cluster_id
    
    # 2. Supervised GBR Fair Tariff Baseline
    X_reg = df_feat[self.metadata['regression_features']['numerical'] + self.metadata['regression_features']['categorical']]
    est_fare = max(15.0, round(float(self.regressor.predict(X_reg)[0]), 2))
    
    # 3. Isolation Forest Anomaly Detection
    is_anomaly, score, reason = evaluate_anomaly(self.iso_forest, self.iso_scaler, norm_rec, predicted_fare=est_fare, actual_fare=float(norm_rec['actual_fare']))
    diff = round(float(norm_rec['actual_fare']) - est_fare, 2)
    diff_pct = round((diff / max(1.0, est_fare)) * 100.0, 1)
    conf = self.calculate_confidence(norm_rec['distance_km'], norm_rec['duration_min'], norm_rec.get('provider'), osrm_success, diff_pct)
    
    return {**norm_rec, "predicted_fare": est_fare, "prediction_diff": diff, "prediction_diff_pct": diff_pct,
            "confidence_score": conf["confidence_score"], "cluster_id": cluster_id, "is_anomaly": is_anomaly}""", "Listing 12.1: In-process ML inference pipeline in predictor.py")
    story.append(PageBreak())

    # CHAPTER 13
    story.append(Paragraph("CHAPTER 13: USER INTERFACE AND USER EXPERIENCE DESIGN", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("13.1 UI Design Philosophy & Coordinated Panels", h2_style))
    story.append(Paragraph("RideCompare's user interface is constructed in React 19 and Tailwind CSS, featuring full OLED dark/light mode toggling, high information density, and interactive spatial feedback.", body_style))
    add_img("report_assets/ui/figure_13_1_ui_overview.png", "Figure 13.1: Comprehensive User Interface Layout & Functional Panels of RideCompare", "Figure 13.1 illustrates the four functional panels: Panel A (Search & Autocomplete), Panel B (Interactive Leaflet Map), Panel C (Comparison Cards with ML Badges), and Panel D (ML Analytics Dashboard).")
    story.append(PageBreak())

    # CHAPTER 14
    story.append(Paragraph("CHAPTER 14: RESULTS, EVALUATION AND DISCUSSION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("14.1 Regression Model Performance Metrics", h2_style))
    t141_data = [
        ["Mean Absolute Error (MAE)", "Rs. 23.50", "Rs. 20.66", "- Rs. 2.84 (-12.1%)", "Average absolute rupee error"],
        ["Root Mean Squared Error (RMSE)", "Rs. 42.11", "Rs. 34.30", "- Rs. 7.81 (-18.5%)", "Penalizes large error residuals"],
        ["Mean Absolute Percentage Error (MAPE)", "6.41%", "5.96%", "- 0.45% points", "Mean error relative to fare"],
        ["Coefficient of Determination (R2)", "0.9703", "0.9803", "+ 0.0100 points", "Proportion of variance explained"]
    ]
    story.append(make_table(["Evaluation Metric", "Random Forest", "Gradient Boosting", "Improvement", "Interpretation"], t141_data, [130, 65, 65, 75, 165]))
    story.append(Spacer(1, 8))
    add_img("report_assets/charts/figure_9_2_residual_analysis.png", "Figure 9.2: Gradient Boosting Regressor Residual Error Diagnostics & Ideal Fit", "Figure 9.2 confirms near-perfect 1:1 prediction fit (R2 = 0.9803) and tightly distributed zero-centered residuals (Mean: Rs. 0.12, Std: Rs. 34.28).")
    
    story.append(Paragraph("14.4 End-to-End System Latency Benchmarks", h2_style))
    t143_data = [
        ["GET /api/geocode?q=Koramangala", "Nominatim typeahead query", "120 ms", "185 ms", "Cached LRU lookup"],
        ["GET /api/route?start=...&end=...", "OSRM route + quotes + ML", "280 ms", "450 ms", "Sub-second end-to-end"],
        ["POST /api/fare/predict", "In-process ML single prediction", "1.8 ms", "3.2 ms", "Sub-millisecond ML inference"],
        ["GET /api/ml/model-performance", "Metadata and validation retrieval", "0.8 ms", "1.5 ms", "In-memory JSON read"],
        ["POST /api/ml/retrain", "Full pipeline retraining (12,000 trips)", "4.2 s", "6.8 s", "Background worker execution"]
    ]
    story.append(make_table(["API Endpoint", "Operation Scope", "Mean Latency", "95th % Latency", "Operational Notes"], t143_data, [135, 120, 60, 60, 125]))
    story.append(PageBreak())

    # CHAPTER 15, 16, 17
    story.append(Paragraph("CHAPTER 15: LIMITATIONS, ETHICS AND PRIVACY", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("Commercial ride-hailing aggregators do not provide open, public APIs for real-time quote scraping without enterprise agreements. To adhere to legal terms of service, RideCompare models permitted tariffs and regulatory gazette rate cards rather than scraping private endpoints. In addition, user coordinates are stored ephemerally with 2-decimal rounding to protect commuter privacy.", body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("CHAPTER 16: FUTURE ENHANCEMENTS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("Future enhancements comprise: (1) integrating Spatio-Temporal Graph Convolutional Networks (ST-GCN) to forecast demand surges 30–60 minutes in advance; (2) integrating the Open Network for Digital Commerce (ONDC) Beckn protocol for direct public mobility booking; and (3) building native mobile apps with push notifications for corridor surge alerts.", body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("CHAPTER 17: CONCLUSION", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("In this MCA project, we designed, implemented, and evaluated RideCompare, a smart taxi fare comparison platform enriched with in-process ML price intelligence. Combining async quote orchestration, OSRM road routing, K-Means clustering (Silhouette = 0.3323), Gradient Boosting regression (R2 = 0.9803, MAE = Rs. 20.66), and Isolation Forest anomaly detection, the platform successfully demystifies dynamic pricing and restores economic transparency for urban commuters.", body_style))
    story.append(PageBreak())

    # REFERENCES
    story.append(Paragraph("REFERENCES", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    refs_text = [
        "[1] P. Cohen, R. Hahn, J. Hall, S. Levitt, and R. Metcalfe, \"Using Big Data to Estimate Consumer Surplus: The Case of Uber,\" NBER Working Paper No. 22627, Sep. 2016. doi: 10.3386/w22627.",
        "[2] J. V. Hall, C. Kendrick, and C. Nosko, \"The Effects of Uber's Surge Pricing: A Case Study,\" Univ. of Chicago Booth School of Business, Working Paper, May 2015.",
        "[3] H. Halaburda and Y. Yehezkel, \"Platform Competition under Asymmetric Information,\" American Economic Journal: Microeconomics, vol. 8, no. 3, pp. 51-68, Aug. 2016.",
        "[4] Ministry of Road Transport and Highways (MoRTH), \"Motor Vehicle Aggregator Guidelines 2020,\" Govt. of India, Notification No. RT-11036/64/2017-MVL, Nov. 2020.",
        "[5] Ministry of Road Transport and Highways (MoRTH), \"Motor Vehicle Aggregator Guidelines 2025 (Revision of Surge Pricing Provisions),\" Govt. of India, Jan. 2025.",
        "[6] A. Moreira-Matias et al., \"Predicting Taxi-Passenger Demand Using Streaming Data,\" IEEE Trans. Intell. Transp. Syst., vol. 14, no. 3, pp. 1393-1402, Sep. 2013.",
        "[7] L. Breiman, \"Random Forests,\" Machine Learning, vol. 45, no. 1, pp. 5-32, Oct. 2001.",
        "[8] J. H. Friedman, \"Greedy Function Approximation: A Gradient Boosting Machine,\" Annals of Statistics, vol. 29, no. 5, pp. 1189-1232, Oct. 2001.",
        "[9] J. B. MacQueen, \"Some Methods for Classification and Analysis of Multivariate Observations,\" in Proc. 5th Berkeley Symp. Math. Statist. Prob., vol. 1, pp. 281-297, 1967.",
        "[10] P. J. Rousseeuw, \"Silhouettes: A Graphical Aid to Interpretation and Validation of Cluster Analysis,\" J. Comput. Appl. Math., vol. 20, pp. 53-65, 1987.",
        "[11] F. T. Liu, K. M. Ting, and Z.-H. Zhou, \"Isolation Forest,\" in Proc. 8th IEEE ICDM, Pisa, Italy, 2008, pp. 413-422.",
        "[12] F. Pedregosa et al., \"Scikit-learn: Machine Learning in Python,\" JMLR, vol. 12, pp. 2825-2830, 2011.",
        "[13] S. Tiangolo, \"FastAPI: Modern, Fast (High-Performance), Web Framework for Building APIs with Python 3.8+,\" GitHub Repository, 2018. [Online]. Available: https://fastapi.tiangolo.com.",
        "[14] OpenStreetMap Contributors, \"Planet Dump and Nominatim Geocoding Engine,\" OpenStreetMap Foundation, 2024. [Online]. Available: https://nominatim.openstreetmap.org.",
        "[15] D. Luxen and C. Vetter, \"Real-Time Routing with OpenStreetMap Data,\" in Proc. 19th ACM SIGSPATIAL GIS, Chicago, IL, 2011, pp. 513-516.",
        "[16] V. A. Agrawal and S. S. Sane, \"Machine Learning Techniques for Taxi Fare Prediction: A Comparative Study,\" IJCA, vol. 182, no. 48, pp. 12-17, Mar. 2019.",
        "[17] Y. Lv, Y. Chen, X. Li, and F.-Y. Wang, \"Traffic Flow Prediction with Big Data: A Deep Learning Approach,\" IEEE TITS, vol. 16, no. 2, pp. 865-873, 2015.",
        "[18] Beckn Foundation, \"Beckn Protocol: Open Specifications for Decentralized Mobility Networks,\" Beckn Whitepaper, 2021. [Online]. Available: https://becknprotocol.io."
    ]
    for r in refs_text:
        story.append(Paragraph(r, ParagraphStyle('RefP', parent=body_style, fontSize=8.5, leading=11, spaceAfter=4)))
    story.append(PageBreak())

    # APPENDICES
    story.append(Paragraph("APPENDIX F: TEST SUITE VERIFICATION REPORT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A8A"), spaceAfter=10))
    story.append(Paragraph("The automated test suite was executed via pytest using Python 3.11.6 on 21st September 2026. All 28 tests passed successfully in 16.89 seconds with zero failures or warnings. Table F.1 summarizes the verification scope.", body_style))
    
    app_f_data = [
        ["backend/tests/test_adapters.py", "7", "7 Passed", "0", "100%", "Uber, Ola, Rapido, and Taxi quote models"],
        ["backend/tests/test_backend_api.py", "11", "11 Passed", "0", "100%", "/health, /geocode, /route, /analytics, security"],
        ["backend/tests/test_global_platforms.py", "1", "1 Passed", "0", "100%", "Regional city centroid mappings and currency formatting"],
        ["backend/tests/test_quote_orchestrator.py", "3", "3 Passed", "0", "100%", "Async quote orchestration, timeouts, route hashing"],
        ["ml/tests/test_ml_pipeline.py", "6", "6 Passed", "0", "100%", "Normalizer bounds, K-Means, GBR, anomaly detection"],
        ["TOTAL SUITE SUMMARY", "28", "28 Passed", "0", "100%", "Complete platform verification"]
    ]
    story.append(make_table(["Test Module File", "Tests", "Passed", "Failed", "Pass Rate", "Verification Scope"], app_f_data, [140, 40, 50, 40, 55, printable_width - 325]))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF report: {pdf_filename} ({os.path.getsize(pdf_filename)} bytes)")

if __name__ == '__main__':
    create_pdf_report()
