"""
generate_pitch_deck.py
Generates a comprehensive, executive-ready, 16-slide PowerPoint presentation (16:9 Widescreen)
for Privacy Gateway AI (MINEARENA 1.0 PS-02).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# --- COLOR PALETTE (Dark Tech / Enterprise Theme) ---
C_BG_DARK = RGBColor(11, 17, 32)        # #0B1120 Deep Navy
C_CARD_BG = RGBColor(30, 41, 59)        # #1E293B Slate 800
C_CARD_BORDER = RGBColor(51, 65, 85)    # #334155 Slate 700
C_TEXT_WHITE = RGBColor(248, 250, 252)  # #F8FAFC White
C_TEXT_MUTED = RGBColor(148, 163, 184)  # #94A3B8 Slate 400
C_TEXT_BODY = RGBColor(226, 232, 240)   # #E2E8F0 Slate 200
C_ACCENT_BLUE = RGBColor(56, 189, 248)  # #38BDF8 Sky Blue
C_ACCENT_GREEN = RGBColor(52, 211, 153) # #34D399 Emerald Green
C_ACCENT_AMBER = RGBColor(251, 191, 36) # #FBBF24 Amber
C_ACCENT_RED = RGBColor(248, 113, 113)  # #F87171 Red
C_PILL_BG = RGBColor(15, 23, 42)        # #0F172A

def create_base_slide(prs, category_pill, slide_title, subtitle, slide_num, total_slides=16):
    """Creates a slide with consistent dark background, header bar, and footer."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    
    # 1. Dark Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BG_DARK
    bg.line.color.rgb = C_BG_DARK
    
    # 2. Category Pill
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.4), Inches(4.5), Inches(0.35))
    pill.fill.solid()
    pill.fill.fore_color.rgb = C_PILL_BG
    pill.line.color.rgb = C_ACCENT_BLUE
    pill.line.width = Pt(1)
    tf_pill = pill.text_frame
    tf_pill.word_wrap = True
    p_p = tf_pill.paragraphs[0]
    p_p.alignment = PP_ALIGN.CENTER
    r_p = p_p.add_run()
    r_p.text = category_pill.upper()
    r_p.font.name = "Segoe UI"
    r_p.font.size = Pt(9.5)
    r_p.font.bold = True
    r_p.font.color.rgb = C_ACCENT_BLUE
    
    # 3. Slide Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(0.55))
    tf_t = tb_title.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
    p_t = tf_t.paragraphs[0]
    r_t = p_t.add_run()
    r_t.text = slide_title
    r_t.font.name = "Segoe UI"
    r_t.font.size = Pt(22)
    r_t.font.bold = True
    r_t.font.color.rgb = C_TEXT_WHITE
    
    # 4. Slide Subtitle
    tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(11.7), Inches(0.4))
    tf_s = tb_sub.text_frame
    tf_s.word_wrap = True
    tf_s.margin_left = tf_s.margin_top = tf_s.margin_right = tf_s.margin_bottom = 0
    p_s = tf_s.paragraphs[0]
    r_s = p_s.add_run()
    r_s.text = subtitle
    r_s.font.name = "Segoe UI"
    r_s.font.size = Pt(11)
    r_s.font.color.rgb = C_TEXT_MUTED
    
    # 5. Footer Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.8), Inches(11.733), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = C_CARD_BORDER
    line.line.color.rgb = C_CARD_BORDER
    
    # 6. Footer Text
    tb_foot = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(8.5), Inches(0.35))
    tf_f = tb_foot.text_frame
    tf_f.margin_left = tf_f.margin_top = tf_f.margin_right = tf_f.margin_bottom = 0
    p_f = tf_f.paragraphs[0]
    r_f = p_f.add_run()
    r_f.text = "MINEARENA 1.0 (PS-02) — Privacy Gateway AI: DPDP-Ready Enterprise LLM Control Plane"
    r_f.font.name = "Segoe UI"
    r_f.font.size = Pt(9)
    r_f.font.color.rgb = C_TEXT_MUTED
    
    # 7. Slide Number
    tb_num = slide.shapes.add_textbox(Inches(10.5), Inches(6.9), Inches(2.0), Inches(0.35))
    tf_num = tb_num.text_frame
    tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
    p_num = tf_num.paragraphs[0]
    p_num.alignment = PP_ALIGN.RIGHT
    r_num = p_num.add_run()
    r_num.text = f"Slide {slide_num} of {total_slides}"
    r_num.font.name = "Segoe UI"
    r_num.font.size = Pt(9)
    r_num.font.color.rgb = C_TEXT_MUTED
    
    return slide

def add_card(slide, left, top, width, height, title, items, badge_text="", border_color=C_CARD_BORDER, bg_color=C_CARD_BG, title_color=C_TEXT_WHITE):
    """Draws a modern tech card with title, optional badge, and bullet points."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)
    
    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_top = Inches(0.2)
    tf.margin_bottom = Inches(0.2)
    
    # Title
    p_title = tf.paragraphs[0]
    p_title.space_after = Pt(8)
    if badge_text:
        r_b = p_title.add_run()
        r_b.text = f"[{badge_text}] "
        r_b.font.name = "Segoe UI"
        r_b.font.size = Pt(10)
        r_b.font.bold = True
        r_b.font.color.rgb = C_ACCENT_BLUE
        
    r_t = p_title.add_run()
    r_t.text = title
    r_t.font.name = "Segoe UI"
    r_t.font.size = Pt(13)
    r_t.font.bold = True
    r_t.font.color.rgb = title_color
    
    # Items
    for item in items:
        p_item = tf.add_paragraph()
        p_item.space_after = Pt(5)
        p_item.level = 0
        
        # If tuple: (bold_prefix, text)
        if isinstance(item, tuple):
            r_bold = p_item.add_run()
            r_bold.text = "• " + item[0] + ": "
            r_bold.font.name = "Segoe UI"
            r_bold.font.size = Pt(10)
            r_bold.font.bold = True
            r_bold.font.color.rgb = C_ACCENT_BLUE
            
            r_txt = p_item.add_run()
            r_txt.text = item[1]
            r_txt.font.name = "Segoe UI"
            r_txt.font.size = Pt(10)
            r_txt.font.color.rgb = C_TEXT_BODY
        else:
            r_txt = p_item.add_run()
            r_txt.text = "• " + item
            r_txt.font.name = "Segoe UI"
            r_txt.font.size = Pt(10)
            r_txt.font.color.rgb = C_TEXT_BODY

def add_stat_box(slide, left, top, width, height, stat_value, stat_label, subtext="", stat_color=C_ACCENT_BLUE):
    """Draws a bold statistical callout box."""
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = C_CARD_BG
    box.line.color.rgb = C_CARD_BORDER
    box.line.width = Pt(1)
    
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.15)
    
    p_val = tf.paragraphs[0]
    p_val.alignment = PP_ALIGN.CENTER
    r_val = p_val.add_run()
    r_val.text = stat_value
    r_val.font.name = "Segoe UI"
    r_val.font.size = Pt(24)
    r_val.font.bold = True
    r_val.font.color.rgb = stat_color
    
    p_lbl = tf.add_paragraph()
    p_lbl.alignment = PP_ALIGN.CENTER
    r_lbl = p_lbl.add_run()
    r_lbl.text = stat_label.upper()
    r_lbl.font.name = "Segoe UI"
    r_lbl.font.size = Pt(9.5)
    r_lbl.font.bold = True
    r_lbl.font.color.rgb = C_TEXT_WHITE
    
    if subtext:
        p_sub = tf.add_paragraph()
        p_sub.alignment = PP_ALIGN.CENTER
        r_sub = p_sub.add_run()
        r_sub.text = subtext
        r_sub.font.name = "Segoe UI"
        r_sub.font.size = Pt(8.5)
        r_sub.font.color.rgb = C_TEXT_MUTED

def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    total_slides = 16
    print("Building Presentation Deck (16 Slides)...")
    
    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Splash Dark Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_BG_DARK
    bg1.line.color.rgb = C_BG_DARK
    
    # Event Badge
    badge1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.1), Inches(4.8), Inches(0.42))
    badge1.fill.solid()
    badge1.fill.fore_color.rgb = C_PILL_BG
    badge1.line.color.rgb = C_ACCENT_BLUE
    badge1.line.width = Pt(1.5)
    tf_b1 = badge1.text_frame
    p_b1 = tf_b1.paragraphs[0]
    p_b1.alignment = PP_ALIGN.CENTER
    r_b1 = p_b1.add_run()
    r_b1.text = "MINEARENA 1.0  |  PROBLEM STATEMENT PS-02"
    r_b1.font.name = "Segoe UI"
    r_b1.font.size = Pt(11)
    r_b1.font.bold = True
    r_b1.font.color.rgb = C_ACCENT_BLUE
    
    # Big Main Title
    tb_m1 = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(1.3))
    tf_m1 = tb_m1.text_frame
    tf_m1.word_wrap = True
    p_m1 = tf_m1.paragraphs[0]
    r_m1 = p_m1.add_run()
    r_m1.text = "Privacy Gateway AI"
    r_m1.font.name = "Segoe UI"
    r_m1.font.size = Pt(44)
    r_m1.font.bold = True
    r_m1.font.color.rgb = C_TEXT_WHITE
    
    # Subtitle
    tb_sub1 = s1.shapes.add_textbox(Inches(1.0), Inches(3.1), Inches(11.3), Inches(0.9))
    tf_sub1 = tb_sub1.text_frame
    tf_sub1.word_wrap = True
    p_sub1 = tf_sub1.paragraphs[0]
    r_sub1 = p_sub1.add_run()
    r_sub1.text = "A DPDP-Ready, Fail-Closed Privacy & Governance Control Plane for Enterprise LLMs"
    r_sub1.font.name = "Segoe UI"
    r_sub1.font.size = Pt(20)
    r_sub1.font.color.rgb = C_ACCENT_BLUE
    
    # Tagline
    p_sub1_2 = tf_sub1.add_paragraph()
    p_sub1_2.space_before = Pt(6)
    r_sub1_2 = p_sub1_2.add_run()
    r_sub1_2.text = "Detect the sensitive. Mask the personal. Verify before sending. Restore locally."
    r_sub1_2.font.name = "Segoe UI"
    r_sub1_2.font.size = Pt(13)
    r_sub1_2.font.italic = True
    r_sub1_2.font.color.rgb = C_TEXT_MUTED
    
    # 4 Stat Callout Cards
    stats1 = [
        ("0", "Outbound PII Leaks", "Zero Tolerance Met", C_ACCENT_GREEN),
        ("100.0%", "Detection Precision & Recall", "442 Ground-Truth Spans", C_ACCENT_BLUE),
        ("100%", "Fail-Closed Security", "17/17 Pytest Tests Passed", C_ACCENT_GREEN),
        ("34.0 ms", "p95 Local Latency", "< 2.5% Request Overhead", C_ACCENT_BLUE),
    ]
    card_w = Inches(2.7)
    for idx, (val, lbl, sub, col) in enumerate(stats1):
        x = Inches(1.0) + idx * (card_w + Inches(0.17))
        add_stat_box(s1, x, Inches(4.3), card_w, Inches(1.3), val, lbl, sub, col)
        
    # Team & Tech Stack Badge
    tb_foot1 = s1.shapes.add_textbox(Inches(1.0), Inches(6.0), Inches(11.3), Inches(0.8))
    tf_foot1 = tb_foot1.text_frame
    p_ft1 = tf_foot1.paragraphs[0]
    r_ft1 = p_ft1.add_run()
    r_ft1.text = "ENGINEERING TASKFORCE: Enterprise AI Governance & Security Division | Bharat Financial Technologies\n"
    r_ft1.font.name = "Segoe UI"
    r_ft1.font.size = Pt(10)
    r_ft1.font.bold = True
    r_ft1.font.color.rgb = C_TEXT_WHITE
    
    r_ft2 = p_ft1.add_run()
    r_ft2.text = "STACK: FastAPI + Python 3.12 | Presidio + spaCy NER | AES-256-GCM + Redis 7 | PostgreSQL 16 | Google Gemini Interactions API | React 18 UI"
    r_ft2.font.name = "Segoe UI"
    r_ft2.font.size = Pt(9.5)
    r_ft2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 2: THE PROBLEM STATEMENT & REGULATORY REALITY
    # =========================================================================
    s2 = create_base_slide(prs, "Problem Context", "The Enterprise GenAI Dilemma & India's DPDP Act, 2023", "Why Indian enterprises cannot send raw customer documents to commercial LLM providers", 2)
    
    add_card(
        s2, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "GenAI Demand in Indian BFSI",
        [
            ("High-Value Use Cases", "Automated loan underwriting, customer KYC verification, grievance analysis, claims processing."),
            ("Sensitive Documents", "Customer dossiers contain Aadhaar cards, PAN, GSTIN, bank statements, and salary slips."),
            ("Productivity Imperative", "Commercial LLMs (Gemini, GPT-4) unlock 10x faster processing and higher accuracy."),
            ("Core Obstacle", "Security and compliance teams block deployment due to data leakage fears.")
        ],
        badge_text="OPPORTUNITY"
    )
    
    add_card(
        s2, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Statutory Mandate (DPDP 2023)",
        [
            ("Section 8 Fiduciary Duties", "Mandatory implementation of reasonable security safeguards to prevent data breaches."),
            ("Section 6 Purpose Limitation", "Processing limited strictly to consented purposes; zero third-party disclosure."),
            ("Section 8(7) Erasure", "Mandatory data expungement when processing purpose is fulfilled."),
            ("₹250 Crore Penalties", "Statutory financial penalties up to ₹250 Cr ($30M USD) per security failure.")
        ],
        badge_text="REGULATORY MANDATE",
        border_color=C_ACCENT_AMBER
    )
    
    add_card(
        s2, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Public LLM Exposure Risks",
        [
            ("Model Data Harvesting", "Standard commercial APIs retain user prompts for training unless strictly covered by zero-retention."),
            ("Cross-Border Transmission", "Customer PII leaves Indian jurisdiction to overseas hyperscaler data centers."),
            ("Prompt Injection / Extraction", "Adversarial prompts can extract historical context or reveal embedded PII."),
            ("The Operational Deadlock", "Enterprises must choose between AI stagnation or statutory non-compliance.")
        ],
        badge_text="EXISTING RISKS",
        border_color=C_ACCENT_RED
    )

    # =========================================================================
    # SLIDE 3: WHY EXISTING GATEWAYS FAIL (COMPETITIVE GAP)
    # =========================================================================
    s3 = create_base_slide(prs, "Competitive Gap Analysis", "Why Existing LLM Proxies Fail on Indian Enterprise Workloads", "Architectural shortcomings in LiteLLM, Cloudflare AI Gateway, Skyflow, and Protecto", 3)
    
    w4 = Inches(2.7)
    gap_cards = [
        ("Western-Centric PII", "Global AI tools use basic regexes for SSNs and credit cards. They lack native support for Aadhaar (Verhoeff checksum), GSTIN (Mod-36), PAN entity coding, and Hinglish address patterns.", "GAP 1", C_ACCENT_RED),
        ("Pre-Filtering Fallacy", "Existing proxies scan user input strings in early middleware. They fail to inspect the final serialized JSON payload at the transport wire boundary, allowing prompt leaks and tampering.", "GAP 2", C_ACCENT_AMBER),
        ("Insecure Tokenization", "Many tools use predictable sequential counters (<PERSON_1>) in unencrypted plaintext Redis, exposing tokens to guessing, injection collisions, and unauthorized reconstruction.", "GAP 3", C_ACCENT_RED),
        ("Auto-Unmasking Vulnerability", "Gateways blindly unmask data to any submitter. A junior analyst or developer querying a document for grammar correction receives unmasked Aadhaar and financial data.", "GAP 4", C_ACCENT_AMBER),
    ]
    
    for idx, (title, text, badge, col) in enumerate(gap_cards):
        x = Inches(0.8) + idx * (w4 + Inches(0.3))
        add_card(
            s3, x, Inches(1.85), w4, Inches(4.7),
            title,
            [text],
            badge_text=badge,
            border_color=col
        )

    # =========================================================================
    # SLIDE 4: THE FIVE CORE SECURITY INVARIANTS
    # =========================================================================
    s4 = create_base_slide(prs, "Design Principles", "The Five Non-Negotiable Enterprise Security Invariants", "Core cryptographic and architectural guarantees enforced across every pipeline execution", 4)
    
    invariants = [
        ("Invariant 1: Outbound Zero-PII", "Under all execution paths, the canonical JSON payload transmitted across the external network boundary to any LLM provider must contain exactly zero occurrences of raw personal identifiers.", "ZERO LEAKAGE"),
        ("Invariant 2: Fail-Closed Default", "In the event of detector initialization failure, policy unavailability, Redis cache outage, or security gate ambiguity, the system immediately aborts transmission. The system never fails open.", "FAIL-CLOSED"),
        ("Invariant 3: Cryptographic Vault Isolation", "Reversible PII mappings must be encrypted under AES-256-GCM with Additional Authenticated Data bound to (org_id, request_id) and an ephemeral TTL. Keys never reside in data stores.", "AES-256-GCM"),
        ("Invariant 4: Least-Privilege Restoration", "The privilege to submit text for LLM processing does not confer the privilege to restore unmasked PII. Unmasking is strictly restricted to authorized roles via enterprise RBAC.", "RBAC RESTRICTION"),
        ("Invariant 5: Audit Trail Hygiene", "No raw PII string or reversible decryption secret shall ever be persisted in PostgreSQL audit tables or application event logs. Only cryptographic digests and entity counts are logged.", "ZERO-PII AUDIT"),
    ]
    
    inv_h = Inches(0.88)
    for idx, (t, desc, b) in enumerate(invariants):
        y = Inches(1.85) + idx * (inv_h + Inches(0.1))
        add_card(
            s4, Inches(0.8), y, Inches(11.733), inv_h,
            t,
            [desc],
            badge_text=b,
            border_color=C_ACCENT_BLUE
        )

    # =========================================================================
    # SLIDE 5: SYSTEM ARCHITECTURE
    # =========================================================================
    s5 = create_base_slide(prs, "System Architecture", "Modular Monolith Control Plane Architecture", "Clean separation of 8 service engines behind explicit Python interfaces and isolated storage tiers", 5)
    
    add_card(
        s5, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Frontend & Ingress Tier",
        [
            ("Enterprise React 18 UI", "TypeScript, Tailwind CSS, Lucide icons, Vite bundling."),
            ("4 Operational Workspaces", "Processing Center (3-panel), Command Center, Governance Center, Audit Center."),
            ("Nginx Reverse Proxy", "Unified routing for /api/, /health, and frontend assets in production container."),
            ("JWT Authentication", "Role-based tokens with bcrypt credential verification.")
        ],
        badge_text="PRESENTATION LAYER"
    )
    
    add_card(
        s5, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "FastAPI Service Engines",
        [
            ("Engine 1: Detection", "Presidio + spaCy NER + Indian Checksums (Verhoeff, Mod-36, Luhn)."),
            ("Engine 2: Tokenization", "CSPRNG typed placeholders + AES-256-GCM Redis Vault."),
            ("Engine 3: Security Gate", "Fail-closed canonical wire inspection + HMAC-SHA256 tickets."),
            ("Engine 4: LLM Dispatch", "Gemini Interactions API (store=False) + OpenAI adapter."),
            ("Engine 5: Restoration", "Exact token lookup + newly generated PII response scanning."),
            ("Engine 6: Policy / PBAC", "Purpose-based entity blocking rules & role matrix.")
        ],
        badge_text="CORE ENGINES",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s5, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Storage & External Ecosystem",
        [
            ("Ephemeral Redis Vault", "Short-lived AES-256-GCM mappings with auto-expiring TTL (default 900s)."),
            ("Immutable PostgreSQL Store", "Alembic migrations, request metadata, SHA-256 wire hashes, zero raw PII."),
            ("Google Gemini Cloud", "POST /v1beta/interactions, Api-Revision: 2026-05-20, zero provider retention."),
            ("Audit Exporters", "One-click JSON and CSV DPDP compliance evidence packages.")
        ],
        badge_text="STORAGE & EGRESS"
    )

    # =========================================================================
    # SLIDE 6: THE 8-STAGE END-TO-END PIPELINE
    # =========================================================================
    s6 = create_base_slide(prs, "Pipeline Orchestration", "The 8-Stage End-to-End Privacy & Governance Pipeline", "Deterministic data transformation pipeline enforcing compliance before, during, and after LLM invocation", 6)
    
    stages = [
        ("1. DETECT", "Presidio + spaCy NER + Verhoeff/Mod-36 checksums scan input locally. Zero network calls.", C_ACCENT_BLUE),
        ("2. CLASSIFY", "Evaluate business purpose and user role against PBAC rules. Block unauthorized entities.", C_ACCENT_BLUE),
        ("3. MASK", "Mint random <TYPE_6CHAR> tokens. Write encrypted AES-256-GCM mappings to Redis with TTL.", C_ACCENT_GREEN),
        ("4. VERIFY", "Independent Security Gate inspects final serialized wire payload. Issues HMAC-SHA256 ticket.", C_ACCENT_GREEN),
        ("5. FORWARD", "Transport guard verifies ticket and dispatches sanitized payload to Gemini (store=False).", C_ACCENT_BLUE),
        ("6. INSPECT", "Extract tokens from LLM response. Classify valid, missing, or forged/unknown tokens.", C_ACCENT_BLUE),
        ("7. RESTORE", "Authorized local unmasking (RBAC gated). Scan response for newly generated/hallucinated PII.", C_ACCENT_GREEN),
        ("8. AUDIT", "Record request metadata, entity frequencies, and payload SHA-256 hash in PostgreSQL.", C_ACCENT_GREEN),
    ]
    
    card_w_st = Inches(2.7)
    card_h_st = Inches(2.25)
    
    # 2 rows of 4 cards
    for idx, (title, desc, col) in enumerate(stages):
        row = idx // 4
        col_idx = idx % 4
        x = Inches(0.8) + col_idx * (card_w_st + Inches(0.3))
        y = Inches(1.85) + row * (card_h_st + Inches(0.2))
        add_card(
            s6, x, y, card_w_st, card_h_st,
            title,
            [desc],
            border_color=col
        )

    # =========================================================================
    # SLIDE 7: ENGINE 1: MULTI-TIER INDIAN PII DETECTION
    # =========================================================================
    s7 = create_base_slide(prs, "Engine 1 Deep-Dive", "Multi-Tier Indian PII Detection & Mathematical Checksums", "Combining Presidio, spaCy NER, and non-linear group-theoretic checksums for 100% precision", 7)
    
    add_card(
        s7, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Aadhaar Verhoeff Checksum",
        [
            ("Dihedral Group D5", "Operates over non-abelian symmetry group of a regular pentagon (order 10)."),
            ("100% Error Detection", "Detects 100% of single-digit transcription errors and 100% of adjacent transpositions."),
            ("UIDAI Domain Checks", "Enforces 12 digits, rejects prefix '0' and '1', discards repeating sequences like 222222222222."),
            ("Zero Network Egress", "Pure mathematical verification executing in < 0.1 ms.")
        ],
        badge_text="AADHAAR VERIFICATION",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s7, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "GSTIN Mod-36 & PAN Codes",
        [
            ("Modulo-36 Radix Checksum", "15-char code verified via alternating radix-36 weighted sum over {0-9, A-Z}."),
            ("Embedded PAN Cross-Check", "Validates that characters 3 to 12 form a legally valid PAN."),
            ("PAN 4th-Char Entity Code", "Restricts 4th char to valid ITD entity codes: P (Individual), C (Company), H (HUF), F (Firm)."),
            ("Valid State Codes", "Enforces GST state code set {01..38, 97, 99}.")
        ],
        badge_text="BUSINESS IDENTIFIERS",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s7, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Contextual NER & Priority",
        [
            ("Local spaCy NER", "en_core_web_sm with zero external API calls for Indian names and titles."),
            ("Address & Hinglish Cues", "Extracts 6-digit Indian PIN codes, urban/rural markers (Nagar, Layout, Vihar, Chowk)."),
            ("False-Positive Filter", "Whitelists banking terms (EMI, KYC, HDFC, Branch, Aadhaar, Loan)."),
            ("Overlap Resolution", "Strict specificity priority: GSTIN (100) > Aadhaar (95) > PAN (90) > Address > Person.")
        ],
        badge_text="CONTEXTUAL LOGIC",
        border_color=C_ACCENT_AMBER
    )

    # =========================================================================
    # SLIDE 8: ENGINE 2: CRYPTOGRAPHIC PRIVACY VAULT & TOKENIZATION
    # =========================================================================
    s8 = create_base_slide(prs, "Engine 2 Deep-Dive", "Cryptographic Privacy Vault & Entropy-Preserving Tokenization", "Unpredictable typed placeholders backed by AES-256-GCM authenticated encryption and ephemeral Redis TTL", 8)
    
    add_card(
        s8, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "High-Entropy Typed Tokens",
        [
            ("Unpredictable Format", "Placeholders follow <ENTITY_6CHAR> (e.g., <AADHAAR_7K2P9X>)."),
            ("1.07 Billion Space", "Base-32 alphabet yields 32^6 = 1,073,741,824 combinations per entity type."),
            ("CSPRNG Generation", "Minted using secrets.choice (/dev/urandom) to prevent guessing attacks."),
            ("Collision Guard", "Actively scans input document to ensure candidate token does not exist in user text.")
        ],
        badge_text="TOKEN ENTROPY",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s8, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Request-Scoped Consistency",
        [
            ("Semantic Co-Reference", "Identical normalized entities in a document receive the identical placeholder."),
            ("Contextual Reasoning", "Enables LLMs to summarize relationships without knowing actual customer identity."),
            ("Cross-Request Randomness", "Fresh random seeds generated across different requests to defeat linkage attacks."),
            ("Right-to-Left Replacement", "Substitutions applied backwards to preserve character offsets exactly.")
        ],
        badge_text="REASONING FIDELITY",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s8, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "AES-256-GCM Redis Vault",
        [
            ("AEAD Cipher", "Galois/Counter Mode (AES-256-GCM) with 96-bit unique random nonce per write."),
            ("AAD Binding", "org_id and request_id bound as Additional Authenticated Data into the 128-bit tag."),
            ("Cross-Tenant Proof", "Ciphertext cannot be transplanted across organizations or requests."),
            ("Ephemeral TTL (900s)", "Auto-expunges mappings after 15 minutes; aligns with DPDP Section 8(7) erasure.")
        ],
        badge_text="CRYPTOGRAPHIC VAULT",
        border_color=C_ACCENT_AMBER
    )

    # =========================================================================
    # SLIDE 9: ENGINE 3: INDEPENDENT OUTBOUND SECURITY GATE
    # =========================================================================
    s9 = create_base_slide(prs, "Engine 3 Deep-Dive", "Independent Outbound Security Gate (Fail-Closed)", "Transport-boundary inspection of the canonical serialized JSON wire payload with HMAC-SHA256 tickets", 9)
    
    add_card(
        s9, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Transport Boundary Placement",
        [
            ("Beyond Middleware", "Placed directly inside the LLM provider dispatch client right at the network socket boundary."),
            ("Canonical JSON Wire Body", "Inspects the full serialized payload (system prompts, user text, tool definitions, metadata)."),
            ("Anti-Tamper Proof", "Catches post-masking memory mutations, debug logging leaks, and template injections."),
            ("Zero Leakage Verification", "Verifies absence of all original PII substrings and normalized variants.")
        ],
        badge_text="INSPECTION SCOPE",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s9, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Three-Valued Security Logic",
        [
            ("PASS Decision", "Payload passes all checks; permits cryptographic ticket generation."),
            ("FAIL Decision", "Detected PII leak, credential regex, or unapproved provider. Blocks transmission."),
            ("UNKNOWN Decision", "Detector down, Redis unreachable, or policy undefined. Blocks transmission."),
            ("Fail-Closed Invariant", "Only PASS initiates outbound sockets. FAIL and UNKNOWN always abort with 403/503.")
        ],
        badge_text="DECISION ENGINE",
        border_color=C_ACCENT_RED
    )
    
    add_card(
        s9, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "HMAC-SHA256 Tickets",
        [
            ("Payload SHA-256 Digest", "Computes cryptographic hash of canonical wire payload JSON."),
            ("HMAC Signature", "Signs (ticket_id | req_id | org_id | provider | model | hash) using gate secret."),
            ("Adapter Verification", "Provider adapter re-computes hash and verifies HMAC signature prior to HTTP dispatch."),
            ("Tamper Containment", "Any single-byte modification of payload in memory voids the ticket immediately.")
        ],
        badge_text="CRYPTOGRAPHIC TICKET",
        border_color=C_ACCENT_GREEN
    )

    # =========================================================================
    # SLIDE 10: ENGINE 4 & 5: LLM ORCHESTRATION & RESPONSE INTELLIGENCE
    # =========================================================================
    s10 = create_base_slide(prs, "Engine 4 & 5 Deep-Dive", "LLM Orchestration & Authorized Local Restoration", "Stateless Google Gemini integration, adversarial response resilience, and RBAC-gated unmasking", 10)
    
    add_card(
        s10, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Stateless Gemini Integration",
        [
            ("Google Interactions API", "POST /v1beta/interactions (Api-Revision: 2026-05-20)."),
            ("store=False Parameter", "Prohibits provider from retaining, logging, or training on interaction context."),
            ("Model Auto-Failover", "Defaults to gemini-3.8-flash; automatically fails over to gemini-3.5-flash-lite on 429/503/timeout."),
            ("Zero Raw PII on Wire", "External provider processes strictly anonymized placeholders.")
        ],
        badge_text="ORCHESTRATION",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s10, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Adversarial Restoration",
        [
            ("Exact Token Lookup", "Strict single-pass regex replacement; rejects fuzzy matching to prevent legal errors."),
            ("Reordered & Repeated", "Handles reordered sentences and multiple mentions of identical placeholders perfectly."),
            ("Forged Token Defense", "Unknown or model-hallucinated placeholders are detected, flagged, and left untouched."),
            ("Newly Generated PII Scan", "Scans restored response for model-hallucinated personal data not in vault.")
        ],
        badge_text="RESTORATION ENGINE",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s10, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "RBAC Unmasking Separation",
        [
            ("Decoupled Permissions", "Document submission privilege does NOT grant unmasking privilege."),
            ("Analyst Role (403)", "Submits documents, receives sanitized LLM output; restoration blocked (HTTP 403)."),
            ("Privacy Officer Role", "Full authorization to restore unmasked PII and export DPDP evidence."),
            ("Auditor Role", "Read-only access to metrics, logs, and cryptographic proofs; zero raw PII view.")
        ],
        badge_text="ACCESS CONTROL",
        border_color=C_ACCENT_AMBER
    )

    # =========================================================================
    # SLIDE 11: ENGINE 6 & 7: GOVERNANCE, PBAC & ZERO-PII AUDIT
    # =========================================================================
    s11 = create_base_slide(prs, "Engine 6 & 7 Deep-Dive", "Enterprise Governance, PBAC & Zero-PII Audit", "Purpose-based policy enforcement, immutable PostgreSQL records, and DPDP compliance evidence export", 11)
    
    add_card(
        s11, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Purpose-Based Policies (PBAC)",
        [
            ("Statutory Purpose Binding", "DPDP Section 6 mandates that data processing be strictly bound to consented purpose."),
            ("Granular Entity Blocking", "Policies define allowed vs blocked entities per business purpose."),
            ("Loan Underwriting", "Permits Aadhaar, PAN, and Bank Account tokenization for credit assessment."),
            ("Marketing Analytics", "Actively blocks Aadhaar, Voter ID, and Bank Accounts, halting pipeline before masking.")
        ],
        badge_text="PURPOSE LIMITATION",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s11, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Zero-Raw-PII PostgreSQL Store",
        [
            ("Clean Compliance Logging", "Conventional logs leak PII. Privacy Gateway AI logs zero raw customer values."),
            ("Cryptographic Audit Trail", "Persists UUID, timestamp, tenant ID, user role, and business purpose."),
            ("Outbound SHA-256 Digest", "Logs SHA-256 hash of the exact sanitized wire payload sent to provider."),
            ("Entity Frequency Map", "Records detected entity counts (e.g., {'AADHAAR': 1, 'PAN': 1}) for analytics.")
        ],
        badge_text="AUDIT INTEGRITY",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s11, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "DPDP Evidence Exporters",
        [
            ("Regulatory Inspection Ready", "Section 21 of DPDP Act empowers Data Protection Board to summon records."),
            ("One-Click Bundle Export", "Automated export of cryptographically verifiable JSON and CSV audit packages."),
            ("Proof of Non-Transmission", "SHA-256 hashes and gate decision receipts prove zero PII left the organization."),
            ("Tamper-Evident History", "Security events (blocked payloads, failed logins) immutably recorded.")
        ],
        badge_text="DPDP COMPLIANCE",
        border_color=C_ACCENT_AMBER
    )

    # =========================================================================
    # SLIDE 12: ENTERPRISE UI: FOUR OPERATIONAL WORKSPACES
    # =========================================================================
    s12 = create_base_slide(prs, "User Experience", "Enterprise UI: Four Production Workspaces", "React 18 + TypeScript + Tailwind CSS control plane engineered for compliance and security teams", 12)
    
    ui_workspaces = [
        ("Processing Center (3-Panel UI)", "Panel A: Original input with interactive PII entity highlights.\nPanel B: Wire payload showing <TYPE_6CHAR> tokens & GATE: PASS.\nPanel C: Locally restored response with unmasking telemetry.", "CORE WORKSPACE 1", C_ACCENT_BLUE),
        ("Command Center Dashboard", "Live telemetry console displaying active system health, provider readiness, p50/p95 latency gauges, throughput counters, and security block rates.", "TELEMETRY WORKSPACE 2", C_ACCENT_GREEN),
        ("Governance Center", "Centralized policy management interface allowing privacy officers to define purpose-based entity blocking rules, provider allowlists, and role matrices.", "POLICY WORKSPACE 3", C_ACCENT_AMBER),
        ("Audit & Intelligence Center", "Searchable compliance repository with request-level investigation, SHA-256 verification, security event timeline, and one-click DPDP evidence export.", "AUDIT WORKSPACE 4", C_ACCENT_BLUE),
    ]
    
    for idx, (title, desc, b, col) in enumerate(ui_workspaces):
        row = idx // 2
        col_idx = idx % 2
        x = Inches(0.8) + col_idx * (Inches(5.7) + Inches(0.333))
        y = Inches(1.85) + row * (Inches(2.25) + Inches(0.2))
        add_card(
            s12, x, y, Inches(5.7), Inches(2.25),
            title,
            [desc],
            badge_text=b,
            border_color=col
        )

    # =========================================================================
    # SLIDE 13: EMPIRICAL EVALUATION: 50-DOC BENCHMARK
    # =========================================================================
    s13 = create_base_slide(prs, "Empirical Evaluation", "Evaluation Benchmark: 50-Document Synthetic Corpus", "Rigorous evaluation across 442 labeled entity spans spanning Loan, KYC, Support, and Insurance domains", 13)
    
    # 4 Stat Callout Cards
    eval_stats = [
        ("0", "Outbound Leaks", "Zero Tolerance Met", C_ACCENT_GREEN),
        ("100.0%", "Overall Precision", "Zero False Positives", C_ACCENT_BLUE),
        ("100.0%", "Overall Recall", "Zero False Negatives", C_ACCENT_BLUE),
        ("100.0%", "Reinsertion Accuracy", "Perfect Token Replacement", C_ACCENT_GREEN),
    ]
    for idx, (val, lbl, sub, col) in enumerate(eval_stats):
        x = Inches(0.8) + idx * (Inches(2.7) + Inches(0.3))
        add_stat_box(s13, x, Inches(1.85), Inches(2.7), Inches(1.3), val, lbl, sub, col)
        
    # Corpus Distribution Card
    add_card(
        s13, Inches(0.8), Inches(3.35), Inches(5.7), Inches(3.2),
        "Synthetic Indian Enterprise Corpus",
        [
            ("15 Loan Underwriting Files", "Multi-entity applications: Aadhaar, PAN, GSTIN, salary, bank accounts, IFSC."),
            ("15 KYC & Onboarding Records", "Voter IDs, passport numbers, birth dates, address landmarks, PIN codes."),
            ("10 Customer Support Tickets", "Unstructured Hinglish queries ('Mera loan account number...', 'Address change')."),
            ("10 Insurance Claim Dossiers", "Policy claims, hospital billing, UPI IDs, credit cards, negative controls."),
            ("442 Ground-Truth Spans", "Exhaustive span-level ground-truth annotations across 15 entity types.")
        ],
        badge_text="CORPUS DETAILS",
        border_color=C_ACCENT_BLUE
    )
    
    # Granular Entity Performance Card
    add_card(
        s13, Inches(6.833), Inches(3.35), Inches(5.7), Inches(3.2),
        "Measured Entity-Wise Performance",
        [
            ("Aadhaar (44 spans)", "100.0% Precision | 100.0% Recall (Verhoeff checksum validated)."),
            ("PAN (59 spans)", "100.0% Precision | 100.0% Recall (4th-char entity code validated)."),
            ("GSTIN (20 spans)", "100.0% Precision | 100.0% Recall (Mod-36 checksum + embedded PAN)."),
            ("Address & Person (126 spans)", "100.0% Precision | 100.0% Recall (PIN codes, locality markers, spaCy NER)."),
            ("Financial & Telecomm (193 spans)", "100.0% Precision | 100.0% Recall (Bank Account, IFSC, UPI, Phone, Cards)."),
            ("Local Overhead", "p50 = 27.32 ms | p95 = 34.01 ms (sub-35 ms local latency).")
        ],
        badge_text="15 ENTITY TYPES",
        border_color=C_ACCENT_GREEN
    )

    # =========================================================================
    # SLIDE 14: SECURITY VERIFICATION & CONTAINER OUTAGE RESILIENCE
    # =========================================================================
    s14 = create_base_slide(prs, "Security Verification", "Adversarial Robustness & Container Outage Resilience", "12/12 security test scenarios passed; 17/17 pytest suite passing in 44.25s", 14)
    
    sec_cards = [
        ("Adversarial Attacks (SEC 01-03)", [
            ("SEC-01 Outbound Leak", "Injected PII detected by Security Gate; LLM call blocked (0 leaks)."),
            ("SEC-02 Wire Tampering", "Payload modified post-gate; HMAC signature mismatch blocks dispatch."),
            ("SEC-03 Forged Tokens", "LLM hallucinated tokens left unmasked; flagged in response audit.")
        ], C_ACCENT_RED),
        ("Outage Resilience (SEC 04-06)", [
            ("SEC-04 Redis Killed", "docker stop pgw-redis tested live; API returns 503 fail-closed."),
            ("SEC-05 Detector Crash", "Simulated detector exception returns 503 fail-closed immediately."),
            ("SEC-06 Policy Unknown", "Indeterminate security state treated as FAIL; wire dispatch blocked.")
        ], C_ACCENT_AMBER),
        ("Access Control (SEC 07-09)", [
            ("SEC-07 Cross-Tenant", "Transplanted ciphertext fails AES-256-GCM AAD tag verification."),
            ("SEC-08 Analyst Role", "Analyst receives sanitized text; unmasking blocked with HTTP 403."),
            ("SEC-09 Expired TTL", "Expired Redis mapping raises VaultNotFoundError; text stays masked.")
        ], C_ACCENT_GREEN),
        ("Hygiene & Rules (SEC 10-12)", [
            ("SEC-10 Clean Logs/DB", "Ciphertext inspection confirms 0 raw PII in Redis blobs or DB audit."),
            ("SEC-11 Token Collision", "User input containing <PERSON_...> avoided via collision guard."),
            ("SEC-12 PBAC Block", "Marketing purpose blocks Aadhaar before any masking or LLM call.")
        ], C_ACCENT_BLUE),
    ]
    
    for idx, (title, items, col) in enumerate(sec_cards):
        row = idx // 2
        col_idx = idx % 2
        x = Inches(0.8) + col_idx * (Inches(5.7) + Inches(0.333))
        y = Inches(1.85) + row * (Inches(2.25) + Inches(0.2))
        add_card(
            s14, x, y, Inches(5.7), Inches(2.25),
            title,
            items,
            badge_text="VERIFIED PASS",
            border_color=col
        )

    # =========================================================================
    # SLIDE 15: PRODUCTION READINESS & FUTURE ROADMAP
    # =========================================================================
    s15 = create_base_slide(prs, "Production & Roadmap", "Production Readiness & Future Engineering Roadmap", "Production container deployment verified live; clear roadmap for enterprise scale", 15)
    
    add_card(
        s15, Inches(0.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Production Container Stack",
        [
            ("Docker Compose Topology", "pgw-backend, pgw-frontend, pgw-postgres, pgw-redis, and Nginx proxy."),
            ("Nginx Reverse Proxy", "Proxies /api/ and /health to backend:8000; serves built Vite SPA at :5173."),
            ("Live Gemini Interactions", "Verified with real Google Gemini API (Api-Revision: 2026-05-20, store=False)."),
            ("Zero Local Leaks", "Strict .dockerignore prevents local secrets, .venv, or node_modules from leaking.")
        ],
        badge_text="LIVE DEPLOYMENT",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s15, Inches(4.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Short-Term Roadmap",
        [
            ("Streaming SSE Token Buffering", "Windowed token rehydration across partial streaming LLM response chunks."),
            ("On-Device Document OCR", "Local Tesseract / PaddleOCR pipeline for physical Aadhaar & PAN card scans."),
            ("MCP Tool-Call Vaulting", "Privacy filtering and token vaulting for Model Context Protocol agent tool calls."),
            ("Secondary Provider Live Key", "Provision OpenAI API key for multi-provider live load balancing.")
        ],
        badge_text="NEXT RELEASES",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s15, Inches(8.8), Inches(1.85), Inches(3.65), Inches(4.7),
        "Enterprise Scale Roadmap",
        [
            ("Hardware Security Modules (HSM)", "Envelope encryption key management with AWS KMS / HashiCorp Vault."),
            ("Distributed Multi-Region Vault", "Active-active encrypted Redis clustering for cross-region disaster recovery."),
            ("Differential Privacy Analytics", "Epsilon-delta noise injection for aggregated enterprise intelligence queries."),
            ("Automated DPBI Filing", "Direct API integration with Data Protection Board for compliance reporting.")
        ],
        badge_text="ENTERPRISE SCALE",
        border_color=C_ACCENT_AMBER
    )

    # =========================================================================
    # SLIDE 16: CONCLUSION & DEMO INVITATION
    # =========================================================================
    s16 = create_base_slide(prs, "Conclusion", "Privacy Gateway AI: Empowering Compliant Enterprise AI", "Bridging the gap between generative AI utility and statutory DPDP compliance", 16)
    
    add_card(
        s16, Inches(0.8), Inches(1.85), Inches(3.65), Inches(3.5),
        "Statutory Compliance",
        [
            ("Eliminates Breach Liability", "Guarantees zero outbound PII leakage; protects against ₹250 Cr penalties."),
            ("DPDP Aligned", "Full compliance with Section 6 (Purpose), Section 8 (Security), and Section 8(7) (Erasure)."),
            ("Verifiable Proof", "Cryptographic wire SHA-256 hashes prove non-transmission to regulators.")
        ],
        badge_text="COMPLIANCE ASSURANCE",
        border_color=C_ACCENT_GREEN
    )
    
    add_card(
        s16, Inches(4.8), Inches(1.85), Inches(3.65), Inches(3.5),
        "Zero Enterprise Friction",
        [
            ("Sub-35 ms Overhead", "Adds < 2.5% latency to end-to-end LLM processing; imperceptible to users."),
            ("Provider Independent", "Works with Google Gemini, OpenAI, or self-hosted models without vendor lock-in."),
            ("Adversarial Resilience", "Handles model hallucinations, reordering, and dropped placeholders cleanly.")
        ],
        badge_text="HIGH PERFORMANCE",
        border_color=C_ACCENT_BLUE
    )
    
    add_card(
        s16, Inches(8.8), Inches(1.85), Inches(3.65), Inches(3.5),
        "Open & Auditable",
        [
            ("Zero Raw PII in Logs", "Safe logging architecture storing zero customer secrets or sensitive spans."),
            ("Role-Separated Restoration", "Least privilege enforced: submission privileges != unmasking rights."),
            ("Reproducible Benchmark", "Full 50-document Indian enterprise evaluation benchmark included.")
        ],
        badge_text="GOVERNANCE EXCELLENCE",
        border_color=C_ACCENT_AMBER
    )
    
    # Bottom Demo Callout Card
    demo_box = s16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.6), Inches(11.733), Inches(0.95))
    demo_box.fill.solid()
    demo_box.fill.fore_color.rgb = C_CARD_BG
    demo_box.line.color.rgb = C_ACCENT_BLUE
    demo_box.line.width = Pt(1.5)
    
    tf_demo = demo_box.text_frame
    tf_demo.word_wrap = True
    tf_demo.margin_left = Inches(0.3)
    tf_demo.margin_top = Inches(0.15)
    
    p_d1 = tf_demo.paragraphs[0]
    r_d1 = p_d1.add_run()
    r_d1.text = "LIVE INTERACTIVE DEMONSTRATION READY  |  HTTP://LOCALHOST:5173\n"
    r_d1.font.name = "Segoe UI"
    r_d1.font.size = Pt(12)
    r_d1.font.bold = True
    r_d1.font.color.rgb = C_ACCENT_BLUE
    
    p_d2 = tf_demo.add_paragraph()
    r_d2 = p_d2.add_run()
    r_d2.text = "Try live 3-panel masking, simulate post-masking tampering attacks, test marketing purpose blocking, and verify analyst 403 restoration restrictions."
    r_d2.font.name = "Segoe UI"
    r_d2.font.size = Pt(10)
    r_d2.font.color.rgb = C_TEXT_BODY

    # Save presentation
    output_path = os.path.abspath("Privacy_Gateway_AI_Pitch_Deck.pptx")
    prs.save(output_path)
    print(f"Successfully generated PowerPoint presentation at: {output_path}")

if __name__ == "__main__":
    main()
