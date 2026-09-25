"""
Standalone Problem Statement PDF Generator for RideCompare
Institution: Rajagiri College of Social Sciences (Autonomous), Department of Computer Applications
Student: Siddharth MV (MCA 2026-2027)
Project: Smart Real-Time Taxi Fare Comparison and Machine Learning Based Fare Intelligence System
"""

import os
import sys
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class AcademicCanvas(canvas.Canvas):
    """Custom canvas providing running headers, footers, and page numbers."""
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
        self.setFillColor(colors.HexColor("#1E3A8A"))

        # Header
        self.drawString(44, A4[1] - 30, "RAJAGIRI COLLEGE OF SOCIAL SCIENCES (AUTONOMOUS)")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(290, A4[1] - 30, "|  Department of Computer Applications")
        self.drawRightString(A4[0] - 44, A4[1] - 30, "PROJECT PROBLEM STATEMENT")

        # Header rule
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(44, A4[1] - 35, A4[0] - 44, A4[1] - 35)

        # Footer rule
        self.line(44, 38, A4[0] - 44, 38)

        # Footer text
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(44, 26, "RideCompare: Smart Real-Time Taxi Fare Comparison & ML Intelligence System")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 44, 26, page_text)
        self.restoreState()


def build_problem_statement_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=44,
        rightMargin=44,
        topMargin=48,
        bottomMargin=48
    )

    printable_width = A4[0] - 88

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#0F172A")
    )

    meta_key = ParagraphStyle(
        'MetaKey',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1E3A8A")
    )

    meta_val = ParagraphStyle(
        'MetaVal',
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE, PARTICULARS, BACKGROUND, REAL-WORLD PROBLEM & FORMAL STATEMENT
    # =========================================================================
    inst_header = [
        [Paragraph("<b>RAJAGIRI COLLEGE OF SOCIAL SCIENCES (AUTONOMOUS)</b><br/><font size='7.5' color='#475569'>DEPARTMENT OF COMPUTER APPLICATIONS | MASTER OF COMPUTER APPLICATIONS (MCA)</font>", ParagraphStyle('InstHead', fontName='Helvetica', fontSize=9.5, leading=13, alignment=1, textColor=colors.HexColor("#1E3A8A")))]
    ]
    t_inst = Table(inst_header, colWidths=[printable_width])
    t_inst.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor("#1E3A8A")),
    ]))
    story.append(t_inst)
    story.append(Spacer(1, 8))

    story.append(Paragraph("SMART REAL-TIME TAXI FARE COMPARISON AND MACHINE LEARNING BASED FARE INTELLIGENCE SYSTEM", title_style))
    story.append(Paragraph("COMPREHENSIVE PROJECT PROBLEM STATEMENT & SPECIFICATION", subtitle_style))

    meta_table_data = [
        [
            Paragraph("<b>Candidate Name:</b>", meta_key), Paragraph("SIDDHARTH MV", meta_val),
            Paragraph("<b>Degree / Program:</b>", meta_key), Paragraph("Master of Computer Applications (MCA)", meta_val)
        ],
        [
            Paragraph("<b>Project Platform:</b>", meta_key), Paragraph("RideCompare", meta_val),
            Paragraph("<b>Academic Year:</b>", meta_key), Paragraph("2026 – 2027", meta_val)
        ],
        [
            Paragraph("<b>Domain:</b>", meta_key), Paragraph("Urban Mobility / Applied ML & Distributed Web Systems", meta_val),
            Paragraph("<b>Document Scope:</b>", meta_key), Paragraph("Formal Problem Statement & Technical Objectives", meta_val)
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[printable_width * 0.22, printable_width * 0.28, printable_width * 0.22, printable_width * 0.28])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Background & Urban Mobility Landscape", h1_style))
    story.append(Paragraph(
        "Over the past decade, urban passenger transportation across metropolitan economies has undergone a structural transition from traditional street-hail taxis toward on-demand ride-hailing aggregator platforms. Commercial ride-hailing networks—prominently Uber, Ola Cabs, and Rapido in India—alongside indigenous metered auto-rickshaws and state-regulated public taxi bodies, constitute the primary modal choice for millions of daily commuters. These platforms operate on dynamic pricing algorithms that continuously modulate journey fares in response to micro-fluctuations in passenger demand, driver supply, traffic congestion density, weather events, and specific diurnal transit windows. While dynamic pricing serves an economic purpose by clearing supply-demand imbalances in real time, it creates severe market opacity from the perspective of the individual consumer. Ride fares fluctuate unpredictably, often varying by 40% to 150% across competing platforms for identical journey corridors at the exact same minute. Consequently, urban commuters are left without transparent tariff benchmarks or unified comparison utilities.",
        body_style
    ))

    story.append(Paragraph("2. The Real-World Commuter Problem", h1_style))
    story.append(Paragraph(
        "Under the current urban transit paradigm, an individual commuter attempting to book a ride must undertake an inefficient, iterative manual process: (1) launch the first ride-hailing app (e.g., Uber) and enter pickup location; (2) enter destination and wait for geocoding and fare quotation; (3) review vehicle options and note fares and ETAs; (4) switch to a second provider (e.g., Ola) and repeat the entire input process from scratch; (5) switch to a third application (e.g., Rapido) for bike or auto options; and (6) mentally compare the fragmented results, balance price vs. ETA trade-offs, and make a decision under time pressure.",
        body_style
    ))

    story.append(Paragraph("3. Formal Problem Statement", h1_style))
    ps_text = (
        "<b>Problem Statement:</b><br/>"
        "<i>\"To design, develop, evaluate, and deploy a centralized, production-grade web application—entitled "
        "<b>'Smart Real-Time Taxi Fare Comparison and Machine Learning Based Fare Intelligence System' (RideCompare)</b>—"
        "that concurrently aggregates multi-provider taxi tariffs, determines road routing kinetics, normalizes disparate "
        "vehicle categories, and leverages in-process Machine Learning models (K-Means clustering, Gradient Boosting regression, "
        "and Isolation Forest anomaly detection) to provide transparent fair tariff baselines, surge explanations, and "
        "multi-factor ride rankings in real time.\"</i>"
    )
    t_ps = Table([[Paragraph(ps_text, callout_style)]], colWidths=[printable_width])
    t_ps.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 1.25, colors.HexColor("#2563EB")),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_ps)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: EXISTING SYSTEM SHORTCOMINGS & PROJECT OBJECTIVES
    # =========================================================================
    story.append(Paragraph("4. Deficiencies and Pain Points of Existing Systems", h1_style))
    story.append(Paragraph(
        "In the existing commercial ecosystem, service providers operate as isolated walled gardens. Analysis of consumer workflows highlights six acute deficiencies:",
        body_style
    ))

    flaws = [
        ("Fragmented Information", "Tariff details are isolated within proprietary mobile applications, preventing unified market visibility and forcing commuters into tedious app-switching."),
        ("Rapidly Expiring Prices", "Dynamic quotes typically possess short expiration windows (60 seconds). By the time a user finishes comparing three apps, earlier quotes have already expired or repriced."),
        ("Surge Pricing Opacity", "Aggregator apps mask algorithmic markups behind simple surge multipliers without explanatory diagnostics. Commuters cannot discern whether a high quote reflects genuine congestion or opportunistic price gouging."),
        ("Disparate Vehicle Categories", "Comparing a bike taxi from one provider against an auto-rickshaw or compact sedan from another requires complex mental normalization of speed, comfort, and weather risk."),
        ("Lack of Historical Context", "Existing applications present point-in-time quotes without context. Commuters have no way of knowing whether a quoted fare is historically normal, elevated, or an anomalous pricing glitch."),
        ("Omission of Public & Metered Transit", "Commercial aggregators deliberately omit government-regulated metered taxis and autos that maintain fixed statutory rates with zero surge pricing.")
    ]
    for title, desc in flaws:
        story.append(Paragraph(f"&bull;&nbsp; <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("5. Specific, Measurable Project Objectives", h1_style))
    story.append(Paragraph("To address each facet of the problem statement, the project establishes eight rigorous, measurable technical objectives:", body_style))

    objectives = [
        ("1. Data Collection & Preprocessing", "Assemble and preprocess a structured historical dataset of 12,000 transit records across Indian metropolitan corridors, handling physical bounds, cyclic diurnal features, and unit economic derivations."),
        ("2. Concurrent Quote Orchestration", "Construct an asynchronous backend architecture capable of querying multi-provider rate cards (Uber Go, Uber Premier, Ola Mini, Ola Prime, Rapido Bike, Rapido Auto, Local Taxi) within a 15-second freshness window."),
        ("3. Geospatial Road Kinematics", "Integrate open geospatial services (OpenStreetMap Nominatim for geocoding and Project-OSRM for turn-by-turn road geometry) to obtain accurate route distances and driving durations."),
        ("4. Unsupervised Pricing Regime Discovery", "Train an unsupervised K-Means clustering model to classify rides into empirical pricing regimes ('Peak Hour Surge', 'Standard City Transit', 'Long-Distance Transit') with silhouette validation."),
        ("5. Supervised Fair Baseline Estimation", "Train, evaluate, and tune supervised regression models (Random Forest vs Gradient Tree Boosting) to predict an expected fair tariff baseline with high statistical fidelity (R2 > 0.95)."),
        ("6. Multivariate Anomaly Detection", "Deploy an Isolation Forest detector to flag abnormal pricing spikes and fare glitches with natural-language diagnostic feedback."),
        ("7. Composite Smart Scoring", "Formulate a multi-criteria utility score balancing fare (40%), pickup ETA (30%), prediction confidence (15%), and provider reliability (15%)."),
        ("8. Responsive Web Interface", "Develop a high-performance React 19 / TypeScript single-page application featuring interactive Leaflet route mapping, corridor price volatility sparklines, and direct app deep linking.")
    ]
    for title, desc in objectives:
        story.append(Paragraph(f"&bull;&nbsp; <b>{title}:</b> {desc}", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: SCOPE, PROPOSED SYSTEM ADVANTAGES, AND ACADEMIC SIGN-OFF
    # =========================================================================
    story.append(Paragraph("6. Project Scope and Operational Boundaries", h1_style))
    scope_items = [
        ("Target Users", "Daily office commuters, university students, budget-conscious travelers, airport passengers, and urban transport analysts."),
        ("Supported Locations", "Primary coverage encompasses Indian metropolitan transit hubs: Bangalore (default), Delhi NCR, and Mumbai, with arbitrary coordinate-based routing supported up to 300 km."),
        ("Supported Services", "Uber Go, Uber Premier, Ola Mini, Ola Prime, Rapido Bike, Rapido Auto, and Local Metered Taxis."),
        ("Data Scope", "12,000 empirical historical records encompassing 22 features, reflecting multi-tier vehicle categories, traffic levels, weather conditions, and diurnal commute peaks."),
        ("Machine Learning Scope", "In-process inference running synchronously with quote retrieval, achieving sub-millisecond execution times without external microservice overhead."),
        ("Operational Boundary", "As commercial aggregators do not provide open, public API endpoints for real-time third-party booking without proprietary enterprise contracts, live provider quotes are computed using calibrated statutory rate cards matching published tariff regulations, integrated with universal app deep-linking.")
    ]
    for title, desc in scope_items:
        story.append(Paragraph(f"&bull;&nbsp; <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("7. Proposed System Architecture & Core Advantages", h1_style))
    story.append(Paragraph(
        "RideCompare solves the problem via a decoupled three-tier system: React 19 UI with Leaflet, FastAPI backend gateway with Project-OSRM, and in-process Scikit-Learn ML intelligence pipelines.",
        body_style
    ))

    advantages = [
        ("Single Search Query", "Origin and destination are specified once; geocoding and road routing are resolved automatically."),
        ("Sub-Second Aggregation", "Concurrent asynchronous orchestration delivers full multi-provider comparison in under 600 ms (90% search latency reduction vs. manual search)."),
        ("Quantified Surge Transparency", "The ML baseline displays the exact numerical surge premium (e.g., '+Rs. 54.20 (+28% surge)') over the fair expected fare."),
        ("Multi-Modal Coverage", "Bikes, auto-rickshaws, compact sedans, premium cabs, and local metered taxis are compared side-by-side."),
        ("Multi-Factor Smart Utility", "Rides are ranked not only by price, but by a balanced utility formula incorporating ETA, ML prediction confidence, and reliability."),
        ("One-Tap Direct Transition", "Universal deep links allow instant handover to native apps with coordinates pre-populated.")
    ]
    for title, desc in advantages:
        story.append(Paragraph(f"&bull;&nbsp; <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 14))

    # Academic Sign-off / Submission block
    sign_block = [
        [
            Paragraph("<b>Submitted By:</b><br/><br/><b>SIDDHARTH MV</b><br/>Register No: [Candidate Register Number]<br/>MCA 2026-2027<br/>Department of Computer Applications<br/>Rajagiri College of Social Sciences", meta_val),
            Paragraph("<b>Verified & Evaluated By:</b><br/><br/><b>PROJECT SUPERVISOR / COMMITTEE</b><br/>Department of Computer Applications<br/>Rajagiri College of Social Sciences (Autonomous)<br/>Kalamassery, Kochi, Kerala", meta_val)
        ]
    ]
    t_sign = Table(sign_block, colWidths=[printable_width * 0.5, printable_width * 0.5])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('LINEAFTER', (0, 0), (0, -1), 1, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(KeepTogether([t_sign]))

    doc.build(story, canvasmaker=AcademicCanvas)
    print(f"Built cleanly: {output_path}")


if __name__ == "__main__":
    out_file = os.path.abspath("RideCompare_Problem_Statement_Document.pdf")
    build_problem_statement_pdf(out_file)

    # Standard Problem_Statement.pdf in project root
    std_file = os.path.abspath("Problem_Statement.pdf")
    shutil.copyfile(out_file, std_file)
    print(f"Updated: {std_file}")

    # Copy to Desktop
    desktop_file = os.path.expanduser(r"~\Desktop\Problem_Statement.pdf")
    shutil.copyfile(out_file, desktop_file)
    print(f"Updated Desktop: {desktop_file}")
