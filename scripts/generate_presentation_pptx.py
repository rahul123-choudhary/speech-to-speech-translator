import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor


# Color Palette
CLR_PRIMARY = RGBColor(30, 27, 75)      # #1e1b4b (Deep Indigo)
CLR_ACCENT = RGBColor(67, 56, 202)      # #4338ca (Vibrant Indigo)
CLR_TEXT_DARK = RGBColor(15, 23, 42)    # #0f172a (Slate Dark)
CLR_TEXT_MUTED = RGBColor(71, 85, 105)  # #475569 (Slate Muted)
CLR_BG_CARD = RGBColor(248, 250, 252)   # #f8fafc (Card Background)
CLR_BORDER = RGBColor(203, 213, 225)    # #cbd5e1 (Card Border)
CLR_WHITE = RGBColor(255, 255, 255)
CLR_GREEN_BG = RGBColor(236, 253, 245)  # #ecfdf5 (Speaking Box BG)
CLR_GREEN_BORDER = RGBColor(5, 150, 105)# #059669 (Speaking Box Border)
CLR_GREEN_TEXT = RGBColor(6, 78, 59)    # #064e3b (Speaking Box Text)
CLR_FLOW_BG = RGBColor(238, 242, 255)   # #eef2ff (Flow Box BG)
CLR_FLOW_BORDER = RGBColor(99, 102, 241)# #6366f1 (Flow Box Border)


def add_slide_header(slide, title_text, subtitle_text):
    """Add a professional title and subtitle header on a slide."""
    header_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.13), Inches(0.95))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_title = tf.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = "Arial"
    p_title.font.size = Pt(20)
    p_title.font.bold = True
    p_title.font.color.rgb = CLR_PRIMARY

    p_sub = tf.add_paragraph()
    p_sub.text = subtitle_text
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(11)
    p_sub.font.bold = True
    p_sub.font.color.rgb = CLR_ACCENT
    p_sub.space_before = Pt(3)

    # Dividing line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(1.35), Inches(12.13), Inches(0.02)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = CLR_BORDER
    line.line.color.rgb = CLR_BORDER


def add_flow_diagram(slide, steps, top_y=Inches(4.4), height=Inches(1.05)):
    """Draw a connected horizontal dataflow diagram on the slide."""
    n = len(steps)
    total_w = 12.13
    box_w = (total_w - (n - 1) * 0.35) / n

    for i, step_text in enumerate(steps):
        left_x = 0.6 + i * (box_w + 0.35)
        # Flow step box
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(left_x), top_y, Inches(box_w), height
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = CLR_FLOW_BG
        shape.line.color.rgb = CLR_FLOW_BORDER
        shape.line.width = Pt(1.5)

        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.08)
        tf.margin_right = Inches(0.08)
        tf.margin_top = Inches(0.08)
        tf.margin_bottom = Inches(0.08)
        
        lines = step_text.split("\n")
        p0 = tf.paragraphs[0]
        p0.text = lines[0]
        p0.alignment = PP_ALIGN.CENTER
        p0.font.name = "Arial"
        p0.font.size = Pt(9.5)
        p0.font.bold = True
        p0.font.color.rgb = CLR_PRIMARY

        if len(lines) > 1:
            p1 = tf.add_paragraph()
            p1.text = lines[1]
            p1.alignment = PP_ALIGN.CENTER
            p1.font.name = "Arial"
            p1.font.size = Pt(8)
            p1.font.color.rgb = CLR_TEXT_MUTED
            p1.space_before = Pt(2)

        # Connector Arrow
        if i < n - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW,
                Inches(left_x + box_w + 0.08), top_y + Inches(0.38), Inches(0.20), Inches(0.25)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = CLR_ACCENT
            arrow.line.fill.background()


def add_speaking_box(slide, speaking_text, top_y=Inches(5.7), height=Inches(1.3)):
    """Add a green callout box with stage presentation speaking script."""
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.6), top_y, Inches(12.13), height
    )
    box.fill.solid()
    box.fill.fore_color.rgb = CLR_GREEN_BG
    box.line.color.rgb = CLR_GREEN_BORDER
    box.line.width = Pt(1.5)

    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Inches(0.1)
    tf.margin_bottom = Inches(0.1)

    p0 = tf.paragraphs[0]
    p0.text = "🗣️ Presentation Speaking Script (Stage par kya bolna hai):"
    p0.font.name = "Arial"
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(5, 150, 105)

    p1 = tf.add_paragraph()
    p1.text = speaking_text
    p1.font.name = "Arial"
    p1.font.size = Pt(9.5)
    p1.font.color.rgb = CLR_GREEN_TEXT
    p1.space_before = Pt(3)


def generate_pptx():
    # Save strictly OUTSIDE project directory
    desktop_dir = Path(r"C:\Users\rahul\OneDrive\Desktop")
    if not desktop_dir.exists():
        desktop_dir = Path(r"C:\Users\rahul\Downloads")
    downloads_dir = Path(r"C:\Users\rahul\Downloads")

    target_paths = [
        desktop_dir / "S2ST_60_Percent_Presentation.pptx",
        downloads_dir / "S2ST_60_Percent_Presentation.pptx",
    ]

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: COVER SLIDE
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)

    # Top Hero Banner
    banner = slide1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(0.6), Inches(12.13), Inches(2.2)
    )
    banner.fill.solid()
    banner.fill.fore_color.rgb = CLR_PRIMARY
    banner.line.color.rgb = CLR_ACCENT
    banner.line.width = Pt(2)

    tf1 = banner.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Direct Speech-to-Speech Translation (S2ST) System"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = CLR_WHITE

    p2 = tf1.add_paragraph()
    p2.text = "Yorùbá Oral Speech to English & Multilingual Synthesis | 60% Project Milestone"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.name = "Arial"
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(199, 210, 254)
    p2.space_before = Pt(8)

    p3 = tf1.add_paragraph()
    p3.text = "Team Contributions, Dedicated Dataflows & Technical Architecture Breakdown"
    p3.alignment = PP_ALIGN.CENTER
    p3.font.name = "Arial"
    p3.font.size = Pt(10.5)
    p3.font.color.rgb = RGBColor(224, 231, 255)
    p3.space_before = Pt(5)

    # 4 Pillar Cards on Slide 1
    cards_info = [
        ("MEMBER 1: DATA LEAD", "Dataset Engineering", "IWSLT 2026 Yorùbá Corpus\nNative Review Gate (5/5)\nApproved Train/Val/Test Splits"),
        ("MEMBER 2: TRAINING LEAD", "DL Architecture & LoRA", "Direct S2ST (XLS-R Backbone)\nRank-8 LoRA (19.8% Params)\nUnit Decoder & PyTorch Loop"),
        ("MEMBER 3: TESTING LEAD", "Codec & Evaluation", "24 kHz Meta EnCodec Vocoder\nWhisper ASR-BLEU Testing\nInference Latency Profiling"),
        ("MEMBER 4: RAHUL CHOUDHARY", "Lead Full-Stack Architect", "Interactive Web Studio UI\nMic Recording & 57 Demo Clips\nWebSocket & Voice Synthesis"),
    ]

    card_w = 2.82
    for i, (m_tag, m_title, m_desc) in enumerate(cards_info):
        left_c = 0.6 + i * (card_w + 0.28)
        card = slide1.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(left_c), Inches(3.1), Inches(card_w), Inches(2.7)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = CLR_BG_CARD if i < 3 else CLR_FLOW_BG
        card.line.color.rgb = CLR_BORDER if i < 3 else CLR_ACCENT
        card.line.width = Pt(1 if i < 3 else 2)

        tf_c = card.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = tf_c.margin_right = Inches(0.15)
        tf_c.margin_top = Inches(0.15)

        p_tag = tf_c.paragraphs[0]
        p_tag.text = m_tag
        p_tag.font.name = "Arial"
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = CLR_ACCENT if i == 3 else CLR_TEXT_DARK

        p_tit = tf_c.add_paragraph()
        p_tit.text = m_title
        p_tit.font.name = "Arial"
        p_tit.font.size = Pt(11)
        p_tit.font.bold = True
        p_tit.font.color.rgb = CLR_PRIMARY
        p_tit.space_before = Pt(4)

        p_des = tf_c.add_paragraph()
        p_des.text = m_desc
        p_des.font.name = "Arial"
        p_des.font.size = Pt(8.5)
        p_des.font.color.rgb = CLR_TEXT_MUTED
        p_des.space_before = Pt(8)

    # Bottom Metadata Strip
    strip = slide1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(6.1), Inches(12.13), Inches(0.7)
    )
    strip.fill.solid()
    strip.fill.fore_color.rgb = RGBColor(238, 242, 255)
    strip.line.color.rgb = RGBColor(199, 210, 254)

    tf_s = strip.text_frame
    tf_s.word_wrap = True
    p_s = tf_s.paragraphs[0]
    p_s.text = "Language Pair: Yorùbá (yo) → English (en)   |   Dataset: IWSLT 2026 African S2ST   |   Milestone: 60% Core Baseline Completed   |   Team: 4 Dedicated Streams"
    p_s.alignment = PP_ALIGN.CENTER
    p_s.font.name = "Arial"
    p_s.font.size = Pt(10)
    p_s.font.bold = True
    p_s.font.color.rgb = CLR_PRIMARY

    # =========================================================================
    # SLIDE 2: PROJECT INTRODUCTION & GLOBAL DATAFLOW
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide2,
        "1. Project Overview & Global System Architecture",
        "Direct Speech-to-Speech translation bypassing traditional text bottlenecks"
    )

    # Left Overview Card
    card_l = slide2.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.6), Inches(1.55), Inches(5.9), Inches(2.6)
    )
    card_l.fill.solid()
    card_l.fill.fore_color.rgb = CLR_BG_CARD
    card_l.line.color.rgb = CLR_BORDER
    tf_l = card_l.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_right = Inches(0.2)
    tf_l.margin_top = Inches(0.15)

    p = tf_l.paragraphs[0]
    p.text = "Why Direct Speech-to-Speech Translation?"
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY

    bullets_l = [
        "Traditional Cascades: Speech → ASR (Text) → MT (Translation) → TTS (Speech).",
        "Cascaded Problem: Accumulates recognition errors, introduces high latency, and destroys oral emotion and vocal nuance.",
        "Direct S2ST Approach: Directly maps source acoustic frames to discrete target speech units without text transcription bottle-necks.",
        "Language Focus: Preserves oral-tradition low-resource Yorùbá speech with aligned English reference waveforms."
    ]
    for b in bullets_l:
        p_b = tf_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(3)

    # Right Overview Card (60% Milestone Achieved)
    card_r = slide2.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(6.83), Inches(1.55), Inches(5.9), Inches(2.6)
    )
    card_r.fill.solid()
    card_r.fill.fore_color.rgb = CLR_BG_CARD
    card_r.line.color.rgb = CLR_BORDER
    tf_r = card_r.text_frame
    tf_r.word_wrap = True
    tf_r.margin_left = tf_r.margin_right = Inches(0.2)
    tf_r.margin_top = Inches(0.15)

    p = tf_r.paragraphs[0]
    p.text = "60% Milestone Achievements (Core Baseline)"
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY

    bullets_r = [
        "Phase 1 (0–20%): IWSLT dataset ingestion, 16kHz WAV normalization, native review gate & JSONL splits.",
        "Phase 2 (20–40%): Direct S2ST architecture (XLS-R backbone), LoRA Rank-8 adaptation & transformer unit decoder.",
        "Phase 3 (40–60%): 24 kHz Meta EnCodec vocoder, Whisper ASR-BLEU testing harness & latency tracking.",
        "System Delivery: FastAPI WebSocket streaming engine, interactive Web Studio UI & 57 preset demo audio clips."
    ]
    for b in bullets_r:
        p_b = tf_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(3)

    # Flow label
    lbl = slide2.shapes.add_textbox(Inches(0.6), Inches(4.25), Inches(12.13), Inches(0.3))
    lbl.text_frame.paragraphs[0].text = "Global End-to-End System Dataflow Pipeline:"
    lbl.text_frame.paragraphs[0].font.name = "Arial"
    lbl.text_frame.paragraphs[0].font.size = Pt(11)
    lbl.text_frame.paragraphs[0].font.bold = True
    lbl.text_frame.paragraphs[0].font.color.rgb = CLR_PRIMARY

    # Global Flow Diagram
    add_flow_diagram(
        slide2,
        [
            "1. Yorùbá Speech\n(16 kHz Mono PCM)",
            "2. Speech Encoder\n(XLS-R Features)",
            "3. LoRA Adaptation\n(Rank-8 Efficient)",
            "4. Unit Decoder\n(Speech Tokens)",
            "5. Neural Codec\n(24kHz EnCodec)",
            "6. Target Speech\n(English WAV Output)",
        ],
        top_y=Inches(4.6),
        height=Inches(1.0)
    )

    # Bottom Handoff Note
    add_speaking_box(
        slide2,
        "System Data Handoff Chain: Member 1 (curates & validates raw audio into approved JSONL manifests) → Member 2 (extracts acoustic features & predicts discrete speech units) → Member 3 (reconstructs audio via 24kHz Neural Codec & verifies quality via Whisper ASR-BLEU) → Member 4 (integrates into live Web Studio, real-time WebSocket streaming server & live demo platform).",
        top_y=Inches(5.8),
        height=Inches(1.2)
    )

    # =========================================================================
    # SLIDE 3: MEMBER 1 — DATA WALA KAAM
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide3,
        "2. Contribution of Member 1 — Dataset Engineering & Curation (Data Lead)",
        "Speech corpus ingestion, audio normalization, native speaker review gate & approved manifests"
    )

    # Top Content Cards
    card1_l = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(5.9), Inches(2.55))
    card1_l.fill.solid()
    card1_l.fill.fore_color.rgb = CLR_BG_CARD
    card1_l.line.color.rgb = CLR_BORDER
    tf1_l = card1_l.text_frame
    tf1_l.word_wrap = True
    tf1_l.margin_left = tf1_l.margin_right = Inches(0.18)
    tf1_l.margin_top = Inches(0.12)
    p = tf1_l.paragraphs[0]
    p.text = "Core Technical Deliverables (60% Scope)"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m1_a = [
        "IWSLT 2026 Corpus Extraction: Downloaded and aligned parallel Yorùbá speech with English reference translations.",
        "Audio Standardization: Converted 57 audio pairs into standard 16 kHz mono 16-bit WAV format.",
        "SHA-256 Integrity Checksums: Generated unique cryptographic hashes for every raw audio file to prevent corruption.",
        "Native Review Quality Gate: Built native_review.csv assessing translation fidelity, intelligibility, and cultural fit (5/5).",
        "Disjoint Partitioning: Created approved manifests: train.jsonl (45 pairs), validation.jsonl (6 pairs), and test.jsonl."
    ]
    for b in bullets_m1_a:
        p_b = tf1_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    card1_r = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.83), Inches(1.55), Inches(5.9), Inches(2.55))
    card1_r.fill.solid()
    card1_r.fill.fore_color.rgb = CLR_BG_CARD
    card1_r.line.color.rgb = CLR_BORDER
    tf1_r = card1_r.text_frame
    tf1_r.word_wrap = True
    tf1_r.margin_left = tf1_r.margin_right = Inches(0.18)
    tf1_r.margin_top = Inches(0.12)
    p = tf1_r.paragraphs[0]
    p.text = "Implementation & Quality Assurance"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m1_b = [
        "Dataset Source: Official IWSLT 2026 African S2ST release (McGill-NLP/NaijaS2ST).",
        "Target Hours: ~2.0 hours of high-quality validated conversational audio pairs.",
        "Native Review Protocol: Strict gate requiring native reviewer ID and 5-point scores before any row can be trained.",
        "Data Location: data/iwslt2026_yoruba/raw/ (audio) & data/iwslt2026_yoruba/processed/approved/ (manifests).",
        "Key Scripts: scripts/fetch_iwslt_yoruba_subset.py, s2st/data.py, s2st/prepare.py."
    ]
    for b in bullets_m1_b:
        p_b = tf1_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    # Member 1 Dataflow Diagram
    lbl = slide3.shapes.add_textbox(Inches(0.6), Inches(4.2), Inches(12.13), Inches(0.3))
    lbl.text_frame.paragraphs[0].text = "Member 1 Dedicated Dataflow Pipeline:"
    lbl.text_frame.paragraphs[0].font.name = "Arial"
    lbl.text_frame.paragraphs[0].font.size = Pt(10.5)
    lbl.text_frame.paragraphs[0].font.bold = True
    lbl.text_frame.paragraphs[0].font.color.rgb = CLR_PRIMARY

    add_flow_diagram(
        slide3,
        [
            "1. Raw IWSLT Corpus\n(Upstream 85GB Release)",
            "2. Subset Filter\n(fetch_iwslt_subset.py)",
            "3. Audio Normalization\n(16 kHz Mono WAV)",
            "4. SHA-256 Check\n(Integrity Checksums)",
            "5. Native Review Gate\n(Fidelity & Cultural 5/5)",
            "6. Approved Splits\n(train/val/test.jsonl)",
        ],
        top_y=Inches(4.5),
        height=Inches(0.95)
    )

    # Speaking Box
    add_speaking_box(
        slide3,
        "\"Mera role is project mein Data Engineering aur Curation ka tha. Kisi bhi deep learning speech model ke liye high-quality paired audio sabse important foundation hoti hai. Maine official IWSLT 2026 dataset se Yorùbá aur English ke matched audio pairs extract kiye, sabhi raw clips ko 16 kHz mono WAV format mein standardize kiya, aur SHA-256 checksums se verify kiya. Uske baad native speaker review gate implement kiya jisme translation fidelity aur cultural appropriateness verify ki gayi. Finally, maine data ko approved Train, Validation aur Test splits mein format karke Member 2 ko training ke liye handover kiya.\"",
        top_y=Inches(5.6),
        height=Inches(1.45)
    )

    # =========================================================================
    # SLIDE 4: MEMBER 2 — TRAINING PART
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide4,
        "3. Contribution of Member 2 — Deep Learning Architecture & Training (Training Lead)",
        "Direct S2ST model design, parameter-efficient LoRA adaptation, unit decoder & PyTorch pipeline"
    )

    # Top Content Cards
    card2_l = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(5.9), Inches(2.55))
    card2_l.fill.solid()
    card2_l.fill.fore_color.rgb = CLR_BG_CARD
    card2_l.line.color.rgb = CLR_BORDER
    tf2_l = card2_l.text_frame
    tf2_l.word_wrap = True
    tf2_l.margin_left = tf2_l.margin_right = Inches(0.18)
    tf2_l.margin_top = Inches(0.12)
    p = tf2_l.paragraphs[0]
    p.text = "Core Technical Deliverables (60% Scope)"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m2_a = [
        "Direct S2ST Architecture: End-to-end direct acoustic network in s2st/model.py without intermediate text tokens.",
        "Multilingual Speech Backbone: Self-supervised XLS-R / W2V-BERT encoder capturing rich phonetic representations.",
        "Parameter-Efficient LoRA (Rank=8): Frozen 80% base backbone, adapting only query/value attention projections.",
        "Acoustic Unit Decoder: Multi-layer cross-attention transformer predicting target discrete speech tokens.",
        "PyTorch Training Loop: Dynamic zero-padding, batch collation, cross-entropy unit loss, and AdamW optimizer."
    ]
    for b in bullets_m2_a:
        p_b = tf2_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    card2_r = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.83), Inches(1.55), Inches(5.9), Inches(2.55))
    card2_r.fill.solid()
    card2_r.fill.fore_color.rgb = CLR_BG_CARD
    card2_r.line.color.rgb = CLR_BORDER
    tf2_r = card2_r.text_frame
    tf2_r.word_wrap = True
    tf2_r.margin_left = tf2_r.margin_right = Inches(0.18)
    tf2_r.margin_top = Inches(0.12)
    p = tf2_r.paragraphs[0]
    p.text = "Model Specifications & Hyperparameters"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m2_b = [
        "Total Network Parameters: 393,747,072.",
        "Trainable LoRA Parameters: 78,308,352 (19.89%) — ~80% compute reduction.",
        "Acoustic Token Vocabulary: 1,024 discrete acoustic clusters.",
        "Loss Objective: Cross-entropy token loss + auxiliary duration alignment.",
        "Key Scripts: s2st/model.py, s2st/train.py, configs/yor_en_s2st.yaml, scripts/run_train.py."
    ]
    for b in bullets_m2_b:
        p_b = tf2_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    # Member 2 Dataflow Diagram
    lbl = slide4.shapes.add_textbox(Inches(0.6), Inches(4.2), Inches(12.13), Inches(0.3))
    lbl.text_frame.paragraphs[0].text = "Member 2 Dedicated Dataflow Pipeline:"
    lbl.text_frame.paragraphs[0].font.name = "Arial"
    lbl.text_frame.paragraphs[0].font.size = Pt(10.5)
    lbl.text_frame.paragraphs[0].font.bold = True
    lbl.text_frame.paragraphs[0].font.color.rgb = CLR_PRIMARY

    add_flow_diagram(
        slide4,
        [
            "1. Approved Manifests\n(from Member 1)",
            "2. Dynamic Batching\n(Zero-padding collation)",
            "3. XLS-R Speech Encoder\n(Acoustic Representations)",
            "4. LoRA Adapters\n(Rank-8 Efficient Layers)",
            "5. Transformer Decoder\n(Cross-Attention Predictor)",
            "6. Discrete Tokens\n(Predicted Speech Units)",
        ],
        top_y=Inches(4.5),
        height=Inches(0.95)
    )

    # Speaking Box
    add_speaking_box(
        slide4,
        "\"Mera role is project mein Model Architecture aur Deep Learning Training par tha. Hamara goal intermediate text transcription ke bina Direct Speech-to-Speech translation achieve karna hai. Iske liye maine multilingual XLS-R speech encoder use kiya aur uspar Parameter-Efficient LoRA (Rank=8) fine-tuning lagayi. Isse pure 393M parameters ke bajaye sirf ~19.8% parameters par efficient training hoti hai, jo catastrophic forgetting ko rokti hai. Saath hi maine Transformer-based Unit Decoder design kiya jo discrete speech tokens predict karta hai. Maine end-to-end PyTorch training pipeline, dynamic batching aur loss functions configure karke Member 3 ko handover kiya.\"",
        top_y=Inches(5.6),
        height=Inches(1.45)
    )

    # =========================================================================
    # SLIDE 5: MEMBER 3 — TESTING PART
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide5,
        "4. Contribution of Member 3 — Neural Codec, Synthesis & Evaluation (Testing Lead)",
        "24 kHz Neural Codec vocoding, OpenAI Whisper ASR-BLEU benchmark harness & automated regression tests"
    )

    # Top Content Cards
    card3_l = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(5.9), Inches(2.55))
    card3_l.fill.solid()
    card3_l.fill.fore_color.rgb = CLR_BG_CARD
    card3_l.line.color.rgb = CLR_BORDER
    tf3_l = card3_l.text_frame
    tf3_l.word_wrap = True
    tf3_l.margin_left = tf3_l.margin_right = Inches(0.18)
    tf3_l.margin_top = Inches(0.12)
    p = tf3_l.paragraphs[0]
    p.text = "Core Technical Deliverables (60% Scope)"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m3_a = [
        "24 kHz Neural Codec Vocoder: Integrated Meta EnCodec in s2st/codec.py to reconstruct high-fidelity audio from tokens.",
        "ASR-BLEU Testing Harness: Developed automated transcription using OpenAI Whisper to score generated audio against English references.",
        "Objective Error Metrics: Built evaluation framework computing corpus-level BLEU, Character Error Rate (CER), and WER.",
        "Inference Latency Tracking: Created per-utterance latency profiling capturing Mean, p50, and p95 response time in milliseconds.",
        "Automated Test Suite: Created PyTest test cases (tests/test_prepare.py, tests/test_target_language.py) validating tensor shapes."
    ]
    for b in bullets_m3_a:
        p_b = tf3_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    card3_r = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.83), Inches(1.55), Inches(5.9), Inches(2.55))
    card3_r.fill.solid()
    card3_r.fill.fore_color.rgb = CLR_BG_CARD
    card3_r.line.color.rgb = CLR_BORDER
    tf3_r = card3_r.text_frame
    tf3_r.word_wrap = True
    tf3_r.margin_left = tf3_r.margin_right = Inches(0.18)
    tf3_r.margin_top = Inches(0.12)
    p = tf3_r.paragraphs[0]
    p.text = "Evaluation Harness Specifications"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m3_b = [
        "Synthesis Output Rate: 24,000 Hz, 16-bit PCM Linear WAV.",
        "ASR Model: OpenAI Whisper for transcription and objective scoring.",
        "Metric Benchmark: SacreBLEU (corpus-level translation adequacy) & CER.",
        "Publication Export: scripts/generate_publication_report.py exports LaTeX tables and markdown summaries.",
        "Key Scripts: s2st/codec.py, s2st/evaluate.py, scripts/generate_publication_report.py, tests/."
    ]
    for b in bullets_m3_b:
        p_b = tf3_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    # Member 3 Dataflow Diagram
    lbl = slide5.shapes.add_textbox(Inches(0.6), Inches(4.2), Inches(12.13), Inches(0.3))
    lbl.text_frame.paragraphs[0].text = "Member 3 Dedicated Dataflow Pipeline:"
    lbl.text_frame.paragraphs[0].font.name = "Arial"
    lbl.text_frame.paragraphs[0].font.size = Pt(10.5)
    lbl.text_frame.paragraphs[0].font.bold = True
    lbl.text_frame.paragraphs[0].font.color.rgb = CLR_PRIMARY

    add_flow_diagram(
        slide5,
        [
            "1. Predicted Tokens\n(from Member 2)",
            "2. EnCodec 24 kHz\n(Neural Codec Vocoder)",
            "3. Synthesized Audio\n(Reconstructed WAV)",
            "4. Whisper ASR\n(Automated Transcript)",
            "5. Metric Scoring\n(ASR-BLEU & CER)",
            "6. Latency Profiling\n(Mean, p50, p95 ms)",
        ],
        top_y=Inches(4.5),
        height=Inches(0.95)
    )

    # Speaking Box
    add_speaking_box(
        slide5,
        "\"Mera part is project mein Acoustic Codec, Testing aur Evaluation ka tha. Model jo discrete tokens predict karta hai, usko high-fidelity sound wave mein convert karne ke liye maine 24 kHz EnCodec Neural Codec vocoder integrate kiya. Quality testing ke liye maine ek automated evaluation framework develop kiya jo OpenAI Whisper speech recognizer ke through output speech ko transcribe karke ASR-BLEU score aur CER calculate karta hai. Saath hi per-utterance response latency track karne ka benchmark system banaya aur automated PyTest regression suites maintain kiye. Is verified speech synthesis engine ko maine Member 4 ko live Web Studio integration ke liye hand over kiya.\"",
        top_y=Inches(5.6),
        height=Inches(1.45)
    )

    # =========================================================================
    # SLIDE 6: MEMBER 4 — RAHUL CHOUDHARY (FULL-STACK LEAD)
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide6,
        "5. Contribution of Member 4 — Rahul Choudhary (Lead Full-Stack Architect)",
        "Interactive Web Studio UI, microphone recording, 57 demo clips, real-time WebSocket streaming & voice synthesis"
    )

    # Top Content Cards
    card4_l = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.55), Inches(5.9), Inches(2.55))
    card4_l.fill.solid()
    card4_l.fill.fore_color.rgb = CLR_FLOW_BG
    card4_l.line.color.rgb = CLR_ACCENT
    card4_l.line.width = Pt(2)
    tf4_l = card4_l.text_frame
    tf4_l.word_wrap = True
    tf4_l.margin_left = tf4_l.margin_right = Inches(0.18)
    tf4_l.margin_top = Inches(0.12)
    p = tf4_l.paragraphs[0]
    p.text = "Core Technical Deliverables (60% Scope)"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m4_a = [
        "Interactive Web Studio UI: Built modern landing page (s2st/landing.html) and translator interface (s2st/ui.html) with wave visualizer.",
        "Live Mic Recording & Upload: 16 kHz mono 16-bit PCM browser microphone capture with canvas wave visualizer + WAV file upload.",
        "57 Pre-loaded Demo Audio Clips: Clickable catalog across 4 categories (Weather, Sports, Civic, Society) for 1-click live demo.",
        "Emotion & Speed Controls: Acoustic emotion detection engine + UI sliders (Joyful, Serious, Calm) + speed controls (0.75x–1.5x).",
        "FastAPI WebSocket Streaming: Low-latency /v1/sessions/{id}/stream handling chunk buffering, base64 protocol & audio dispatch."
    ]
    for b in bullets_m4_a:
        p_b = tf4_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    card4_r = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.83), Inches(1.55), Inches(5.9), Inches(2.55))
    card4_r.fill.solid()
    card4_r.fill.fore_color.rgb = CLR_BG_CARD
    card4_r.line.color.rgb = CLR_BORDER
    tf4_r = card4_r.text_frame
    tf4_r.word_wrap = True
    tf4_r.margin_left = tf4_r.margin_right = Inches(0.18)
    tf4_r.margin_top = Inches(0.12)
    p = tf4_r.paragraphs[0]
    p.text = "System Integration, Audio & Launch Automation"
    p.font.name = "Arial"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = CLR_PRIMARY
    bullets_m4_b = [
        "Multilingual Voice Synthesis: Connected neural voices for English, Hindi, Odia, Telugu, Tamil, and Bengali.",
        "Firebase Auth & Atlas Status: Firebase Email/Password sign-in, MongoDB Atlas status, and 1–5 star Human Evaluation rating form.",
        "One-Click Launcher (run_backend.bat): Automated port-conflict detection, stale process killing, and one-click app startup.",
        "Instant Demo Advantage: Presentation panel can test live speech with one click without microphone permissions.",
        "Key Files Owned: s2st/ui.html, s2st/landing.html, s2st/api.py, s2st/voices.py, run_backend.bat."
    ]
    for b in bullets_m4_b:
        p_b = tf4_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.name = "Arial"
        p_b.font.size = Pt(8.5)
        p_b.font.color.rgb = CLR_TEXT_DARK
        p_b.space_before = Pt(2.5)

    # Member 4 Dataflow Diagram
    lbl = slide6.shapes.add_textbox(Inches(0.6), Inches(4.2), Inches(12.13), Inches(0.3))
    lbl.text_frame.paragraphs[0].text = "Member 4 Dedicated End-to-End System Dataflow Pipeline:"
    lbl.text_frame.paragraphs[0].font.name = "Arial"
    lbl.text_frame.paragraphs[0].font.size = Pt(10.5)
    lbl.text_frame.paragraphs[0].font.bold = True
    lbl.text_frame.paragraphs[0].font.color.rgb = CLR_PRIMARY

    add_flow_diagram(
        slide6,
        [
            "1. Browser Mic / Demo\n(16kHz PCM audio)",
            "2. Web Studio UI\n(Waveform Visualizer)",
            "3. WebSocket Engine\n(Chunked Streaming)",
            "4. Translation Engine\n(Direct / Multilingual)",
            "5. Emotion & Prosody\n(Speed & Style synthesis)",
            "6. Audio Output\n(Low-Latency Playback)",
        ],
        top_y=Inches(4.5),
        height=Inches(0.95)
    )

    # Speaking Box
    add_speaking_box(
        slide6,
        "\"Mera role is pure project ka Interactive Web Studio, Live Streaming API aur End-to-End System Integration build karna tha. Maine pura user-facing Web Application design kiya hai. Isme live microphone recording ke saath maine 57 pre-loaded native Yorùbá audio clips bhi integrate kiye hain categories wise—taaki hum presentation mein bina mic ke directly real speech translate karke demo dikha sakein. Backend par maine FastAPI WebSocket streaming engine develop kiya jo low-latency chunked audio handle karta hai. Saath hi acoustic emotion detection aur voice speed controls integrate kiye hain. (Action Tip: Ab screen par browser open karke 1 demo clip play karke live speech sunayein!)\"",
        top_y=Inches(5.6),
        height=Inches(1.45)
    )

    # =========================================================================
    # SLIDE 7: MILESTONE SUMMARY & ROADMAP
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    add_slide_header(
        slide7,
        "6. Milestone Progress Matrix & Future Roadmap",
        "Current 60% Core Baseline Completed vs Remaining 40% Future Scope"
    )

    # Comparison Table
    table_shape = slide7.shapes.add_table(5, 4, Inches(0.6), Inches(1.55), Inches(12.13), Inches(3.6))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(2.2)
    tbl.columns[1].width = Inches(1.8)
    tbl.columns[2].width = Inches(4.3)
    tbl.columns[3].width = Inches(3.83)

    headers = ["Project Workstream", "Lead Member", "60% Completed Core Work (Achieved)", "Remaining 40% Scope (Upcoming)"]
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CLR_PRIMARY
        cell.text = h
        p = cell.text_frame.paragraphs[0]
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = CLR_WHITE

    row_data = [
        ("Dataset Engineering", "Member 1", "IWSLT 2026 Yorùbá corpus, 16kHz WAV normalization, Native review gate (5/5), verified train/val/test JSONL splits.", "Corpus expansion across diverse regional Yorùbá oral dialects."),
        ("Model Architecture", "Member 2", "Direct S2ST model, XLS-R encoder, Rank-8 LoRA adapter (19.8% trainable params), unit decoder & PyTorch loop.", "Multi-epoch GPU convergence training to generate final best.pt checkpoint weights."),
        ("Testing & Codec", "Member 3", "24kHz EnCodec vocoder integration, OpenAI Whisper ASR-BLEU benchmark harness, automated PyTest suite & latency tracking.", "Official held-out test set benchmark evaluation, human MOS ratings & publication report."),
        ("Full-Stack Studio & Pilot", "Member 4 (Rahul)", "Complete Web Studio UI, Mic recorder, 57 demo clips player, WebSocket streaming, emotion prosody, launchers.", "Large-scale production pilot testing with native community speakers."),
    ]

    for i, row in enumerate(row_data, start=1):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CLR_BG_CARD if i % 2 == 1 else CLR_WHITE
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.name = "Arial"
            p.font.size = Pt(9)
            if j == 0:
                p.font.bold = True
                p.font.color.rgb = CLR_PRIMARY
            elif j == 1:
                p.font.bold = True
                p.font.color.rgb = CLR_ACCENT
            elif j == 2:
                p.font.color.rgb = RGBColor(21, 128, 61) # Green
            else:
                p.font.color.rgb = CLR_TEXT_MUTED

    # Bottom RoadMap Note
    add_speaking_box(
        slide7,
        "Presentation Summary: The 60% Core Baseline is fully functional and auditable across all 4 workstreams—from data preparation and model architecture to neural codec testing and the full interactive Web Studio. The remaining 40% will focus on multi-epoch GPU training for final model weights and held-out benchmark evaluation.",
        top_y=Inches(5.4),
        height=Inches(1.2)
    )

    # =========================================================================
    # SLIDE 8: THANK YOU & LIVE DEMO
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)

    # Center Hero Card
    hero = slide8.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1.5), Inches(1.2), Inches(10.33), Inches(5.1)
    )
    hero.fill.solid()
    hero.fill.fore_color.rgb = CLR_PRIMARY
    hero.line.color.rgb = CLR_ACCENT
    hero.line.width = Pt(2)

    tf_h = hero.text_frame
    tf_h.word_wrap = True
    tf_h.margin_top = Inches(0.4)

    p = tf_h.paragraphs[0]
    p.text = "THANK YOU!"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = CLR_WHITE

    p2 = tf_h.add_paragraph()
    p2.text = "Questions & Technical Discussion"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.name = "Arial"
    p2.font.size = Pt(18)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(199, 210, 254)
    p2.space_before = Pt(8)

    p3 = tf_h.add_paragraph()
    p3.text = "Yorùbá–English Direct Speech-to-Speech Translation Research Project"
    p3.alignment = PP_ALIGN.CENTER
    p3.font.name = "Arial"
    p3.font.size = Pt(12)
    p3.font.color.rgb = RGBColor(224, 231, 255)
    p3.space_before = Pt(8)

    p4 = tf_h.add_paragraph()
    p4.text = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    p4.alignment = PP_ALIGN.CENTER
    p4.font.name = "Arial"
    p4.font.size = Pt(11)
    p4.font.color.rgb = CLR_ACCENT
    p4.space_before = Pt(14)

    p5 = tf_h.add_paragraph()
    p5.text = "🎙️ Live Demo Ready: Launch http://127.0.0.1:8000/app to demonstrate real-time Yorùbá speech translation, 57 interactive preset audio clips, acoustic emotion detection & multilingual voice synthesis!"
    p5.alignment = PP_ALIGN.CENTER
    p5.font.name = "Arial"
    p5.font.size = Pt(11)
    p5.font.bold = True
    p5.font.color.rgb = RGBColor(187, 247, 208)  # Light Green
    p5.space_before = Pt(12)

    # Save to all target paths
    for path in target_paths:
        prs.save(str(path))
        print(f"[SUCCESS] PowerPoint presentation saved at: {path}")


if __name__ == "__main__":
    generate_pptx()
