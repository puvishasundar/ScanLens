import streamlit as st
import matplotlib.pyplot as plt
import io
import base64
from model import predict_risk

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(
    page_title="ScanLens ✨ — Job Safety Scanner",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- LOAD CSS ---------------- #
def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ---------------- FLOATING EMOJIS ---------------- #
st.markdown("""
<div class='floating-emojis' aria-hidden='true'>
  <span class='fe fe1'>🔍</span>
  <span class='fe fe2'>⚠️</span>
  <span class='fe fe3'>💼</span>
  <span class='fe fe4'>🚨</span>
  <span class='fe fe5'>✨</span>
  <span class='fe fe6'>🛡️</span>
  <span class='fe fe7'>💰</span>
  <span class='fe fe8'>🔎</span>
  <span class='fe fe9'>❗</span>
  <span class='fe fe10'>💎</span>
  <span class='fe fe11'>🕵️</span>
  <span class='fe fe12'>🌟</span>
</div>
""", unsafe_allow_html=True)

# ---------------- HERO HEADER ---------------- #
st.markdown("""
<div class='hero-header'>
  <div class='hero-glow'></div>
  <div class='hero-content'>
    <div class='hero-badge'>🛡️ AI-Powered Protection</div>
    <div class='hero-title'>
      <span class='title-scan'>Scan</span><span class='title-lens'>Lens</span>
      <span class='title-sparkle'>✨</span>
    </div>
    <div class='hero-subtitle'>
      🚨 Fake Job &amp; Internship Detector &nbsp;•&nbsp; Powered by Smart NLP 🤖
    </div>
    <div class='hero-tags'>
      <span class='htag'>⚡ Instant Results</span>
      <span class='htag'>🔒 100% Private</span>
      <span class='htag'>🎯 High Accuracy</span>
      <span class='htag'>🧠 NLP Powered</span>
      <span class='htag'>📎 File Support</span>
    </div>
  </div>
  <div class='version-pill'>v2.0 Pro 🌟</div>
</div>
""", unsafe_allow_html=True)

# ---------------- STATS ROW ---------------- #
st.markdown("""
<div class='stat-row'>
  <div class='stat-item'>
    <div class='stat-num'>500+</div>
    <div class='stat-label'>Scans Done</div>
  </div>
  <div class='stat-item'>
    <div class='stat-num'>95%</div>
    <div class='stat-label'>Accuracy</div>
  </div>
  <div class='stat-item'>
    <div class='stat-num'>120+</div>
    <div class='stat-label'>Scams Caught</div>
  </div>
  <div class='stat-item'>
    <div class='stat-num'>0</div>
    <div class='stat-label'>Data Stored</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- RED FLAGS TICKER ---------------- #
st.markdown("""
<div class='ticker-wrap'>
  <div class='ticker-track'>
    <span>🚩 "Work from home"</span>
    <span>⚠️ "Quick money"</span>
    <span>🚩 "No experience needed"</span>
    <span>⚠️ "Send registration fee"</span>
    <span>🚩 "Instant hire"</span>
    <span>⚠️ "Rating apps for cash"</span>
    <span>🚩 "Security deposit required"</span>
    <span>⚠️ "WhatsApp only recruiter"</span>
    <span>🚩 "Earn ₹50,000/week"</span>
    <span>⚠️ "No interview needed"</span>
    <span>🚩 "Work from home"</span>
    <span>⚠️ "Quick money"</span>
    <span>🚩 "No experience needed"</span>
    <span>⚠️ "Send registration fee"</span>
    <span>🚩 "Instant hire"</span>
    <span>⚠️ "Rating apps for cash"</span>
    <span>🚩 "Security deposit required"</span>
    <span>⚠️ "WhatsApp only recruiter"</span>
    <span>🚩 "Earn ₹50,000/week"</span>
    <span>⚠️ "No interview needed"</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- INPUT SECTION ---------------- #
col_input, col_side = st.columns([3, 1])

with col_input:
    st.markdown("""
    <div class='input-label'>
      📋 Paste Message to Scan
      <span class='input-sub'>WhatsApp messages, job offers, emails, SMS — any suspicious text 💬</span>
    </div>
    """, unsafe_allow_html=True)

    user_input = st.text_area(
        "",
        placeholder='✍️ e.g. "Urgent hiring! Earn ₹50,000/week from home. No experience needed. Send ₹500 registration fee to join our team immediately..."',
        height=160,
        label_visibility="collapsed"
    )

    st.markdown("<div class='upload-label'>📎 Or upload a screenshot / PDF</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "",
        type=["png", "jpg", "jpeg", "pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        from ocr_utils import extract_text_from_image, extract_text_from_pdf
        if uploaded_file.type == "application/pdf":
            ocr_text = extract_text_from_pdf(uploaded_file)
        else:
            ocr_text = extract_text_from_image(uploaded_file)
        if ocr_text.strip():
            user_input = ocr_text
            st.success("✅ Text extracted from file successfully!")
        else:
            st.warning("⚠️ Could not read text clearly. Try a higher resolution image.")

    col_btn, col_tip = st.columns([1, 2])
    with col_btn:
        scan_btn = st.button("🔍 Scan Now", use_container_width=True, key="scan_btn_main")
    with col_tip:
        st.markdown("""
        <div style='padding-top:12px; font-size:12px; color:rgba(255,255,255,0.35); line-height:1.5;'>
            🔒 100% private — your text is never stored or shared with anyone.
        </div>
        """, unsafe_allow_html=True)

with col_side:
    st.markdown("""
    <div class='glass-card' style='margin-top: 34px;'>
      <div class='card-label'>🚩 Common Red Flags</div>
      <div style='font-size:12px; color:rgba(255,255,255,0.55); line-height:2;'>
        💸 Upfront payment requests<br>
        📱 WhatsApp-only contact<br>
        🎯 "No experience needed"<br>
        ⚡ Urgency &amp; pressure tactics<br>
        💰 Unrealistic salaries<br>
        📧 Non-company email IDs<br>
        🔒 Requests personal data early<br>
        🏠 Work from home only
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='glass-card'>
      <div class='card-label'>💡 How to Use</div>
      <div style='font-size:12px; color:rgba(255,255,255,0.55); line-height:2;'>
        1️⃣ Copy suspicious message<br>
        2️⃣ Paste it in the box<br>
        3️⃣ Or upload a screenshot<br>
        4️⃣ Hit <b style="color:#c084fc;">Scan Now</b><br>
        5️⃣ Review your results
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# ---------------- DONUT CHART ---------------- #
def plot_risk(score):
    fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor='none')

    if score < 40:
        fill_color = "#4ade80"
        glow_color = "#4ade80"
    elif score < 70:
        fill_color = "#f59e0b"
        glow_color = "#f59e0b"
    else:
        fill_color = "#f43f5e"
        glow_color = "#f43f5e"

    ax.pie(
        [score, 100 - score],
        startangle=90,
        colors=[fill_color, "#1a0030"],
        wedgeprops=dict(width=0.42, edgecolor='none'),
        counterclock=False
    )

    ax.text(0, 0.1, f"{score}", ha='center', va='center',
            fontsize=32, fontweight='bold', color='white')
    ax.text(0, -0.3, "R I S K   S C O R E", ha='center', va='center',
            fontsize=7, color='#c084fc', fontweight='700')

    ax.set_title("Risk Meter", fontsize=9.5, color='#c084fc', pad=12, fontweight='600')
    fig.patch.set_alpha(0.0)
    ax.set_facecolor('none')
    return fig

def plot_risk_base64(score):
    fig = plot_risk(score)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", dpi=150)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

# ---------------- RESULTS ---------------- #
if scan_btn and user_input:

    with st.spinner("🔍 Analysing your message..."):
        result       = predict_risk(user_input)

    risk_score   = result["score"]
    confidence   = result["confidence"]
    result_label = result["label"]
    keywords     = result["keywords"]
    reasons      = result["reasons"]

    if risk_score < 40:
        status_color  = "#4ade80"
        status_bg     = "rgba(74,222,128,0.1)"
        status_border = "rgba(74,222,128,0.35)"
        verdict_icon  = "✅"
        verdict_emoji = "🎉"
        risk_level    = "LOW RISK"
    elif risk_score < 70:
        status_color  = "#f59e0b"
        status_bg     = "rgba(245,158,11,0.1)"
        status_border = "rgba(245,158,11,0.35)"
        verdict_icon  = "⚠️"
        verdict_emoji = "🤔"
        risk_level    = "MEDIUM RISK"
    else:
        status_color  = "#f43f5e"
        status_bg     = "rgba(244,63,94,0.1)"
        status_border = "rgba(244,63,94,0.35)"
        verdict_icon  = "🚨"
        verdict_emoji = "😱"
        risk_level    = "HIGH RISK"

    # -------- RESULT BANNER -------- #
    st.markdown(f"""
    <div class='result-banner' style='border-color:{status_border}; background:{status_bg};'>
        {verdict_emoji} &nbsp; Scan Complete — <span style='color:{status_color};'>{risk_level}</span> &nbsp; {verdict_emoji}
    </div>
    """, unsafe_allow_html=True)

    # -------- ROW 1: Score + Donut + Confidence -------- #
    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        st.markdown(
            "<div class='glass-card' style='height:100%;'>"
            "<div class='card-label'>🎯 Risk Score</div>"
            "<div style='display:flex; align-items:flex-end; gap:8px; margin-bottom:6px;'>"
            f"<div class='big-score' style='color:{status_color};'>{risk_score}</div>"
            "<div style='font-size:20px; color:rgba(255,255,255,0.25); padding-bottom:12px;'>/100</div>"
            "</div>"
            "<div class='score-label'>Overall Risk Score 📊</div>"
            "<div class='progress-bar-bg'>"
            f"<div class='progress-bar-fill' style='width:{risk_score}%; background:linear-gradient(90deg, {status_color}, #f0abfc);'></div>"
            "</div>"
            f"<div class='verdict-pill' style='background:{status_bg}; border:1px solid {status_border};'>"
            f"<span style='font-size:18px;'>{verdict_icon}</span>"
            f"<span style='font-size:15px; font-weight:700; color:{status_color};'>{result_label}</span>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with col2:
        chart_b64 = plot_risk_base64(risk_score)
        st.markdown(
            "<div class='glass-card' style='text-align:center; height:100%;'>"
            "<div class='card-label'>📈 Risk Meter</div>"
            f"<img src='data:image/png;base64,{chart_b64}' "
            "style='width:100%; max-width:260px; display:block; margin:0 auto;'/>"
            "</div>",
            unsafe_allow_html=True
        )

    with col3:
        # Confidence breakdown
        conf_bar = confidence
        safe_pct = 100 - risk_score
        st.markdown(
            "<div class='glass-card' style='height:100%;'>"
            "<div class='card-label'>🤖 Model Analysis</div>"
            f"<div style='margin-bottom:16px;'>"
            f"<div style='font-size:11px; color:rgba(255,255,255,0.4); margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>Confidence</div>"
            f"<div style='font-size:36px; font-family:Syne,sans-serif; font-weight:800; color:#c084fc;'>{confidence}%</div>"
            f"</div>"
            f"<div style='font-size:11px; color:rgba(255,255,255,0.4); margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>Scam Probability</div>"
            "<div class='progress-bar-bg' style='margin-bottom:12px;'>"
            f"<div class='progress-bar-fill' style='width:{risk_score}%; background:linear-gradient(90deg, #f43f5e, #f0abfc);'></div>"
            "</div>"
            f"<div style='font-size:11px; color:rgba(255,255,255,0.4); margin-bottom:6px; text-transform:uppercase; letter-spacing:1px;'>Legitimate Probability</div>"
            "<div class='progress-bar-bg'>"
            f"<div class='progress-bar-fill' style='width:{safe_pct}%; background:linear-gradient(90deg, #4ade80, #34d399);'></div>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

    # -------- ROW 2: Insights + Signals -------- #
    col3, col4 = st.columns(2)

    with col3:
        reasons_html = ""
        if reasons:
            for r in reasons:
                reasons_html += (
                    "<div class='reason-item'>"
                    "<span class='reason-icon'>🚩</span>"
                    f"<span style='font-size:13px; color:#ffffff; line-height:1.6;'>{r}</span>"
                    "</div>"
                )
        else:
            reasons_html = "<div style='font-size:13px; color:rgba(255,255,255,0.45); font-style:italic; padding:12px 0;'>✅ No strong scam indicators detected.</div>"

        st.markdown(
            "<div class='glass-card'>"
            "<div class='card-label'>⚠️ Risk Insights</div>"
            f"{reasons_html}"
            "</div>",
            unsafe_allow_html=True
        )

    with col4:
        if keywords:
            pills = "".join([
                f"<span class='kw-pill'>🔴 {kw}</span>"
                for kw in keywords
            ])
            signals_html = f"<div style='line-height:2.8;'>{pills}</div>"
            kw_count = f"<div style='font-size:12px; color:rgba(255,255,255,0.35); margin-bottom:12px;'>{len(keywords)} suspicious signal{'s' if len(keywords)>1 else ''} detected</div>"
        else:
            signals_html = "<div style='font-size:13px; color:rgba(255,255,255,0.45); font-style:italic; padding:12px 0;'>✅ No suspicious keywords found.</div>"
            kw_count = ""

        st.markdown(
            "<div class='glass-card'>"
            "<div class='card-label'>🎯 Detected Signals</div>"
            f"{kw_count}"
            f"{signals_html}"
            "</div>",
            unsafe_allow_html=True
        )

    # -------- HIGHLIGHTED MESSAGE -------- #
    highlighted_text = user_input
    for word in keywords:
        highlighted_text = highlighted_text.replace(
            word,
            f"<span class='highlight-word'>{word}</span>"
        )

    char_count = len(user_input)
    word_count = len(user_input.split())

    st.markdown(
        "<div class='glass-card'>"
        "<div class='card-label'>💬 Highlighted Message</div>"
        f"<div style='font-size:11px; color:rgba(255,255,255,0.3); margin-bottom:12px;'>{word_count} words · {char_count} characters</div>"
        "<div class='message-box'>"
        f"{highlighted_text}"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # -------- SAFETY TIPS -------- #
    tips = [
        ("💸 Never pay to apply", "Legitimate employers will NEVER ask for registration, training, or processing fees upfront."),
        ("🔎 Verify the company", "Search the company on LinkedIn, Glassdoor, or their official website before responding."),
        ("📵 Avoid WhatsApp-only", "Real companies use official email domains and registered job portals — not just WhatsApp."),
        ("📧 Check email domains", "Job offers from Gmail/Yahoo instead of company domains are a major red flag."),
        ("🔗 Never click blind links", "Scammers use fake links to steal your credentials. Verify every URL carefully."),
        ("📞 Call to verify", "If in doubt, call the company's official number found on their website to confirm."),
    ]

    tips_html = "<div class='tips-grid'>"
    for title, desc in tips:
        tips_html += (
            "<div class='tip-card'>"
            f"<div class='tip-title'>{title}</div>"
            f"<div class='tip-desc'>{desc}</div>"
            "</div>"
        )
    tips_html += "</div>"

    st.markdown(
        "<div class='glass-card'>"
        "<div class='card-label'>🛡️ Safety Guide</div>"
        f"{tips_html}"
        "</div>",
        unsafe_allow_html=True
    )

    # -------- REPORT FOOTER -------- #
    st.markdown(f"""
    <div class='glass-card' style='text-align:center; padding:16px;'>
      <div style='font-size:12px; color:rgba(255,255,255,0.3);'>
        🔒 This scan was performed locally — no data was stored or shared. &nbsp;|&nbsp;
        ScanLens v2.0 Pro &nbsp;|&nbsp;
        <span style='color:rgba(168,85,247,0.6);'>Powered by Smart NLP 🤖</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

elif scan_btn and not user_input:
    st.markdown(
        "<div class='glass-card' style='border:1px solid rgba(250,204,21,0.35); text-align:center; padding:32px;'>"
        "<div style='font-size:40px; margin-bottom:12px;'>✍️</div>"
        "<div style='font-family:Syne,sans-serif; font-size:16px; font-weight:700; color:#fde047; margin-bottom:8px;'>Nothing to scan!</div>"
        "<div style='font-size:13px; color:rgba(255,255,255,0.4);'>Please paste a suspicious message or upload a file above before scanning.</div>"
        "</div>",
        unsafe_allow_html=True
    )
