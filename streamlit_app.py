import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ResearchAI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Aurora animated background */
.stApp {
    background: #020008 !important;
}

.aurora-bg {
    position: relative;
    width: 100%;
    overflow: hidden;
    padding: 4rem 0 2rem;
    text-align: center;
}
.aurora-bg::before {
    content: '';
    position: absolute;
    top: -60px; left: 50%;
    transform: translateX(-50%);
    width: 900px; height: 400px;
    background: radial-gradient(ellipse at 30% 50%, rgba(120,40,255,0.35) 0%, transparent 60%),
                radial-gradient(ellipse at 70% 50%, rgba(0,200,180,0.25) 0%, transparent 60%),
                radial-gradient(ellipse at 50% 80%, rgba(255,60,120,0.15) 0%, transparent 60%);
    filter: blur(40px);
    animation: aurora 8s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
@keyframes aurora {
    0%   { transform: translateX(-50%) scale(1) rotate(0deg); opacity: 0.8; }
    50%  { transform: translateX(-48%) scale(1.05) rotate(1deg); opacity: 1; }
    100% { transform: translateX(-52%) scale(0.97) rotate(-1deg); opacity: 0.85; }
}
.aurora-bg > * { position: relative; z-index: 1; }

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #a78bfa 40%, #34d399 80%, #ffffff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -3px;
    line-height: 1;
    margin-bottom: 1rem;
}
.hero-sub {
    font-size: 1rem;
    color: #6b7280;
    font-weight: 300;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Glassmorphism pipeline */
.pipeline {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0;
    margin: 2.5rem 0 1.5rem;
    flex-wrap: wrap;
}
.pipe-badge {
    background: rgba(255,255,255,0.10);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.22);
    padding: 0.45rem 1.1rem;
    border-radius: 100px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.04em;
    transition: all 0.2s;
}
.pipe-badge:hover {
    border-color: rgba(167,139,250,0.7);
    color: #ffffff;
    background: rgba(167,139,250,0.2);
}
.pipe-arrow { color: #6b7280; font-size: 0.9rem; margin: 0 0.3rem; }

/* Input */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    color: #f9fafb !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    padding: 1rem 1.4rem !important;
    font-size: 1rem !important;
    font-family: 'Inter', sans-serif !important;
    caret-color: #a78bfa !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    backdrop-filter: blur(10px) !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(167,139,250,0.5) !important;
    box-shadow: 0 0 0 3px rgba(167,139,250,0.1) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder {
    color: #6b7280 !important;
}
/* Research button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    width: 100% !important;
    padding: 0.75rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 0 20px rgba(124,58,237,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 30px rgba(124,58,237,0.5) !important;
}

/* Example buttons */
.stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.08) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255,255,255,0.20) !important;
    border-radius: 100px !important;
    font-size: 0.78rem !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.3rem 0.9rem !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: rgba(167,139,250,0.7) !important;
    color: #ffffff !important;
    background: rgba(167,139,250,0.18) !important;
}

/* Divider */
hr {
    border-color: rgba(255,255,255,0.05) !important;
    margin: 1rem 0 !important;
}

/* Progress steps */
.step-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.7rem 1.2rem;
    border-radius: 12px;
    margin: 0.3rem 0;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    font-size: 0.88rem;
}
.step-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #1f2937;
    flex-shrink: 0;
    transition: all 0.3s;
}
.step-dot.active {
    background: #a78bfa;
    box-shadow: 0 0 10px rgba(167,139,250,0.6);
    animation: pulse-dot 1s ease-in-out infinite;
}
.step-dot.done { background: #34d399; }
@keyframes pulse-dot {
    0%,100% { transform: scale(1); opacity:1; }
    50% { transform: scale(1.4); opacity:0.8; }
}
.step-name { font-weight: 500; color: #4b5563; }
.step-name.active { color: #c4b5fd; }
.step-name.done { color: #6ee7b7; }
.step-desc { color: #374151; font-size: 0.82rem; }

/* Success banner */
.success-banner {
    background: rgba(52,211,153,0.08);
    border: 1px solid rgba(52,211,153,0.2);
    border-radius: 14px;
    padding: 1rem 1.5rem;
    margin: 1.5rem 0 1rem;
    color: #34d399;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}

/* Glass metric cards */
.metric-glass {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 1.4rem 1rem;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-glass:hover {
    border-color: rgba(167,139,250,0.2);
}
.metric-num {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #f9fafb;
    line-height: 1;
}
.metric-unit { font-size: 1.1rem; color: #374151; }
.metric-lbl {
    font-size: 0.7rem;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 0.4rem;
}
.score-bar {
    height: 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 100px;
    margin-top: 0.8rem;
    overflow: hidden;
}
.score-fill {
    height: 100%;
    border-radius: 100px;
    background: linear-gradient(90deg, #7c3aed, #34d399);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: rgba(255,255,255,0.03) !important;
    padding: 4px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #4b5563 !important;
    padding: 0.4rem 1rem !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(124,58,237,0.25) !important;
    color: #c4b5fd !important;
}

/* Content glass cards */
.glass-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 2rem;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    line-height: 1.85;
    color: #9ca3af;
    white-space: pre-wrap;
    word-break: break-word;
}

/* Source cards */
.source-card {
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.05);
    border-left: 2px solid rgba(167,139,250,0.4);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.8rem;
    color: #6b7280;
    white-space: pre-wrap;
    word-break: break-all;
}

/* Improvement items */
.improve-item {
    padding: 0.5rem 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-size: 0.86rem;
    color: #6b7280;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}
.improve-item::before {
    content: '→';
    color: #7c3aed;
    flex-shrink: 0;
    font-size: 0.8rem;
    margin-top: 1px;
}

/* Download buttons */
.stDownloadButton > button {
    background: rgba(255,255,255,0.03) !important;
    color: #6b7280 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.84rem !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.stDownloadButton > button:hover {
    background: rgba(124,58,237,0.1) !important;
    color: #c4b5fd !important;
    border-color: rgba(167,139,250,0.3) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    color: #6b7280 !important;
    font-size: 0.85rem !important;
}

/* New research button */
.stButton > button[data-testid="baseButton-secondary"] {
    background: transparent !important;
    color: #6b7280 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="aurora-bg">
    <div class="hero-title">ResearchAI</div>
    <div class="hero-sub">4 AI agents &nbsp;·&nbsp; Live web search &nbsp;·&nbsp; Self-improving reports</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pipeline">
    <span class="pipe-badge">⬡ Researcher</span>
    <span class="pipe-arrow">—</span>
    <span class="pipe-badge">⬡ Analyzer</span>
    <span class="pipe-arrow">—</span>
    <span class="pipe-badge">⬡ Writer</span>
    <span class="pipe-arrow">—</span>
    <span class="pipe-badge">⬡ Reviewer</span>
    <span class="pipe-arrow">↩</span>
    <span class="pipe-badge" style="font-size:0.7rem;color:#2d2d3a;border-color:rgba(255,255,255,0.04)">score &lt; 7 → rewrite</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Input ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    topic = st.text_input(
        "topic",
        placeholder="What do you want to research today?",
        label_visibility="collapsed",
        key="topic_input"
    )
with col2:
    start = st.button("Research →", type="primary", use_container_width=True)

# ── Examples ──────────────────────────────────────────────────────────────────
st.markdown("<p style='color:#2d3748;font-size:0.75rem;margin:0.5rem 0 0.3rem;'>Try one of these</p>",
            unsafe_allow_html=True)

examples = [
    "AI agents in 2026",
    "EV battery tech 2026",
    "Quantum computing now",
    "Climate tech funding"
]

ecols = st.columns(4)
for i, ex in enumerate(examples):
    with ecols[i]:
        if st.button(ex, key=f"ex_{i}"):
            st.session_state["run_topic"] = ex
            st.rerun()

if "run_topic" in st.session_state and st.session_state["run_topic"]:
    topic = st.session_state["run_topic"]
    start = True
    st.session_state["run_topic"] = ""

# ── Run ───────────────────────────────────────────────────────────────────────
if start and topic:
    steps_info = [
        ("Researcher", "Searching the live web..."),
        ("Analyzer", "Finding patterns & insights..."),
        ("Writer", "Drafting the report..."),
        ("Reviewer", "Quality checking..."),
    ]
    phs = []
    st.markdown("<p style='color:#4b5563;font-size:0.85rem;margin:1.5rem 0 0.5rem;font-weight:500;'>Research in progress</p>",
                unsafe_allow_html=True)
    for name, desc in steps_info:
        ph = st.empty()
        ph.markdown(f"""
        <div class="step-row">
            <div class="step-dot"></div>
            <span class="step-name">{name}</span>
            <span class="step-desc">{desc}</span>
        </div>""", unsafe_allow_html=True)
        phs.append(ph)

    phs[0].markdown("""
    <div class="step-row">
        <div class="step-dot active"></div>
        <span class="step-name active">Researcher</span>
        <span class="step-desc">Searching the live web...</span>
    </div>""", unsafe_allow_html=True)

    try:
        t0 = time.time()
        res = requests.post(f"{API_URL}/research", json={"topic": topic}, timeout=300)
        elapsed = time.time() - t0

        if res.status_code == 200:
            data = res.json()
            for i, (name, desc) in enumerate(steps_info):
                phs[i].markdown(f"""
                <div class="step-row">
                    <div class="step-dot done"></div>
                    <span class="step-name done">{name}</span>
                    <span class="step-desc" style="color:#1f2937">Done</span>
                </div>""", unsafe_allow_html=True)
            st.session_state.update({
                "result": data,
                "res_topic": topic,
                "elapsed": elapsed
            })
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(f"API error {res.status_code}: {res.text}")

    except requests.exceptions.ConnectionError:
        st.error("FastAPI chal nahi raha. Terminal mein run karo: `uvicorn main:app --reload`")
    except requests.exceptions.Timeout:
        st.error("Timeout — simpler topic try karo.")
    except Exception as e:
        st.error(f"Error: {e}")

elif start and not topic:
    st.warning("Koi topic daalo!")

# ── Results ───────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    data       = st.session_state["result"]
    res_topic  = st.session_state.get("res_topic", "")
    elapsed    = st.session_state.get("elapsed", 0)
    score      = data.get("quality_score", 0)
    rev_count  = data.get("review_count", 1)

    st.markdown(f"""
    <div class="success-banner">
        <span style="font-size:1.1rem">✦</span>
        <span>Research complete — <strong style="color:#6ee7b7">{res_topic}</strong></span>
    </div>""", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    cards = [
        (f"{score}", "/10", "Quality score", score * 10),
        ("4", "", "AI agents", None),
        (f"{rev_count}", "", "Review rounds", None),
        (f"{elapsed:.0f}", "s", "Time taken", None),
    ]
    for col, (num, unit, lbl, bar) in zip([m1, m2, m3, m4], cards):
        bar_html = f'<div class="score-bar"><div class="score-fill" style="width:{bar}%"></div></div>' if bar is not None else ""
        with col:
            st.markdown(f"""
            <div class="metric-glass">
                <div class="metric-num">{num}<span class="metric-unit">{unit}</span></div>
                <div class="metric-lbl">{lbl}</div>
                {bar_html}
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "✦ Final Report", "⬡ Research", "◈ Analysis", "◇ Draft", "⊕ Sources"
    ])

    with tab1:
        improvements = data.get("improvements", "")
        if improvements:
            with st.expander("What the reviewer improved"):
                for line in improvements.split("\n"):
                    if line.strip():
                        st.markdown(f'<div class="improve-item">{line.strip().lstrip("-").strip()}</div>',
                                    unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card">{data.get("final_report","No report.")}</div>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        fname = res_topic[:35].replace(" ", "_")
        with d1:
            st.download_button("↓ Download .txt", data.get("final_report",""),
                file_name=f"{fname}_report.txt", mime="text/plain")
        with d2:
            st.download_button("↓ Download .md", data.get("final_report",""),
                file_name=f"{fname}_report.md", mime="text/markdown")

    with tab2:
        st.markdown("<p style='color:#374151;font-size:0.8rem;margin-bottom:0.5rem'>Agent 1 — live web search output</p>",
                    unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card">{data.get("research","No data.")}</div>',
                    unsafe_allow_html=True)

    with tab3:
        st.markdown("<p style='color:#374151;font-size:0.8rem;margin-bottom:0.5rem'>Agent 2 — SWOT analysis & insights</p>",
                    unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card">{data.get("analysis","No data.")}</div>',
                    unsafe_allow_html=True)

    with tab4:
        st.markdown("<p style='color:#374151;font-size:0.8rem;margin-bottom:0.5rem'>Agent 3 — first draft before review</p>",
                    unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card">{data.get("report","No data.")}</div>',
                    unsafe_allow_html=True)

    with tab5:
        st.markdown("<p style='color:#374151;font-size:0.8rem;margin-bottom:0.5rem'>Real sources from Tavily web search</p>",
                    unsafe_allow_html=True)
        sources = data.get("sources", "")
        if sources and "No results" not in sources and "Search failed" not in sources:
            for block in sources.split("[Source "):
                if block.strip():
                    st.markdown(f'<div class="source-card">[Source {block.strip()}</div>',
                                unsafe_allow_html=True)
        else:
            st.info("Tavily se sources nahi aaye — .env mein TAVILY_API_KEY check karo.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↺ Naya research"):
        for k in ["result", "res_topic", "elapsed"]:
            st.session_state.pop(k, None)
        st.rerun()