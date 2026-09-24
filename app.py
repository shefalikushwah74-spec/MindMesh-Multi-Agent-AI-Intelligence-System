"""
Streamlit UI for the multi-agent research pipeline.

This file only builds an interface around the existing `run_pipelines`
function in pipelines.py — the agent logic itself is untouched.

Setup:
    1. Save this file as `app.py` in the same folder as pipelines.py
       (C:\\Users\\sk\\OneDrive\\Desktop\\multi agent)
    2. pip install streamlit   (inside your .venv)
    3. Run with:  streamlit run app.py
"""

import contextlib
import io
import threading
import time
import traceback
from datetime import datetime

import streamlit as st

from pipelines import run_pipelines


# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Research Agent — Multi-Agent Pipeline",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Pipeline stage definitions (used for the sidebar overview and the live
# progress stepper — kept in one place so both stay in sync)
# ----------------------------------------------------------------------------
STAGES = [
    {"key": "search", "label": "Search", "detail": "Finding sources", "marker": "search agent is working"},
    {"key": "read", "label": "Read", "detail": "Extracting content", "marker": "reader agent is scraping"},
    {"key": "write", "label": "Write", "detail": "Drafting the report", "marker": "writer is drafting"},
    {"key": "critic", "label": "Critique", "detail": "Reviewing the report", "marker": "critic is reviewing"},
]


def to_text(x) -> str:
    """Safely convert chain/agent output (str or LangChain message) to plain text."""
    if x is None:
        return ""
    if hasattr(x, "content"):
        return x.content
    return str(x)


def current_stage_index(log_text: str) -> int:
    """Index of the furthest stage whose marker has appeared in the logs so far."""
    log_lower = log_text.lower()
    idx = -1
    for i, stage in enumerate(STAGES):
        if stage["marker"] in log_lower:
            idx = i
    return idx


# ----------------------------------------------------------------------------
# Theme — dark, warm-neutral surface with a burnt-orange accent
# ----------------------------------------------------------------------------
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg:        #161310;
            --bg-2:      #1E1A16;
            --bg-3:      #241F1A;
            --border:    #38312A;
            --text:      #F3EEE7;
            --text-dim:  #A9998A;
            --accent:    #E8622C;
            --accent-2:  #FF8A50;
            --accent-dk: #7A3419;
            --ok:        #7FAE85;
            --err:       #D6674F;
        }

        html, body, [class*="css"]  {
            font-family: 'Inter', -apple-system, sans-serif;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

        section[data-testid="stSidebar"] {
            background: var(--bg-2);
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] * { color: var(--text) !important; }

        .block-container { padding-top: 2rem; max-width: 1100px; }

        /* ---------- Header ---------- */
        .app-header { display: flex; align-items: flex-start; justify-content: space-between;
                      border-bottom: 1px solid var(--border); padding-bottom: 1.4rem; margin-bottom: 1.6rem; }
        .app-title { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: var(--text); }
        .app-subtitle { font-size: 0.92rem; color: var(--text-dim); margin-top: 0.35rem; max-width: 34rem; }
        .app-kicker { font-size: 0.72rem; font-weight: 600; color: var(--accent-2); letter-spacing: 0.06em;
                      text-transform: uppercase; margin-bottom: 0.4rem; }
        .pill-row { display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }
        .pill { font-size: 0.72rem; font-weight: 500; color: var(--text-dim); border: 1px solid var(--border);
                background: var(--bg-3); padding: 0.28rem 0.65rem; border-radius: 999px; }

        /* ---------- Sidebar stage list ---------- */
        .sb-stage { display: flex; gap: 0.6rem; align-items: flex-start; padding: 0.45rem 0; }
        .sb-num { width: 22px; height: 22px; border-radius: 50%; background: var(--bg-3); border: 1px solid var(--border);
                  color: var(--accent-2); font-size: 0.72rem; font-weight: 700; display: flex; align-items: center;
                  justify-content: center; flex-shrink: 0; margin-top: 0.05rem; }
        .sb-stage-label { font-size: 0.86rem; font-weight: 600; color: var(--text); line-height: 1.15; }
        .sb-stage-detail { font-size: 0.76rem; color: var(--text-dim); margin-top: 0.1rem; }

        /* ---------- Stepper (live progress) ---------- */
        .stepper { display: flex; align-items: flex-start; margin: 0.4rem 0 1.6rem; }
        .step { flex: 1; position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .step-line { position: absolute; top: 17px; left: 50%; width: 100%; height: 2px; background: var(--border); z-index: 0; }
        .step:last-child .step-line { display: none; }
        .step.complete .step-line { background: var(--accent); }
        .step-circle { width: 34px; height: 34px; border-radius: 50%; background: var(--bg-3); border: 2px solid var(--border);
                        color: var(--text-dim); font-size: 0.8rem; font-weight: 700; display: flex; align-items: center;
                        justify-content: center; position: relative; z-index: 1; transition: all .25s ease; }
        .step.complete .step-circle { background: var(--accent); border-color: var(--accent); color: #14110D; }
        .step.active .step-circle { border-color: var(--accent); color: var(--accent-2);
                                     animation: pulse 1.3s ease-in-out infinite; }
        .step.error .step-circle { border-color: var(--err); color: var(--err); }
        .step-label { font-size: 0.8rem; font-weight: 600; margin-top: 0.5rem; color: var(--text-dim); }
        .step.complete .step-label, .step.active .step-label { color: var(--text); }
        .step-detail { font-size: 0.7rem; color: var(--text-dim); margin-top: 0.1rem; }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(232, 98, 44, 0.45); }
            50%      { box-shadow: 0 0 0 6px rgba(232, 98, 44, 0); }
        }

        /* ---------- Status pill ---------- */
        .status-pill { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 600;
                        padding: 0.3rem 0.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--bg-3); }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-dim); }
        .status-pill.running .status-dot { background: var(--accent-2); animation: pulse 1.3s ease-in-out infinite; }
        .status-pill.done .status-dot { background: var(--ok); }
        .status-pill.error .status-dot { background: var(--err); }

        /* ---------- Cards / metrics ---------- */
        .card { background: var(--bg-2); border: 1px solid var(--border); border-radius: 10px; padding: 1.1rem 1.3rem; }
        div[data-testid="stMetric"] { background: var(--bg-2); border: 1px solid var(--border); border-radius: 10px;
                                       padding: 0.85rem 1rem 0.7rem; }
        div[data-testid="stMetric"] label { color: var(--text-dim) !important; }
        div[data-testid="stMetricValue"] { color: var(--accent-2) !important; }

        /* ---------- Form / inputs ---------- */
        div[data-testid="stForm"] { background: var(--bg-2); border: 1px solid var(--border); border-radius: 12px;
                                     padding: 1.3rem 1.4rem 1rem; }
        .stTextInput input {
            background: var(--bg-3) !important; color: var(--text) !important;
            border: 1px solid var(--border) !important; border-radius: 8px !important;
        }
        .stTextInput input:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 1px var(--accent) !important; }
        .stTextInput label { color: var(--text-dim) !important; font-size: 0.85rem !important; }

        .stButton button, .stFormSubmitButton button, .stDownloadButton button {
            background: var(--accent) !important; color: #17130F !important; border: none !important;
            font-weight: 700 !important; border-radius: 8px !important; padding: 0.5rem 1.2rem !important;
            transition: background .15s ease !important;
        }
        .stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {
            background: var(--accent-2) !important; color: #17130F !important;
        }
        .stButton button[kind="secondary"] {
            background: transparent !important; color: var(--text-dim) !important; border: 1px solid var(--border) !important;
        }
        .stButton button[kind="secondary"]:hover { color: var(--text) !important; border-color: var(--text-dim) !important; }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] { gap: 1.6rem; border-bottom: 1px solid var(--border); }
        .stTabs [data-baseweb="tab"] { background: transparent; color: var(--text-dim); font-weight: 600;
                                        font-size: 0.88rem; padding: 0.4rem 0.1rem; }
        .stTabs [aria-selected="true"] { color: var(--text) !important; border-bottom: 2px solid var(--accent) !important; }
        .stTabs [data-baseweb="tab-panel"] { padding-top: 1.1rem; }

        /* ---------- Misc ---------- */
        .stAlert { border-radius: 8px; }
        code, pre { font-family: 'JetBrains Mono', monospace !important; }
        .app-footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--border);
                      font-size: 0.76rem; color: var(--text-dim); display: flex; justify-content: space-between; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------------
def render_stepper(placeholder, active_idx: int, error: bool = False):
    """Render the horizontal progress stepper into `placeholder`.

    active_idx == -1        -> nothing started yet, all steps pending
    active_idx in [0, n-1]  -> that step is in progress, earlier ones complete
    active_idx == len-1 and finished -> caller passes len(STAGES) to mark all complete
    """
    n = len(STAGES)
    html = ['<div class="stepper">']
    for i, stage in enumerate(STAGES):
        if error and i == max(active_idx, 0):
            state = "error"
        elif active_idx >= n:
            state = "complete"
        elif i < active_idx:
            state = "complete"
        elif i == active_idx:
            state = "active"
        else:
            state = "pending"

        icon = "✓" if state == "complete" else ("!" if state == "error" else str(i + 1))
        html.append(f'<div class="step {state}">')
        if i < n - 1:
            html.append('<div class="step-line"></div>')
        html.append(f'<div class="step-circle">{icon}</div>')
        html.append(f'<div class="step-label">{stage["label"]}</div>')
        html.append(f'<div class="step-detail">{stage["detail"]}</div>')
        html.append("</div>")
    html.append("</div>")
    placeholder.markdown("".join(html), unsafe_allow_html=True)


def render_status_pill(placeholder, state: str):
    labels = {"idle": "Idle", "running": "Running", "done": "Complete", "error": "Error"}
    placeholder.markdown(
        f'<div class="status-pill {state}"><span class="status-dot"></span>{labels[state]}</div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
for key, default in {
    "result": None, "logs": "", "topic": "", "error": None, "run_state": "idle",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="app-kicker">Pipeline overview</div>', unsafe_allow_html=True)
    for i, stage in enumerate(STAGES, start=1):
        st.markdown(
            f"""
            <div class="sb-stage">
                <div class="sb-num">{i}</div>
                <div>
                    <div class="sb-stage-label">{stage['label']} agent</div>
                    <div class="sb-stage-detail">{stage['detail']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    show_logs = st.checkbox("Show console logs", value=False)
    if st.session_state.result and st.button("Clear session", type="secondary", use_container_width=True):
        st.session_state.update(result=None, logs="", error=None, run_state="idle")
        st.rerun()


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
col_title, col_pills = st.columns([2.2, 1])
with col_title:
    st.markdown('<div class="app-kicker">Multi-agent research system</div>', unsafe_allow_html=True)
    st.markdown('<p class="app-title">Research Agent</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Four coordinated agents search, read, write, and critique — '
        'turning a topic into a sourced, reviewed report.</p>',
        unsafe_allow_html=True,
    )
with col_pills:
    st.markdown(
        '<div class="pill-row">'
        + "".join(f'<span class="pill">{s["label"]}</span>' for s in STAGES)
        + "</div>",
        unsafe_allow_html=True,
    )
st.markdown('<div class="app-header" style="border:none;margin:0;padding:0;"></div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Input form
# ----------------------------------------------------------------------------
with st.form("topic_form"):
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. Latest advances in solid-state batteries",
        value=st.session_state.topic,
        label_visibility="visible",
    )
    submitted = st.form_submit_button("Run pipeline", type="primary")

status_placeholder = st.empty()
stepper_placeholder = st.empty()

# initial / idle render
if st.session_state.run_state == "idle" and not st.session_state.result:
    render_status_pill(status_placeholder, "idle")
    render_stepper(stepper_placeholder, -1)
elif st.session_state.result:
    render_status_pill(status_placeholder, "done")
    render_stepper(stepper_placeholder, len(STAGES))
elif st.session_state.error:
    render_status_pill(status_placeholder, "error")
    render_stepper(stepper_placeholder, current_stage_index(st.session_state.logs), error=True)


# ----------------------------------------------------------------------------
# Run pipeline (background thread so the UI can poll progress live)
# ----------------------------------------------------------------------------
if submitted:
    if not topic.strip():
        st.warning("Please enter a topic first.")
    else:
        st.session_state.topic = topic
        st.session_state.error = None
        st.session_state.result = None
        st.session_state.run_state = "running"

        log_buffer = io.StringIO()
        outcome = {}

        def worker():
            try:
                with contextlib.redirect_stdout(log_buffer):
                    outcome["result"] = run_pipelines(topic)
            except Exception:
                outcome["error"] = traceback.format_exc()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        render_status_pill(status_placeholder, "running")
        while thread.is_alive():
            idx = current_stage_index(log_buffer.getvalue())
            render_stepper(stepper_placeholder, idx)
            time.sleep(0.35)
        thread.join()

        st.session_state.logs = log_buffer.getvalue()

        if "error" in outcome:
            st.session_state.error = outcome["error"]
            st.session_state.run_state = "error"
        else:
            st.session_state.result = outcome.get("result")
            st.session_state.run_state = "done"

        st.rerun()


# ----------------------------------------------------------------------------
# Error state
# ----------------------------------------------------------------------------
if st.session_state.error:
    st.error("The pipeline raised an error while running.")
    with st.expander("Traceback", expanded=False):
        st.code(st.session_state.error)


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
result = st.session_state.result
if result:
    report_text = to_text(result.get("report"))
    report_text = report_text.replace("[Your Name]", "Shefali Kushwah")
    feedback_text = to_text(result.get("feedback"))
    search_text = to_text(result.get("search_results"))
    scraped_text = to_text(result.get("Scraped_content"))

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Report length", f"{len(report_text.split())} words")
    m2.metric("Sources scraped", f"{len(scraped_text):,} chars")
    m3.metric("Search coverage", f"{len(search_text):,} chars")

    st.markdown("<br>", unsafe_allow_html=True)
    tab_report, tab_feedback, tab_search, tab_scraped = st.tabs(
        ["Report", "Critic feedback", "Search results", "Scraped content"]
    )

    with tab_report:
        st.markdown(report_text or "_No report generated._")
        st.download_button(
            "Download report (.md)",
            data=report_text,
            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
        )

    with tab_feedback:
        st.markdown(feedback_text or "_No feedback generated._")

    with tab_search:
        st.text(search_text or "No search results.")

    with tab_scraped:
        st.text(scraped_text or "No scraped content.")

if show_logs and st.session_state.logs:
    with st.expander("Console logs", expanded=False):
        st.code(st.session_state.logs)

if not result and not st.session_state.error and st.session_state.run_state == "idle":
    st.info("Enter a topic above and select **Run pipeline** to get started.")

st.markdown(
    '<div class="app-footer"><span>Search → Read → Write → Critique</span>'
    '<span>Built with LangChain &amp; Streamlit</span></div>',
    unsafe_allow_html=True,
)