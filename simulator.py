import streamlit as st
import plotly.graph_objects as go
import numpy as np
import io
import re
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

# ─────────────────────────────────────────────
# AIRTABLE CONFIG
# ─────────────────────────────────────────────

AIRTABLE_TOKEN   = st.secrets.get("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = st.secrets.get("AIRTABLE_BASE_ID", "")
AIRTABLE_URL     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

def save_lead(table, fields):
    try:
        requests.post(
            f"{AIRTABLE_URL}/{table}",
            headers={
                "Authorization": f"Bearer {AIRTABLE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"fields": fields},
            timeout=5
        )
    except Exception:
        pass

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Freedom Simulator | The Freedom Project",
    page_icon="freedom_symbol_purple_white.svg",
    layout="wide"
)

# ─────────────────────────────────────────────
# DESIGN SYSTEM
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0B0B0F; color: #F2F2F2; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; }

div[data-testid="stMetric"] {
    background: #0f0f16;
    border-radius: 12px;
    padding: 20px;
    border: 0.5px solid rgba(255,255,255,0.08);
}
div[data-testid="stMetric"] label { color: #71717A !important; font-size: 12px !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #F2F2F2 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

.stButton > button {
    background: #5A54C4; color: white; border-radius: 9px; border: none;
    padding: 12px 28px; font-family: 'Inter', sans-serif; font-weight: 500;
    font-size: 14px; width: 100%;
}
.stButton > button:hover { background: #4840a8; border: none; }

.stProgress > div > div > div > div { background-color: #7F77DD; }
.stSelectbox > div > div { background: #0f0f16; border: 0.5px solid rgba(255,255,255,0.1); border-radius: 8px; }
.stNumberInput > div > div > input { background: #0f0f16; border: 0.5px solid rgba(255,255,255,0.1); border-radius: 8px; color: #F2F2F2; }
.stTextInput > div > div > input { background: #0f0f16; border: 0.5px solid rgba(255,255,255,0.1); border-radius: 8px; color: #F2F2F2; }
.stSlider > div > div > div > div { background: #5A54C4; }

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def card(content, border_color="rgba(255,255,255,0.08)", bg="#0f0f16", padding="28px 24px"):
    return f"""<div style="background:{bg};border:0.5px solid {border_color};border-radius:14px;padding:{padding};margin-bottom:16px">{content}</div>"""

def label(text):
    return f'<div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#3f3f46;font-weight:500;margin-bottom:8px">{text}</div>'

def divider(margin="24px 0"):
    return f'<div style="border-top:0.5px solid rgba(255,255,255,0.07);margin:{margin}"></div>'

# ─────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────

def generate_pdf(inp, score, inv_needed, max_cap, target_cap, fn, fi_age, survives, gap):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    buffer = io.BytesIO()

    # ── COLORS ──
    C_BG       = colors.HexColor("#0B0B0F")
    C_SURFACE  = colors.HexColor("#0f0f16")
    C_SURFACE2 = colors.HexColor("#141420")
    C_PURPLE   = colors.HexColor("#5A54C4")
    C_PURPLE_L = colors.HexColor("#7F77DD")
    C_PURPLE_D = colors.HexColor("#26215C")
    C_YELLOW   = colors.HexColor("#f9f09d")
    C_WHITE    = colors.HexColor("#F2F2F2")
    C_MUTED    = colors.HexColor("#71717A")
    C_SUBTLE   = colors.HexColor("#3f3f46")
    C_LINE     = colors.HexColor("#1f1f2e")
    C_SUCCESS  = colors.HexColor("#4ade80")
    C_WARN     = colors.HexColor("#EF9F27")
    C_ERROR    = colors.HexColor("#E24B4A")

    PW, PH = A4
    ML = MR = 1.8*cm
    MT = MB = 1.8*cm
    W  = PW - ML - MR

    # ── STYLES ──
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    sty_brand    = ps("brand",   fontName="Helvetica-Bold", fontSize=9,  textColor=C_PURPLE,   spaceAfter=0,  leading=12, letterSpacing=1.5)
    sty_cover_h  = ps("coverh",  fontName="Helvetica-Bold", fontSize=38, textColor=C_WHITE,    spaceAfter=8,  leading=44, letterSpacing=-0.5)
    sty_cover_s  = ps("covers",  fontName="Helvetica",      fontSize=11, textColor=C_MUTED,    spaceAfter=0,  leading=16)
    sty_h1       = ps("h1",      fontName="Helvetica-Bold", fontSize=16, textColor=C_WHITE,    spaceAfter=6,  leading=20, spaceBefore=20)
    sty_h2       = ps("h2",      fontName="Helvetica-Bold", fontSize=11, textColor=C_WHITE,    spaceAfter=4,  leading=14, spaceBefore=14)
    sty_body     = ps("body",    fontName="Helvetica",      fontSize=9,  textColor=C_MUTED,    spaceAfter=6,  leading=14, alignment=TA_JUSTIFY)
    sty_body_w   = ps("bodyw",   fontName="Helvetica",      fontSize=9,  textColor=C_WHITE,    spaceAfter=6,  leading=14)
    sty_label    = ps("label",   fontName="Helvetica-Bold", fontSize=7,  textColor=C_SUBTLE,   spaceAfter=2,  leading=10, letterSpacing=1.2)
    sty_value    = ps("value",   fontName="Helvetica-Bold", fontSize=18, textColor=C_WHITE,    spaceAfter=0,  leading=22)
    sty_caption  = ps("cap",     fontName="Helvetica",      fontSize=7,  textColor=C_SUBTLE,   spaceAfter=0,  leading=10)
    sty_insight  = ps("ins",     fontName="Helvetica",      fontSize=9,  textColor=C_MUTED,    spaceAfter=8,  leading=14, leftIndent=12)

    score_hex = "#7F77DD" if score >= 70 else "#EF9F27" if score >= 40 else "#E24B4A"
    C_SCORE   = colors.HexColor(score_hex)
    score_txt = "Strong" if score >= 80 else "On track" if score >= 60 else "Needs attention" if score >= 40 else "At risk"

    r_name    = inp.get("name", "")
    r_email   = inp.get("email", "")
    r_country = inp.get("country", "")
    mi        = inp.get("monthly_investment", 0)
    mc_inc    = inp.get("monthly_income", 0)
    ya        = inp.get("years_accumulation", 0)
    yr        = inp.get("years_retirement", 0)
    ar        = inp.get("ann_return", 0.06)
    profile   = inp.get("profile", "Balanced")
    age       = inp.get("current_age", 30)

    # ── CHART ──
    def make_chart():
        def sim(inv):
            cap, hist, mr = 0, [], ar/12
            for _ in range(ya*12):
                cap = cap*(1+mr)+inv
                hist.append(cap)
            for _ in range(yr*12):
                cap = cap*(1+mr)-mc_inc
                hist.append(max(cap,0))
                if cap <= 0: break
            return hist

        h_cur = sim(mi)
        h_rec = sim(inv_needed)
        x_cur = [i/12 for i in range(len(h_cur))]
        x_rec = [i/12 for i in range(len(h_rec))]

        fig, ax = plt.subplots(figsize=(7.2, 3.2))
        fig.patch.set_facecolor("#0f0f16")
        ax.set_facecolor("#0f0f16")

        ax.fill_between(x_cur, h_cur, alpha=0.15, color="#7F77DD")
        ax.plot(x_cur, h_cur, color="#7F77DD", linewidth=2.0, label="Your plan")
        ax.plot(x_rec, h_rec, color="#f9f09d", linewidth=1.4, linestyle="--", label="Recommended plan")
        ax.axvline(x=ya, color="#26215C", linewidth=1.2, linestyle=":")
        ax.text(ya+0.3, max(h_cur)*0.96, "Retirement", color="#3f3f46", fontsize=7)

        ax.set_xlabel("Years", color="#71717A", fontsize=8)
        ax.set_ylabel("Portfolio value (€)", color="#71717A", fontsize=8)
        ax.tick_params(colors="#3f3f46", labelsize=7)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"€{int(x/1000)}k" if x >= 1000 else f"€{int(x)}"))
        for spine in ax.spines.values():
            spine.set_edgecolor("#1f1f2e")
        ax.grid(axis="y", color="#1f1f2e", linewidth=0.5, alpha=0.8)
        ax.grid(axis="x", visible=False)

        legend = ax.legend(fontsize=7, facecolor="#141420", edgecolor="#1f1f2e", labelcolor="#A1A1AA", loc="upper left")

        plt.tight_layout(pad=0.4)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=180, facecolor="#0f0f16")
        plt.close()
        buf.seek(0)
        return buf

    chart_buf = make_chart()

    # ── CANVAS CALLBACKS ──
    def cover_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
        canvas.setFillColor(C_PURPLE)
        canvas.rect(0, 0, 0.35*cm, PH, fill=1, stroke=0)
        canvas.setFillColor(C_SURFACE)
        canvas.rect(0, PH-1.8*cm, PW, 1.8*cm, fill=1, stroke=0)
        # logo in header
        try:
            import os
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, ML+0.5*cm, PH-1.55*cm, width=0.9*cm, height=0.9*cm, preserveAspectRatio=True, mask='auto')
            canvas.setFillColor(C_WHITE)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(ML+1.6*cm, PH-1.1*cm, "THE FREEDOM PROJECT  (fi)")
        except:
            canvas.setFillColor(C_WHITE)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(ML+0.5*cm, PH-1.1*cm, "THE FREEDOM PROJECT  (fi)")
        canvas.setFillColor(C_SUBTLE)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PW-MR, PH-1.1*cm, datetime.now().strftime("%B %Y"))
        cx, cy, r = PW-MR-2.5*cm, PH*0.58, 2.0*cm
        canvas.setFillColor(C_SURFACE)
        canvas.circle(cx, cy, r, fill=1, stroke=0)
        canvas.setStrokeColor(C_SCORE)
        canvas.setLineWidth(4)
        canvas.circle(cx, cy, r, fill=0, stroke=1)
        canvas.setFillColor(C_SCORE)
        canvas.setFont("Helvetica-Bold", 28)
        canvas.drawCentredString(cx, cy-0.3*cm, str(int(score)))
        canvas.setFillColor(C_SUBTLE)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(cx, cy-0.9*cm, "OUT OF 100")
        canvas.setFillColor(C_SCORE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawCentredString(cx, cy+0.6*cm, score_txt.upper())
        canvas.setStrokeColor(C_PURPLE_D)
        canvas.setLineWidth(0.5)
        canvas.line(ML+0.5*cm, PH*0.35, PW-MR, PH*0.35)
        canvas.setFillColor(C_SUBTLE)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(ML+0.5*cm, MB*0.6, f"Prepared for {r_name}  ·  {r_email}  ·  {r_country}")
        canvas.drawRightString(PW-MR, MB*0.6, "For planning purposes only")
        canvas.restoreState()

    def inner_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
        canvas.setFillColor(C_PURPLE)
        canvas.rect(0, 0, 0.25*cm, PH, fill=1, stroke=0)
        # header
        canvas.setFillColor(C_SURFACE)
        canvas.rect(0, PH-1.2*cm, PW, 1.2*cm, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(ML+0.3*cm, PH-0.75*cm, "THE FREEDOM PROJECT  (fi)")
        canvas.setFillColor(C_SUBTLE)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(PW-MR, PH-0.75*cm, "Financial Independence Report")
        # footer
        canvas.setStrokeColor(C_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(ML+0.3*cm, MB+0.3*cm, PW-MR, MB+0.3*cm)
        canvas.setFillColor(C_SUBTLE)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(ML+0.3*cm, MB*0.5, f"{r_name}  ·  {r_country}  ·  {datetime.now().strftime('%B %d, %Y')}")
        canvas.drawRightString(PW-MR, MB*0.5, f"Page {doc.page}")
        canvas.restoreState()

    # ── DOCUMENT ──
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=ML+0.5*cm, rightMargin=MR,
        topMargin=2.2*cm, bottomMargin=1.8*cm
    )

    story = []

    # ════════════════════════════════
    # PAGE 1 — COVER
    # ════════════════════════════════
    story.append(Spacer(1, 3.5*cm))
    story.append(Paragraph("FINANCIAL INDEPENDENCE", ps("tag", fontName="Helvetica-Bold", fontSize=8, textColor=C_PURPLE, spaceAfter=6, letterSpacing=2)))
    story.append(Paragraph("Your Personal<br/>Report", sty_cover_h))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(f"Based on a <b>{profile}</b> investment profile over <b>{ya} years</b> of accumulation.", sty_cover_s))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Target retirement income: <b>€{mc_inc:,}/month</b>  ·  Freedom Number: <b>€{int(fn):,}</b>", sty_cover_s))
    story.append(PageBreak())

    # ════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY
    # ════════════════════════════════
    story.append(Paragraph("01 — Executive Summary", sty_h1))
    story.append(HRFlowable(width=W, color=C_PURPLE_D, thickness=0.5, spaceAfter=14))

    # Summary text
    gap_text = f"Your plan is on track. Your current monthly investment of €{mi:,} exceeds the minimum required." if gap == 0 else \
               f"Your current monthly investment of €{mi:,} falls €{gap:,} short of the recommended €{inv_needed:,}/month."
    fi_text  = f"At your current savings rate, you could reach financial independence at approximately age {fi_age}." if fi_age else \
               "Increasing your monthly investment would allow you to reach financial independence within your planning horizon."
    sust_text = f"Your portfolio sustains your desired income of €{mc_inc:,}/month for the full {yr}-year retirement period." if survives else \
                f"Your portfolio may be depleted before the end of your {yr}-year retirement. Consider increasing contributions."

    story.append(Paragraph(gap_text, sty_body))
    story.append(Paragraph(fi_text,  sty_body))
    story.append(Paragraph(sust_text, sty_body))
    story.append(Spacer(1, 0.5*cm))

    # 4-metric row — simple single-table approach
    metric_items = [
        ("READINESS SCORE",  f"{int(score)} / 100",                    score_hex),
        ("FREEDOM NUMBER",   f"€{int(fn):,}",                          "#7F77DD"),
        ("MONTHLY GAP",      "On track ✓" if gap==0 else f"+€{gap:,}", "#4ade80" if gap==0 else "#EF9F27"),
        ("FI AGE ESTIMATE",  f"Age {fi_age}" if fi_age else "—",       "#F2F2F2"),
    ]
    m_row = []
    for lbl, val, col in metric_items:
        m_row.append(Paragraph(
            f'<font size="6" color="#3f3f46">{lbl}</font><br/><br/>'
            f'<font size="15" color="{col}"><b>{val}</b></font>',
            ps(f"mc_{lbl}", fontName="Helvetica", fontSize=15, leading=20, spaceAfter=0)
        ))

    t_m = Table([m_row], colWidths=[W/4]*4)
    t_m.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_SURFACE),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('TOPPADDING',    (0,0), (-1,-1), 16),
        ('BOTTOMPADDING', (0,0), (-1,-1), 16),
        ('LINEAFTER',     (0,0), (2,0),   0.5, C_LINE),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 0.6*cm))

    # Full metrics table
    story.append(Paragraph("02 — Key Metrics", sty_h1))
    story.append(HRFlowable(width=W, color=C_PURPLE_D, thickness=0.5, spaceAfter=14))

    all_metrics = [
        ("Monthly investment",       f"€{mi:,}"),
        ("Recommended investment",   f"€{inv_needed:,}"),
        ("Target retirement capital",f"€{int(target_cap):,}"),
        ("Maximum capital reached",  f"€{int(max_cap):,}"),
        ("Freedom Number",           f"€{int(fn):,}"),
        ("Estimated FI age",         f"Age {fi_age}" if fi_age else "—"),
        ("Investment profile",       profile),
        ("Annual return assumed",    f"{int(ar*100)}% (nominal)"),
        ("Accumulation period",      f"{ya} years"),
        ("Retirement period",        f"{yr} years"),
        ("Retirement sustained",     "Yes" if survives else "No"),
        ("Projection type",          "Nominal (inflation not adjusted)"),
    ]

    rows = [all_metrics[i:i+2] for i in range(0, len(all_metrics), 2)]
    t_rows = []
    for i, row in enumerate(rows):
        while len(row) < 2: row.append(("",""))
        bg = C_SURFACE if i % 2 == 0 else C_SURFACE2
        t_rows.append([
            Paragraph(f'<font color="#3f3f46">{row[0][0]}</font>', ps("tr", fontName="Helvetica", fontSize=8.5, textColor=C_MUTED, leading=12)),
            Paragraph(f'<b>{row[0][1]}</b>', ps("tv", fontName="Helvetica-Bold", fontSize=8.5, textColor=C_WHITE, leading=12)),
            Paragraph(f'<font color="#3f3f46">{row[1][0]}</font>', ps("tr2", fontName="Helvetica", fontSize=8.5, textColor=C_MUTED, leading=12)),
            Paragraph(f'<b>{row[1][1]}</b>', ps("tv2", fontName="Helvetica-Bold", fontSize=8.5, textColor=C_WHITE, leading=12)),
        ])

    t_full = Table(t_rows, colWidths=[W*0.28, W*0.22, W*0.28, W*0.22])
    style_rows = [
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING',   (0,0), (-1,-1), 9),
        ('BOTTOMPADDING',(0,0), (-1,-1), 9),
        ('LINEAFTER',    (1,0), (1,-1),  0.5, C_LINE),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
    ]
    for i in range(len(t_rows)):
        bg = C_SURFACE if i % 2 == 0 else C_SURFACE2
        style_rows.append(('BACKGROUND', (0,i), (-1,i), bg))
    t_full.setStyle(TableStyle(style_rows))
    story.append(t_full)
    story.append(PageBreak())

    # ════════════════════════════════
    # PAGE 3 — PROJECTION CHART
    # ════════════════════════════════
    story.append(Paragraph("03 — Portfolio Projection", sty_h1))
    story.append(HRFlowable(width=W, color=C_PURPLE_D, thickness=0.5, spaceAfter=10))
    story.append(Paragraph(
        f"The chart below shows your portfolio trajectory over {ya+yr} years under your current plan (purple) "
        f"versus the recommended investment of €{inv_needed:,}/month (yellow dashed). "
        f"The dotted vertical line marks the start of retirement at year {ya}.",
        sty_body
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(RLImage(chart_buf, width=W, height=W*0.44))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(f"Assumed annual return: {int(ar*100)}%  ·  Profile: {profile}  ·  Nominal terms only", sty_caption))
    story.append(Spacer(1, 0.6*cm))

    # ════════════════════════════════
    # PAGE 3 continued — INSIGHTS
    # ════════════════════════════════
    story.append(Paragraph("04 — Personalised Insights", sty_h1))
    story.append(HRFlowable(width=W, color=C_PURPLE_D, thickness=0.5, spaceAfter=10))

    insights = []
    if gap > 0:
        insights.append(("Investment gap", f"Your current monthly investment of €{mi:,} is €{gap:,} below the recommended €{inv_needed:,}. "
            "Closing this gap is the single highest-impact action available to you. Even a partial increase improves long-term outcomes significantly."))
    else:
        insights.append(("On track", f"Your current monthly investment of €{mi:,} exceeds the minimum required to meet your retirement goal. "
            "You have a positive savings buffer that adds resilience to market downturns."))

    if fi_age:
        insights.append(("Financial independence", f"Based on your {profile.lower()} profile ({int(ar*100)}% annual return), "
            f"you could reach your Freedom Number of €{int(fn):,} at approximately age {fi_age}. "
            "This is the point at which your investments generate enough income to cover your expenses indefinitely."))

    insights.append(("Retirement sustainability", "Your plan sustains your desired retirement income for the full period." if survives else
        f"Your portfolio may be depleted before the end of your {yr}-year retirement. "
        "Consider increasing monthly contributions, reducing desired retirement income, or extending your accumulation period."))

    insights.append(("Inflation note", f"Projections are shown in nominal terms. A 2.5% annual inflation rate would reduce "
        f"the real purchasing power of your €{mc_inc:,}/month retirement income over time. "
        "Factor this into your planning by targeting a higher nominal income or investing in inflation-hedged assets."))

    insights.append(("Compounding effect", f"Of your projected maximum portfolio of €{int(max_cap):,}, "
        f"approximately {max(0, round((1 - (mi*12*ya)/max(max_cap,1))*100))}% is generated by investment returns rather than contributions. "
        "This illustrates the power of long-term compound growth."))

    for title_ins, text_ins in insights:
        t_ins = Table([[
            Paragraph(
                f'<font size="7" color="#7F77DD"><b>{title_ins.upper()}</b></font><br/><br/>'
                f'<font size="9" color="#71717A">{text_ins}</font>',
                ps(f"ins_{title_ins}", fontName="Helvetica", fontSize=9, leading=14, spaceAfter=0)
            )
        ]], colWidths=[W])
        t_ins.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), C_SURFACE),
            ('LEFTPADDING',   (0,0), (-1,-1), 16),
            ('RIGHTPADDING',  (0,0), (-1,-1), 16),
            ('TOPPADDING',    (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LINEBEFORE',    (0,0), (0,-1),  2, colors.HexColor("#5A54C4")),
        ]))
        story.append(t_ins)
        story.append(Spacer(1, 5))

    story.append(PageBreak())

    # ════════════════════════════════
    # PAGE 4 — DISCLAIMER
    # ════════════════════════════════
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("A Note on Methodology", sty_h1))
    story.append(HRFlowable(width=W, color=C_PURPLE_D, thickness=0.5, spaceAfter=14))
    story.append(Paragraph(
        "This report was built with one goal in mind: to give you a clear, honest picture of where you stand financially. "
        "The projections are based on mathematical models that assume consistent returns and contributions over time. "
        "Markets do not always behave consistently — but the underlying logic of compound growth and long-term investing does not change.",
        sty_body
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"All projections use nominal returns of {int(ar*100)}% annually ({profile} profile) and do not account for inflation, "
        "taxes or platform fees. Real outcomes will vary. This report is a planning tool, not a prediction. "
        "Use it as a starting point for your financial thinking — and revisit it as your situation evolves.",
        sty_body
    ))
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width=W, color=C_LINE, thickness=0.5, spaceAfter=14))
    story.append(Paragraph(
        "THE FREEDOM PROJECT  (fi)  ·  Captain Compound  ·  financial independence",
        ps("sig", fontName="Helvetica-Bold", fontSize=8, textColor=C_PURPLE, leading=12, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Report generated {datetime.now().strftime('%B %d, %Y')}  ·  {r_name}  ·  {r_country}",
        ps("sig2", fontName="Helvetica", fontSize=7, textColor=C_SUBTLE, leading=10, alignment=TA_CENTER)
    ))

    # ── BUILD ──
    def get_template(is_cover):
        return cover_page if is_cover else inner_page

    doc.build(
        story,
        onFirstPage=cover_page,
        onLaterPages=inner_page
    )
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

col_logo, col_text, col_right = st.columns([1, 8, 3])
with col_logo:
    try:
        st.image("freedom_symbol_purple_white.svg", width=44)
    except:
        st.markdown("<div style='width:44px'></div>", unsafe_allow_html=True)
with col_text:
    st.markdown("""
    <div style="padding-top:4px">
      <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:17px;letter-spacing:1px;color:#F2F2F2">THE FREEDOM PROJECT</span>
      <span style="color:#9490e8;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:17px"> (fi)</span>
      <div style="font-size:11px;color:#3f3f46;letter-spacing:.5px;margin-top:2px">Freedom Simulator</div>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    st.markdown("<div style='font-size:12px;color:#3f3f46;text-align:right;padding-top:10px'>financial independence</div>", unsafe_allow_html=True)

st.markdown("<div style='border-bottom:0.5px solid rgba(255,255,255,0.07);margin-bottom:32px;margin-top:12px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

for key, default in [
    ("step", 1), ("inputs", {}), ("results", None),
    ("show_pdf_gate", False), ("pdf_unlocked", False),
    ("pro_unlocked", False), ("pro_email", ""), ("pro_gate_open", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────
# STEP INDICATOR
# ─────────────────────────────────────────────

def step_indicator(current, total=3):
    steps = ["Your situation", "Your goal", "Investment profile"]
    cols = st.columns(total)
    for i, (col, s) in enumerate(zip(cols, steps)):
        n = i + 1
        if n < current:
            dot_bg, dot_color, text_color, dot_text = "rgba(127,119,221,0.2)", "#7F77DD", "#7F77DD", "✓"
        elif n == current:
            dot_bg, dot_color, text_color, dot_text = "rgba(127,119,221,0.15)", "#F2F2F2", "#F2F2F2", str(n)
        else:
            dot_bg, dot_color, text_color, dot_text = "transparent", "#3f3f46", "#3f3f46", str(n)
        with col:
            st.markdown(f"""
            <div style="text-align:center">
              <div style="width:30px;height:30px;border-radius:50%;background:{dot_bg};border:1px solid {dot_color};
                display:inline-flex;align-items:center;justify-content:center;font-size:12px;
                font-weight:600;color:{dot_color};margin-bottom:6px">{dot_text}</div>
              <div style="font-size:11px;color:{text_color};letter-spacing:.3px">{s}</div>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIMULATION FUNCTIONS
# ─────────────────────────────────────────────

def get_return(profile):
    return {"Conservative": 0.04, "Balanced": 0.06, "Aggressive": 0.08}[profile]

def simulate(monthly_inv, monthly_inc, years_acc, years_ret, ann_return):
    capital, history, mr = 0, [], ann_return / 12
    for _ in range(years_acc * 12):
        capital = capital * (1 + mr) + monthly_inv
        history.append(capital)
    survives = True
    for _ in range(years_ret * 12):
        capital = capital * (1 + mr) - monthly_inc
        history.append(capital)
        if capital <= 0:
            survives = False
            break
    return history, survives

def required_investment(monthly_inc, years_acc, years_ret, ann_return):
    invest = 50
    while invest < 20000:
        _, ok = simulate(invest, monthly_inc, years_acc, years_ret, ann_return)
        if ok: return invest
        invest += 25
    return invest

def freedom_number(monthly_exp, swr=0.04):
    return (monthly_exp * 12) / swr

def years_to_fi(monthly_inv, fn, ann_return):
    capital, mr = 0, ann_return / 12
    for m in range(1, 600):
        capital = capital * (1 + mr) + monthly_inv
        if capital >= fn: return m / 12
    return None

def monte_carlo(mi, mc, ya, yr, ar, n=1000):
    ok = sum(
        simulate(mi, mc, ya, yr, ar + np.random.normal(0, 0.015))[1]
        for _ in range(n)
    )
    return round(ok / n * 100, 1)

# ─────────────────────────────────────────────
# STEPS 1–3
# ─────────────────────────────────────────────

if st.session_state.step <= 3:
    step_indicator(st.session_state.step)
    st.markdown("<div style='margin-bottom:32px'></div>", unsafe_allow_html=True)

# ── STEP 1 ──
if st.session_state.step == 1:
    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px">Your current situation</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#71717A;font-size:15px;margin-bottom:32px">Tell us where you stand today.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(label("Current age"), unsafe_allow_html=True)
        current_age = st.number_input("Age", min_value=18, max_value=70, value=30, step=1, label_visibility="collapsed")
    with col2:
        st.markdown(label("Monthly investment (€)"), unsafe_allow_html=True)
        monthly_investment = st.number_input("Monthly investment", min_value=0, max_value=50000, value=300, step=50, label_visibility="collapsed")
    with col3:
        st.markdown(label("Years of accumulation"), unsafe_allow_html=True)
        years_accumulation = st.slider("Years acc", 5, 40, 25, label_visibility="collapsed")

    ret_age = current_age + years_accumulation
    st.markdown(f"""
    {card(f'''
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:13px;color:#52525B;margin-bottom:4px">Estimated retirement age</div>
          <div style="font-size:32px;font-weight:700;color:#7F77DD;font-family:'Space Grotesk',sans-serif">{ret_age}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:13px;color:#52525B;margin-bottom:4px">Monthly investment</div>
          <div style="font-size:24px;font-weight:700;color:#F2F2F2;font-family:'Space Grotesk',sans-serif">€{monthly_investment:,}</div>
        </div>
      </div>
    ''')}""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    col_btn = st.columns([2, 1, 2])
    with col_btn[1]:
        if st.button("Continue →"):
            st.session_state.inputs.update({"monthly_investment": monthly_investment, "years_accumulation": years_accumulation, "current_age": current_age})
            st.session_state.step = 2
            st.rerun()

# ── STEP 2 ──
elif st.session_state.step == 2:
    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px">Your retirement goal</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#71717A;font-size:15px;margin-bottom:32px">What kind of retirement do you want?</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(label("Desired monthly income (€)"), unsafe_allow_html=True)
        monthly_income = st.number_input("Monthly income", min_value=500, max_value=20000, value=1500, step=100, label_visibility="collapsed")
    with col2:
        st.markdown(label("Years in retirement"), unsafe_allow_html=True)
        years_retirement = st.slider("Years ret", 5, 40, 25, label_visibility="collapsed")

    fn = freedom_number(monthly_income)
    st.markdown(f"""
    {card(f'''
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
        <div>
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Your Freedom Number</div>
          <div style="font-size:40px;font-weight:700;color:#7F77DD;font-family:'Space Grotesk',sans-serif;line-height:1">€{int(fn):,}</div>
          <div style="font-size:12px;color:#52525B;margin-top:6px">Portfolio needed at 4% withdrawal rate</div>
        </div>
        <div>
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Monthly income generated</div>
          <div style="font-size:40px;font-weight:700;color:#F2F2F2;font-family:'Space Grotesk',sans-serif;line-height:1">€{monthly_income:,}</div>
          <div style="font-size:12px;color:#52525B;margin-top:6px">For {years_retirement} years of retirement</div>
        </div>
      </div>
    ''', border_color='rgba(90,84,196,0.25)')}""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            st.session_state.step = 1; st.rerun()
    with c2:
        if st.button("Continue →"):
            st.session_state.inputs.update({"monthly_income": monthly_income, "years_retirement": years_retirement, "freedom_number": fn})
            st.session_state.step = 3; st.rerun()

# ── STEP 3 ──
elif st.session_state.step == 3:
    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:6px">Your investment profile</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#71717A;font-size:15px;margin-bottom:32px">Choose how you want to invest.</div>', unsafe_allow_html=True)

    profile_data = {
        "Conservative": ("~4% annual return", "Low-cost bond and money market funds. Lower growth, lower volatility.", "#AFA9EC"),
        "Balanced":     ("~6% annual return", "Global equity index funds + bonds. The most recommended long-term allocation.", "#7F77DD"),
        "Aggressive":   ("~8% annual return", "100% global equity index funds. Higher long-term growth, higher volatility.", "#5A54C4"),
    }

    profile = st.selectbox("Investment profile", list(profile_data.keys()), index=1, label_visibility="collapsed")
    ret_label, ret_desc, pcolor = profile_data[profile]

    st.markdown(f"""
    {card(f'''
      <div style="display:flex;align-items:center;gap:16px">
        <div style="width:4px;height:60px;background:{pcolor};border-radius:2px;flex-shrink:0"></div>
        <div>
          <div style="font-size:17px;font-weight:600;color:#F2F2F2;margin-bottom:4px">{ret_label}</div>
          <div style="font-size:13px;color:#52525B;line-height:1.65">{ret_desc}</div>
        </div>
      </div>
    ''')}""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#0f0f16;border:0.5px solid rgba(255,255,255,0.05);border-left:2px solid #26215C;
         border-radius:0 8px 8px 0;padding:14px 18px;margin-top:4px">
      <div style="font-size:12px;color:#3f3f46;line-height:1.7">
        <span style="color:#52525B;font-weight:500">Free version note:</span>
        Projections use nominal returns and do not account for inflation.
        In real terms, purchasing power will be lower. The Pro version includes
        inflation-adjusted projections so you can plan with real euros, not just nominal figures.
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            st.session_state.step = 2; st.rerun()
    with c2:
        if st.button("Run simulation →"):
            st.session_state.inputs.update({"profile": profile, "ann_return": get_return(profile)})
            st.session_state.step = 4; st.rerun()

# ─────────────────────────────────────────────
# STEP 4 — RESULTS
# ─────────────────────────────────────────────

elif st.session_state.step == 4:

    inp = st.session_state.inputs
    mi, mc_inc = inp["monthly_investment"], inp["monthly_income"]
    ya, yr     = inp["years_accumulation"],  inp["years_retirement"]
    ar         = inp["ann_return"]
    fn         = inp["freedom_number"]
    age        = inp["current_age"]

    history, survives = simulate(mi, mc_inc, ya, yr, ar)
    inv_needed        = required_investment(mc_inc, ya, yr, ar)
    hist_rec, _       = simulate(inv_needed, mc_inc, ya, yr, ar)
    max_cap           = max(history) if history else 0
    target_cap        = mc_inc * 12 / ar
    score             = min(100, (max_cap / target_cap) * 100)
    ytf               = years_to_fi(mi, fn, ar)
    fi_age            = age + round(ytf) if ytf else None
    gap               = max(0, inv_needed - mi)

    score_color = "#7F77DD" if score >= 70 else "#EF9F27" if score >= 40 else "#E24B4A"
    score_text  = (
        "Strong trajectory." if score >= 80 else
        "Making progress — a few adjustments could help." if score >= 60 else
        "Your plan needs attention." if score >= 40 else
        "Significant gaps detected."
    )

    # ── HEADER ──
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:28px">
      <div>
        <div style="font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700;letter-spacing:-.5px">Your results</div>
        <div style="font-size:13px;color:#52525B;margin-top:4px">{inp['profile']} profile · {ya} years accumulation · {yr} years retirement</div>
      </div>
      <div style="font-size:12px;color:#3f3f46;cursor:pointer" onclick="">← Start over</div>
    </div>
    {divider('0 0 28px')}
    """, unsafe_allow_html=True)

    # ── SCORE + KEY METRICS ──
    col_score, col_fn, col_gap, col_fi = st.columns(4)

    with col_score:
        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid rgba(255,255,255,0.08);border-radius:14px;padding:24px;text-align:center">
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">Readiness score</div>
          <div style="font-size:60px;font-weight:700;color:{score_color};font-family:'Space Grotesk',sans-serif;line-height:1">{int(score)}</div>
          <div style="font-size:11px;color:#52525B;margin-top:6px">{score_text}</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(score / 100)

    with col_fn:
        st.metric("Freedom Number", f"€{int(fn):,}")
    with col_gap:
        if gap == 0:
            st.metric("Monthly gap", "On track ✓", delta="Sufficient savings")
        else:
            st.metric("Monthly gap", f"+€{gap:,}/mo", delta="Needs increase", delta_color="inverse")
    with col_fi:
        st.metric("Estimated FI age", f"Age {fi_age}" if fi_age else "Not reached")

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── CHART ──
    x1 = [i / 12 for i in range(len(history))]
    x2 = [i / 12 for i in range(len(hist_rec))]

    fig = go.Figure()
    fig.add_vrect(x0=0, x1=ya, fillcolor="rgba(127,119,221,0.03)", line_width=0, annotation_text="Accumulation", annotation_font_color="#3f3f46", annotation_position="top left")
    fig.add_vrect(x0=ya, x1=max(x1[-1], x2[-1]), fillcolor="rgba(255,255,255,0.01)", line_width=0, annotation_text="Retirement", annotation_font_color="#3f3f46", annotation_position="top left")
    fig.add_trace(go.Scatter(x=x1, y=history,  mode="lines", name="Your plan",        line=dict(color="#7F77DD", width=2.5)))
    fig.add_trace(go.Scatter(x=x2, y=hist_rec, mode="lines", name="Recommended plan", line=dict(color="#f9f09d", width=1.5, dash="dot")))
    fig.add_vline(x=ya, line_color="rgba(255,255,255,0.12)", line_dash="dash")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0B0B0F", plot_bgcolor="#0f0f16",
        height=380, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#A1A1AA", size=12), orientation="h", y=-0.12),
        xaxis=dict(title="Years", color="#3f3f46", gridcolor="rgba(255,255,255,0.04)", zeroline=False),
        yaxis=dict(title="Portfolio (€)", color="#3f3f46", gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickprefix="€")
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div style="font-size:11px;color:#3f3f46;line-height:1.7;margin-top:-8px;margin-bottom:8px">
      Projections are shown in nominal terms and do not adjust for inflation.
      Assumed annual return: {int(ar*100)}% ({inp['profile']} profile) · Monte Carlo and inflation-adjusted projections available in Pro.
    </div>
    """, unsafe_allow_html=True)

    # ── INSIGHTS ──
    st.markdown(divider(), unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:20px;font-weight:700;margin-bottom:20px">What this means for you</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid {'rgba(127,119,221,0.3)' if gap==0 else 'rgba(239,159,39,0.3)'};border-radius:12px;padding:20px 18px">
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Monthly investment</div>
          <div style="font-size:22px;font-weight:700;font-family:'Space Grotesk',sans-serif;color:{'#7F77DD' if gap==0 else '#EF9F27'};margin-bottom:6px">
            {'On track ✓' if gap==0 else f'+€{gap:,}/month needed'}
          </div>
          <div style="font-size:12px;color:#52525B;line-height:1.6">
            {'Your savings rate is sufficient for your retirement goal.' if gap==0 else f'Increasing by €{gap:,}/month would close the gap completely.'}
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        dur_text = f"Sustained for full {yr} years" if survives else f"Runs out after ~{(len(history)/12 - ya):.1f} years"
        dur_color = "#7F77DD" if survives else "#E24B4A"
        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid {'rgba(127,119,221,0.3)' if survives else 'rgba(226,75,74,0.3)'};border-radius:12px;padding:20px 18px">
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Retirement sustainability</div>
          <div style="font-size:22px;font-weight:700;font-family:'Space Grotesk',sans-serif;color:{dur_color};margin-bottom:6px">{dur_text}</div>
          <div style="font-size:12px;color:#52525B;line-height:1.6">
            {'Your portfolio sustains €' + f'{mc_inc:,}/month for your full retirement.' if survives else 'Consider increasing contributions or reducing desired income.'}
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid rgba(127,119,221,0.2);border-radius:12px;padding:20px 18px">
          <div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Financial independence</div>
          <div style="font-size:22px;font-weight:700;font-family:'Space Grotesk',sans-serif;color:#7F77DD;margin-bottom:6px">
            {'Age ' + str(fi_age) if fi_age else 'Not reached'}
          </div>
          <div style="font-size:12px;color:#52525B;line-height:1.6">
            {'At your current savings rate, you could stop depending on a salary at age ' + str(fi_age) + '.' if fi_age else 'Increase your monthly investment to reach FI within your lifetime.'}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── PDF GATE ──
    st.markdown(divider("40px 0"), unsafe_allow_html=True)

    if not st.session_state.pdf_unlocked:

        st.markdown(f"""
        <div style="font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;margin-bottom:6px">Your personalised report</div>
        <div style="font-size:14px;color:#71717A;margin-bottom:28px">A full PDF with your projections, score, metrics and insights. Free to download.</div>
        """, unsafe_allow_html=True)

        # ── REPORT PREVIEW (blurred) ──
        st.markdown(f"""
        <div style="position:relative;border-radius:14px;overflow:hidden;margin-bottom:28px">

          <!-- blurred overlay -->
          <div style="position:absolute;inset:0;background:linear-gradient(to bottom, rgba(11,11,15,0.1) 0%, rgba(11,11,15,0.85) 60%, rgba(11,11,15,0.97) 100%);
               backdrop-filter:blur(2px);z-index:2;border-radius:14px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:32px">
            <div style="text-align:center">
              <div style="display:inline-block;background:rgba(90,84,196,0.15);border:0.5px solid rgba(90,84,196,0.4);border-radius:20px;
                color:#9490e8;font-size:11px;letter-spacing:.8px;text-transform:uppercase;padding:5px 14px;margin-bottom:10px">Free report</div>
              <div style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:600;color:#F2F2F2;margin-bottom:4px">Register to unlock your report</div>
              <div style="font-size:12px;color:#52525B">Takes 10 seconds. No payment required.</div>
            </div>
          </div>

          <!-- preview content -->
          <div style="background:#0f0f16;border:0.5px solid rgba(255,255,255,0.07);border-radius:14px;padding:32px;filter:blur(1px)">
            <div style="font-size:10px;color:#3f3f46;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:4px">THE FREEDOM PROJECT (fi)</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;color:#F2F2F2;margin-bottom:20px">Financial Independence Report</div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">
              <div style="background:#141420;border-radius:8px;padding:14px">
                <div style="font-size:10px;color:#3f3f46;margin-bottom:6px">Readiness score</div>
                <div style="font-size:28px;font-weight:700;color:{score_color};font-family:'Space Grotesk',sans-serif">{int(score)}</div>
              </div>
              <div style="background:#141420;border-radius:8px;padding:14px">
                <div style="font-size:10px;color:#3f3f46;margin-bottom:6px">Freedom Number</div>
                <div style="font-size:18px;font-weight:700;color:#F2F2F2;font-family:'Space Grotesk',sans-serif">€{int(fn):,}</div>
              </div>
              <div style="background:#141420;border-radius:8px;padding:14px">
                <div style="font-size:10px;color:#3f3f46;margin-bottom:6px">Monthly gap</div>
                <div style="font-size:18px;font-weight:700;color:#F2F2F2;font-family:'Space Grotesk',sans-serif">{'✓' if gap==0 else f'+€{gap:,}'}</div>
              </div>
              <div style="background:#141420;border-radius:8px;padding:14px">
                <div style="font-size:10px;color:#3f3f46;margin-bottom:6px">FI age</div>
                <div style="font-size:18px;font-weight:700;color:#F2F2F2;font-family:'Space Grotesk',sans-serif">{fi_age if fi_age else '—'}</div>
              </div>
            </div>
            <div style="height:48px;background:#141420;border-radius:8px;margin-bottom:10px"></div>
            <div style="height:32px;background:#141420;border-radius:8px;width:70%"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── REGISTRATION FORM ──
        st.markdown(f"""
        <div style="background:rgba(90,84,196,0.06);border:0.5px solid rgba(90,84,196,0.2);border-radius:14px;padding:28px 32px">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">Get your free report</div>
          <div style="font-size:13px;color:#52525B;margin-bottom:24px">Enter your details to download your personalised financial independence report.</div>
        """, unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown('<div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Full name</div>', unsafe_allow_html=True)
            name = st.text_input("name", placeholder="Arturo Maldonado", label_visibility="collapsed")
        with fc2:
            st.markdown('<div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Email address</div>', unsafe_allow_html=True)
            email = st.text_input("email", placeholder="you@example.com", label_visibility="collapsed")
        with fc3:
            st.markdown('<div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Country</div>', unsafe_allow_html=True)
            country = st.selectbox("country", [
                "Germany", "Netherlands", "Switzerland", "Austria", "Belgium",
                "Sweden", "Denmark", "Norway", "Finland", "Luxembourg",
                "Spain", "Portugal", "France", "Italy", "United Kingdom",
                "Ireland", "Poland", "Czech Republic", "Estonia", "Latvia",
                "United States", "Canada", "Australia", "New Zealand",
                "Mexico", "Colombia", "Argentina", "Chile", "Peru",
                "Brazil", "Costa Rica", "Uruguay",
                "Singapore", "Hong Kong", "Japan", "South Korea",
                "United Arab Emirates", "South Africa", "Israel",
                "Other"
            ], label_visibility="collapsed")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

        col_dl = st.columns([2, 1, 2])
        with col_dl[1]:
            if st.button("Download my report →"):
                email_valid = re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email)
                if not name.strip():
                    st.error("Please enter your name.")
                elif not email.strip() or not email_valid:
                    st.error("Please enter a valid email address.")
                else:
                    st.session_state.inputs.update({"name": name, "email": email, "country": country})
                    print(f"DEBUG free_leads: email={email} country={country} score={score} fn={fn} profile={inp.get('profile','')}")
                    save_lead("free_leads", {
                        "Email":          email,
                        "Country":        country,
                        "Score":          round(score, 1),
                        "Freedom Number": int(fn),
                        "Profile":        inp.get("profile", ""),
                    })
                    print(f"DEBUG save_lead called")
                    st.session_state.pdf_unlocked = True
                    st.rerun()

    else:
        # ── PDF READY ──
        inp2 = st.session_state.inputs
        first_name = inp2.get("name", "").split()[0] if inp2.get("name") else "there"

        st.markdown(f"""
        <div style="background:rgba(90,84,196,0.07);border:0.5px solid rgba(90,84,196,0.25);border-radius:14px;padding:28px 32px;
             display:flex;align-items:center;gap:24px;margin-bottom:20px">
          <div style="width:48px;height:48px;border-radius:50%;background:rgba(90,84,196,0.2);border:1px solid rgba(90,84,196,0.4);
               display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">✓</div>
          <div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">
              Your report is ready, {first_name}.
            </div>
            <div style="font-size:13px;color:#52525B">
              Your personalised Financial Independence Report is ready to download.
              Prepared for {inp2.get('email','')} · {inp2.get('country','')}.
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        pdf = generate_pdf(inp2, score, inv_needed, max_cap, target_cap, fn, fi_age, survives, gap)
        col_dl2 = st.columns([2, 1, 2])
        with col_dl2[1]:
            st.download_button(
                label="⬇ Download PDF report",
                data=pdf,
                file_name=f"freedom_project_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    # ── PRO SECTION ──
    st.markdown(divider("32px 0"), unsafe_allow_html=True)

    pro = st.session_state.pro_unlocked

    if not pro:
        # ── PRO GATE ──
        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid rgba(90,84,196,0.25);border-radius:14px;overflow:hidden">

          <!-- header -->
          <div style="background:rgba(90,84,196,0.1);padding:24px 28px;border-bottom:0.5px solid rgba(90,84,196,0.2)">
            <div style="display:inline-block;background:rgba(90,84,196,0.2);border:0.5px solid rgba(90,84,196,0.4);
                 border-radius:20px;color:#9490e8;font-size:10px;letter-spacing:.8px;text-transform:uppercase;
                 padding:4px 12px;margin-bottom:12px">Pro access</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;margin-bottom:6px">
              Go deeper with your analysis
            </div>
            <div style="font-size:14px;color:#71717A;line-height:1.7;max-width:520px">
              The Pro version gives you a more complete picture of your financial future,
              including probabilistic analysis, real returns and a detailed branded report.
            </div>
          </div>

          <!-- features grid -->
          <div style="padding:24px 28px">
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px">
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">📊</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">Monte Carlo</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">1,000 simulations. Know the real probability your plan survives.</div>
              </div>
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">📉</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">Inflation-adjusted</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">See your projections in real euros, not just nominal figures.</div>
              </div>
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">🔀</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">Scenario comparison</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">Conservative vs balanced vs aggressive — side by side.</div>
              </div>
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">📄</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">Full PDF report</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">4-page branded report with chart, metrics and personalised insights.</div>
              </div>
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">📅</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">FI date estimate</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">The exact age at which your investments work harder than you do.</div>
              </div>
              <div style="background:#141420;border:0.5px solid rgba(255,255,255,0.06);border-radius:9px;padding:16px">
                <div style="font-size:16px;margin-bottom:8px">🔜</div>
                <div style="font-size:13px;font-weight:600;color:#F2F2F2;margin-bottom:4px">More tools coming</div>
                <div style="font-size:12px;color:#52525B;line-height:1.5">Retirement Planner and Portfolio Allocator. Pro members get early access.</div>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:rgba(90,84,196,0.07);border:0.5px solid rgba(90,84,196,0.2);border-radius:9px;
             padding:14px 18px;margin-bottom:20px;font-size:12px;color:#71717A;line-height:1.6">
          <span style="color:#9490e8;font-weight:500">Early access:</span>
          Pro is currently free while we build the full platform. Enter your email to unlock it now.
          You will be notified when Pro becomes a paid feature, with a discount for early members.
        </div>
        """, unsafe_allow_html=True)

        # Pro gate form
        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        col_pe1, col_pe2, col_pe3 = st.columns([2, 2, 1])
        with col_pe1:
            st.markdown('<div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Email address</div>', unsafe_allow_html=True)
            pro_email = st.text_input("pro_email", placeholder="you@example.com", label_visibility="collapsed")
        with col_pe2:
            st.markdown('<div style="font-size:11px;color:#3f3f46;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Full name</div>', unsafe_allow_html=True)
            pro_name = st.text_input("pro_name", placeholder="Arturo Maldonado", label_visibility="collapsed")
        with col_pe3:
            st.markdown('<div style="font-size:11px;color:#3f3f46;margin-bottom:6px">&nbsp;</div>', unsafe_allow_html=True)
            if st.button("Unlock Pro →"):
                pro_email_valid = re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', pro_email or "")
                if not pro_name.strip():
                    st.error("Please enter your name.")
                elif not pro_email_valid:
                    st.error("Please enter a valid email address.")
                else:
                    save_lead("pro_leads", {
                        "Name":  pro_name,
                        "Email": pro_email,
                    })
                    st.session_state.pro_unlocked = True
                    st.session_state.pro_email = pro_email
                    st.session_state.inputs.update({"pro_name": pro_name, "pro_email": pro_email})
                    st.rerun()

    else:
        # ── PRO FEATURES UNLOCKED ──
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px">
          <div style="display:inline-block;background:rgba(90,84,196,0.15);border:0.5px solid rgba(90,84,196,0.35);
               border-radius:20px;color:#9490e8;font-size:10px;letter-spacing:.8px;text-transform:uppercase;padding:4px 12px">
            Pro access unlocked
          </div>
          <div style="font-size:12px;color:#3f3f46">{st.session_state.pro_email}</div>
        </div>
        """, unsafe_allow_html=True)

        # Monte Carlo
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">📊 Monte Carlo simulation</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#71717A;margin-bottom:14px'>1,000 simulations with randomised annual returns to estimate the real probability of your plan succeeding.</div>", unsafe_allow_html=True)

        with st.spinner("Running 1,000 simulations..."):
            mc_prob = monte_carlo(mi, mc_inc, ya, yr, ar)
        mc_color = "#7F77DD" if mc_prob >= 70 else "#EF9F27" if mc_prob >= 50 else "#E24B4A"
        mc_label = "Strong probability of success." if mc_prob >= 70 else "Moderate. Consider increasing contributions." if mc_prob >= 50 else "Low. Plan adjustments recommended."

        st.markdown(f"""
        <div style="background:#0f0f16;border:0.5px solid rgba(255,255,255,0.08);border-radius:12px;
             padding:24px 28px;display:flex;align-items:center;gap:24px;margin-bottom:28px">
          <div style="font-size:56px;font-weight:700;color:{mc_color};font-family:'Space Grotesk',sans-serif;line-height:1;flex-shrink:0">{mc_prob}%</div>
          <div>
            <div style="font-size:15px;font-weight:500;color:#F2F2F2;margin-bottom:4px">Probability of success</div>
            <div style="font-size:13px;color:#52525B;margin-bottom:6px">Your plan survives all {yr} years of retirement in {mc_prob}% of simulated market scenarios.</div>
            <div style="font-size:12px;color:{mc_color}">{mc_label}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(divider("0 0 20px"), unsafe_allow_html=True)

        # Inflation-adjusted
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">📉 Inflation-adjusted projection</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#71717A;margin-bottom:14px'>See what your portfolio looks like in real euros after accounting for inflation.</div>", unsafe_allow_html=True)

        inflation = st.slider("Annual inflation rate", 1.0, 5.0, 2.5, 0.5, format="%.1f%%")
        real_return = max(ar - inflation / 100, 0.01)
        hist_real, _ = simulate(mi, mc_inc, ya, yr, real_return)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x1, y=history, mode="lines", name="Nominal", line=dict(color="#7F77DD", width=2)))
        fig2.add_trace(go.Scatter(x=[i/12 for i in range(len(hist_real))], y=hist_real, mode="lines",
                                  name=f"Real ({inflation}% inflation)", line=dict(color="#f9f09d", width=2, dash="dot")))
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#0B0B0F", plot_bgcolor="#0f0f16",
                           height=300, margin=dict(l=0,r=0,t=10,b=0),
                           legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#A1A1AA")),
                           xaxis=dict(color="#3f3f46", gridcolor="rgba(255,255,255,0.04)"),
                           yaxis=dict(color="#3f3f46", gridcolor="rgba(255,255,255,0.04)", tickprefix="€"))
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown(divider("0 0 20px"), unsafe_allow_html=True)

        # Scenario comparison
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">🔀 Scenario comparison</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#71717A;margin-bottom:14px'>Conservative, balanced and aggressive profiles — your plan across all three.</div>", unsafe_allow_html=True)

        fig3 = go.Figure()
        for p, r, c in [("Conservative", 0.04, "#AFA9EC"), ("Balanced", 0.06, "#7F77DD"), ("Aggressive", 0.08, "#26215C")]:
            h, _ = simulate(mi, mc_inc, ya, yr, r)
            fig3.add_trace(go.Scatter(x=[i/12 for i in range(len(h))], y=h, mode="lines",
                                      name=f"{p} ({int(r*100)}%)", line=dict(color=c, width=2)))
        fig3.update_layout(template="plotly_dark", paper_bgcolor="#0B0B0F", plot_bgcolor="#0f0f16",
                           height=300, margin=dict(l=0,r=0,t=10,b=0),
                           legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#A1A1AA")),
                           xaxis=dict(color="#3f3f46", gridcolor="rgba(255,255,255,0.04)"),
                           yaxis=dict(color="#3f3f46", gridcolor="rgba(255,255,255,0.04)", tickprefix="€"))
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown(divider("0 0 20px"), unsafe_allow_html=True)

        # Pro PDF
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif;font-size:18px;font-weight:700;margin-bottom:4px">📄 Full Pro report</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#71717A;margin-bottom:20px'>4-page branded PDF with chart, metrics, Monte Carlo result and personalised insights.</div>", unsafe_allow_html=True)

        pro_inp = {**inp,
                   "name":    st.session_state.inputs.get("pro_name", st.session_state.pro_email),
                   "email":   st.session_state.pro_email,
                   "country": inp.get("country", "—")}
        pro_pdf = generate_pdf(pro_inp, score, inv_needed, max_cap, target_cap, fn, fi_age, survives, gap)

        col_pro_dl = st.columns([2, 1, 2])
        with col_pro_dl[1]:
            st.download_button(
                label="⬇ Download Pro report",
                data=pro_pdf,
                file_name=f"freedom_project_pro_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    # ── RESTART ──
    st.markdown(divider("32px 0"), unsafe_allow_html=True)
    col_r = st.columns([2, 1, 2])
    with col_r[1]:
        if st.button("← Start over"):
            for k in ["step", "inputs", "results", "show_pdf_gate", "pdf_unlocked", "pro_unlocked", "pro_email", "pro_gate_open"]:
                st.session_state[k] = 1 if k == "step" else ({} if k == "inputs" else ("" if k == "pro_email" else (False if k != "results" else None)))
            st.rerun()
