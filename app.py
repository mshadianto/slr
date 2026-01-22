"""
Muezza AI - Faithful Research Companion
=======================================
Premium Agentic Systematic Literature Review Dashboard.
Enterprise-grade UI with modern, serene aesthetics.

Usage:
    streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import asyncio
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import local modules
from config import settings
from agents.state import SLRState, PRISMAStats, AgentStatus, create_initial_state
from agents.orchestrator import SLROrchestrator
from agents.narrative_generator import NarrativeGenerator, generate_results_chapter
from agents.narrative_orchestrator import NarrativeOrchestrator
from agents.citation_stitcher import CitationAutoStitcher, CitationStyle
from agents.logic_continuity_agent import LogicContinuityAgent
from agents.forensic_audit_agent import ForensicAuditAgent, VerificationStatus
from agents.docx_generator import DocxGenerator

# Page configuration
st.set_page_config(
    page_title="Muezza AI | Faithful Research Companion",
    page_icon="🐱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PREMIUM CSS THEME - Emerald Green, Gold, Dark Slate Gray
# ============================================================================
st.markdown("""
<style>
    /* ===== ROOT VARIABLES ===== */
    :root {
        --emerald-50: #ecfdf5;
        --emerald-100: #d1fae5;
        --emerald-200: #a7f3d0;
        --emerald-300: #6ee7b7;
        --emerald-400: #34d399;
        --emerald-500: #10b981;
        --emerald-600: #059669;
        --emerald-700: #047857;
        --emerald-800: #065f46;
        --emerald-900: #064e3b;

        --gold-50: #fffbeb;
        --gold-100: #fef3c7;
        --gold-200: #fde68a;
        --gold-300: #fcd34d;
        --gold-400: #fbbf24;
        --gold-500: #f59e0b;
        --gold-600: #d97706;
        --gold-700: #b45309;

        --slate-50: #f8fafc;
        --slate-100: #f1f5f9;
        --slate-200: #e2e8f0;
        --slate-300: #cbd5e1;
        --slate-400: #94a3b8;
        --slate-500: #64748b;
        --slate-600: #475569;
        --slate-700: #334155;
        --slate-800: #1e293b;
        --slate-900: #0f172a;

        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #3b82f6;
    }

    /* ===== GLOBAL STYLES ===== */
    .stApp {
        background: linear-gradient(180deg, var(--slate-900) 0%, var(--slate-800) 100%);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== SIDEBAR STYLES ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--slate-800) 0%, var(--slate-900) 100%);
        border-right: 1px solid var(--emerald-800);
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: var(--slate-200);
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--emerald-400) !important;
        font-weight: 600;
    }

    /* ===== MAIN HEADER ===== */
    .main-header {
        background: linear-gradient(135deg, var(--emerald-900) 0%, var(--slate-800) 50%, var(--emerald-800) 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid var(--emerald-700);
        box-shadow: 0 4px 24px rgba(16, 185, 129, 0.15);
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 300px;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.05));
        pointer-events: none;
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--emerald-300), var(--gold-400));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .main-header .tagline {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        color: var(--slate-300);
        font-weight: 400;
        letter-spacing: 0.5px;
    }

    .main-header .version-badge {
        display: inline-block;
        background: var(--gold-500);
        color: var(--slate-900);
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 1rem;
        vertical-align: middle;
    }

    /* ===== AGENT CARDS ===== */
    .agent-card {
        background: linear-gradient(145deg, var(--slate-800), var(--slate-900));
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.5rem 0;
        border: 1px solid var(--slate-700);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .agent-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .agent-card.active {
        border-color: var(--emerald-500);
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
    }

    .agent-card.active::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--emerald-400), var(--emerald-600));
    }

    .agent-card.completed {
        border-color: var(--gold-500);
    }

    .agent-card.completed::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--gold-400), var(--gold-600));
    }

    .agent-card.error {
        border-color: var(--danger);
    }

    .agent-card .agent-icon {
        font-size: 1.75rem;
        margin-bottom: 0.5rem;
    }

    .agent-card .agent-name {
        font-size: 1rem;
        font-weight: 600;
        color: var(--slate-100);
        margin: 0;
    }

    .agent-card .agent-status {
        font-size: 0.8rem;
        color: var(--slate-400);
        margin-top: 0.25rem;
    }

    .agent-card .agent-status.running {
        color: var(--emerald-400);
    }

    .agent-card .agent-status.completed {
        color: var(--gold-400);
    }

    /* ===== API STATUS INDICATORS ===== */
    .api-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--slate-800);
        border-radius: 8px;
        margin: 0.25rem 0;
        border: 1px solid var(--slate-700);
    }

    .api-status .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }

    .api-status .dot.online {
        background: var(--emerald-500);
        box-shadow: 0 0 8px var(--emerald-500);
    }

    .api-status .dot.offline {
        background: var(--danger);
        animation: none;
    }

    .api-status .dot.warning {
        background: var(--warning);
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .api-status .name {
        font-size: 0.85rem;
        color: var(--slate-300);
    }

    /* ===== PRISMA METRICS ===== */
    .metric-card {
        background: linear-gradient(145deg, var(--slate-800), var(--slate-900));
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        border: 1px solid var(--slate-700);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        border-color: var(--emerald-600);
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.1);
    }

    .metric-card .number {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--emerald-400), var(--gold-400));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-card .label {
        font-size: 0.85rem;
        color: var(--slate-400);
        margin-top: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ===== TERMINAL LOG ===== */
    .terminal-log {
        background: var(--slate-900);
        border: 1px solid var(--slate-700);
        border-radius: 12px;
        padding: 1rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
    }

    .terminal-log .log-entry {
        padding: 0.25rem 0;
        border-bottom: 1px solid var(--slate-800);
        color: var(--slate-300);
    }

    .terminal-log .log-entry:last-child {
        border-bottom: none;
    }

    .terminal-log .timestamp {
        color: var(--slate-500);
        margin-right: 0.5rem;
    }

    .terminal-log .agent-name {
        color: var(--emerald-400);
        font-weight: 600;
    }

    .terminal-log .action {
        color: var(--gold-400);
    }

    .terminal-log .success {
        color: var(--emerald-400);
    }

    .terminal-log .error {
        color: var(--danger);
    }

    /* ===== DATA TABLE ===== */
    .audit-table {
        background: var(--slate-800);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--slate-700);
    }

    .audit-table th {
        background: var(--slate-900);
        color: var(--emerald-400);
        padding: 1rem;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        font-weight: 600;
    }

    .audit-table td {
        padding: 0.875rem 1rem;
        color: var(--slate-200);
        border-bottom: 1px solid var(--slate-700);
    }

    .audit-table tr:hover td {
        background: var(--slate-700);
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        background: linear-gradient(135deg, var(--emerald-600), var(--emerald-700)) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--gold-500), var(--gold-600)) !important;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3) !important;
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--slate-800);
        border-radius: 12px;
        padding: 0.5rem;
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--slate-400);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--emerald-600), var(--emerald-700)) !important;
        color: white !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background: var(--slate-800);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
        border: 1px solid var(--slate-700);
    }

    /* ===== INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: var(--slate-800) !important;
        border: 1px solid var(--slate-600) !important;
        border-radius: 8px !important;
        color: var(--slate-200) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--emerald-500) !important;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2) !important;
    }

    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background: var(--slate-800) !important;
        border-radius: 8px !important;
        color: var(--slate-200) !important;
    }

    .streamlit-expanderContent {
        background: var(--slate-900) !important;
        border: 1px solid var(--slate-700) !important;
        border-top: none !important;
    }

    /* ===== DIVIDER ===== */
    hr {
        border-color: var(--slate-700) !important;
        margin: 2rem 0 !important;
    }

    /* ===== SECTION HEADERS ===== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }

    .section-header h2 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--slate-100);
    }

    .section-header .icon {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, var(--emerald-600), var(--emerald-700));
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }

    /* ===== VERIFICATION MODAL ===== */
    .verification-modal {
        background: var(--slate-800);
        border: 1px solid var(--emerald-600);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .verification-modal .source-text {
        background: var(--slate-900);
        border-left: 3px solid var(--gold-500);
        padding: 1rem;
        font-style: italic;
        color: var(--slate-300);
        margin: 1rem 0;
    }

    .verification-modal .confidence-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .verification-modal .confidence-badge.high {
        background: var(--emerald-900);
        color: var(--emerald-400);
    }

    .verification-modal .confidence-badge.medium {
        background: var(--gold-900);
        color: var(--gold-400);
    }

    .verification-modal .confidence-badge.low {
        background: rgba(239, 68, 68, 0.2);
        color: var(--danger);
    }

    /* ===== DOWNLOAD BUTTON ===== */
    .download-section {
        background: linear-gradient(135deg, var(--slate-800), var(--slate-900));
        border: 1px solid var(--gold-600);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-top: 2rem;
    }

    .download-section h3 {
        color: var(--gold-400);
        margin-bottom: 1rem;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--slate-900);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--slate-600);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--slate-500);
    }

    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--emerald-500), var(--gold-500)) !important;
    }

    /* ===== SELECTBOX ===== */
    [data-baseweb="select"] {
        background: var(--slate-800) !important;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        background: var(--slate-800);
        border: 2px dashed var(--slate-600);
        border-radius: 12px;
        padding: 1rem;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--emerald-500);
    }

    /* ===== METRICS ===== */
    [data-testid="stMetric"] {
        background: var(--slate-800);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid var(--slate-700);
    }

    [data-testid="stMetricValue"] {
        color: var(--emerald-400) !important;
    }

    /* ===== CAT LOGO ANIMATION ===== */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    .muezza-logo {
        animation: float 3s ease-in-out infinite;
        font-size: 3rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "slr_state": None,
        "orchestrator": None,
        "is_running": False,
        "progress": 0,
        "progress_message": "",
        "processing_log": [],
        "prisma_stats": PRISMAStats(),
        "agent_status": {
            "search": AgentStatus.PENDING,
            "screening": AgentStatus.PENDING,
            "acquisition": AgentStatus.PENDING,
            "quality": AgentStatus.PENDING,
        },
        "quality_distribution": {"HIGH": 0, "MODERATE": 0, "LOW": 0, "CRITICAL": 0},
        "results_df": None,
        "narrative_generator": None,
        "generated_narratives": None,
        "narrative_generating": False,
        "report_orchestrator": None,
        "full_report_chapters": None,
        "report_generating": False,
        "citation_stitcher": None,
        "continuity_report": None,
        "bibliography_loaded": False,
        "forensic_audit_result": None,
        "researcher_name": "Peneliti",
        "institution": "",
        "generated_bibliography": [],
        "verification_modal_open": False,
        "selected_paper_for_verification": None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def check_configuration() -> Dict[str, bool]:
    """Check if required API keys are configured."""
    return {
        "anthropic": bool(settings.anthropic_api_key),
        "scopus": bool(settings.scopus_api_key),
        "semantic_scholar": bool(settings.semantic_scholar_api_key),
        "core": bool(getattr(settings, 'core_api_key', None)),
        "unpaywall": bool(settings.unpaywall_email),
    }


def add_log_entry(message: str, agent: str = "Muezza", log_type: str = "info"):
    """Add entry to processing log."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    entry = {
        "timestamp": timestamp,
        "agent": agent,
        "message": message,
        "type": log_type
    }
    st.session_state.processing_log.append(entry)


def render_api_status_indicator(name: str, is_configured: bool):
    """Render a single API status indicator."""
    status_class = "online" if is_configured else "offline"
    status_text = "Connected" if is_configured else "Not Configured"

    st.markdown(f"""
    <div class="api-status">
        <span class="dot {status_class}"></span>
        <span class="name">{name}</span>
        <span style="margin-left: auto; font-size: 0.75rem; color: var(--slate-500);">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)


def render_agent_card(icon: str, name: str, description: str, status: AgentStatus):
    """Render an agent status card."""
    status_class = status.value.lower()
    status_text = {
        AgentStatus.PENDING: "Waiting...",
        AgentStatus.ACTIVE: "Running",
        AgentStatus.COMPLETED: "Completed",
        AgentStatus.ERROR: "Error"
    }
    status_icon = {
        AgentStatus.PENDING: "⏳",
        AgentStatus.ACTIVE: "🔄",
        AgentStatus.COMPLETED: "✅",
        AgentStatus.ERROR: "❌"
    }

    st.markdown(f"""
    <div class="agent-card {status_class}">
        <div class="agent-icon">{icon}</div>
        <p class="agent-name">{name}</p>
        <p class="agent-status {status_class}">{status_icon[status]} {status_text[status]}</p>
        <p style="font-size: 0.75rem; color: var(--slate-500); margin-top: 0.5rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(value: int, label: str, icon: str):
    """Render a PRISMA metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="number">{value}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_terminal_log():
    """Render the terminal-style processing log."""
    st.markdown('<div class="terminal-log">', unsafe_allow_html=True)

    if not st.session_state.processing_log:
        st.markdown("""
        <div class="log-entry">
            <span class="timestamp">[--:--:--]</span>
            <span class="agent-name">Muezza</span>
            <span style="color: var(--slate-400);"> is ready and waiting for your command...</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        for entry in st.session_state.processing_log[-15:]:
            type_class = entry.get("type", "info")
            st.markdown(f"""
            <div class="log-entry">
                <span class="timestamp">[{entry['timestamp']}]</span>
                <span class="agent-name">{entry['agent']}</span>
                <span class="{type_class}"> {entry['message']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_prisma_sankey(stats: PRISMAStats):
    """Render PRISMA 2020 Sankey diagram with premium styling."""

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="rgba(16, 185, 129, 0.5)", width=1),
            label=[
                f"Identified<br>n={stats.identified}",
                f"After Dedup<br>n={stats.identified - stats.duplicates_removed}",
                f"Screened<br>n={stats.screened}",
                f"Sought<br>n={stats.sought_retrieval}",
                f"Assessed<br>n={stats.assessed_eligibility}",
                f"Included<br>n={stats.included_synthesis}",
                f"Duplicates<br>n={stats.duplicates_removed}",
                f"Excluded<br>n={stats.excluded_screening}",
                f"Not Retrieved<br>n={stats.not_retrieved}",
                f"Excluded<br>n={stats.excluded_eligibility}"
            ],
            color=[
                "#10b981",  # Identified - emerald
                "#34d399",  # After Dedup
                "#6ee7b7",  # Screened
                "#fbbf24",  # Sought - gold
                "#f59e0b",  # Assessed
                "#10b981",  # Included - emerald
                "#64748b",  # Duplicates - slate
                "#ef4444",  # Excluded screening - red
                "#94a3b8",  # Not retrieved
                "#dc2626"   # Excluded eligibility
            ],
            customdata=[
                "Papers identified from databases",
                "After duplicate removal",
                "Screened by title/abstract",
                "Full-text retrieval attempted",
                "Assessed for eligibility",
                "Included in synthesis",
                "Duplicate records removed",
                "Excluded at screening",
                "Could not retrieve full-text",
                "Excluded after assessment"
            ],
            hovertemplate='%{label}<br>%{customdata}<extra></extra>'
        ),
        link=dict(
            source=[0, 1, 2, 2, 3, 3, 4, 4],
            target=[1, 2, 3, 7, 4, 8, 5, 9],
            value=[
                max(1, stats.identified - stats.duplicates_removed),
                max(1, stats.screened),
                max(1, stats.sought_retrieval),
                max(1, stats.excluded_screening),
                max(1, stats.assessed_eligibility),
                max(1, stats.not_retrieved),
                max(1, stats.included_synthesis),
                max(1, stats.excluded_eligibility)
            ],
            color=[
                "rgba(16, 185, 129, 0.3)",
                "rgba(52, 211, 153, 0.3)",
                "rgba(110, 231, 183, 0.3)",
                "rgba(239, 68, 68, 0.2)",
                "rgba(251, 191, 36, 0.3)",
                "rgba(148, 163, 184, 0.2)",
                "rgba(16, 185, 129, 0.4)",
                "rgba(220, 38, 38, 0.2)"
            ]
        )
    )])

    fig.update_layout(
        title=dict(
            text="PRISMA 2020 Flow Diagram",
            font=dict(color="#e2e8f0", size=16),
            x=0.5
        ),
        font=dict(color="#94a3b8", size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def render_quality_chart(distribution: Dict[str, int]):
    """Render quality distribution chart."""
    colors = {
        "HIGH": "#10b981",
        "MODERATE": "#fbbf24",
        "LOW": "#f97316",
        "CRITICAL": "#ef4444"
    }

    fig = go.Figure(data=[
        go.Bar(
            x=list(distribution.keys()),
            y=list(distribution.values()),
            marker_color=[colors.get(k, "#64748b") for k in distribution.keys()],
            text=list(distribution.values()),
            textposition='auto',
            textfont=dict(color='white', size=14, family='Arial Black'),
            hovertemplate='<b>%{x}</b><br>Papers: %{y}<extra></extra>'
        )
    ])

    fig.update_layout(
        title=dict(
            text="Quality Assessment Distribution",
            font=dict(color="#e2e8f0", size=14),
            x=0.5
        ),
        xaxis=dict(
            title="Quality Category",
            color="#94a3b8",
            gridcolor="rgba(100, 116, 139, 0.2)"
        ),
        yaxis=dict(
            title="Number of Papers",
            color="#94a3b8",
            gridcolor="rgba(100, 116, 139, 0.2)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        bargap=0.3
    )

    return fig


def progress_callback(phase: str, percent: int, message: str):
    """Callback for progress updates from the orchestrator."""
    st.session_state.progress = percent
    st.session_state.progress_message = message

    # Determine agent name for log
    agent_names = {
        "search": "Search Strategist",
        "screening": "Screening Specialist",
        "acquisition": "Waterfall Retrieval",
        "quality": "Quality Evaluator"
    }

    agent_name = agent_names.get(phase, "Muezza")

    # Update agent status
    if percent >= 0:
        if phase == "search":
            st.session_state.agent_status["search"] = AgentStatus.ACTIVE if percent < 25 else AgentStatus.COMPLETED
        elif phase == "screening":
            st.session_state.agent_status["screening"] = AgentStatus.ACTIVE if percent < 50 else AgentStatus.COMPLETED
        elif phase == "acquisition":
            st.session_state.agent_status["acquisition"] = AgentStatus.ACTIVE if percent < 75 else AgentStatus.COMPLETED
        elif phase == "quality":
            st.session_state.agent_status["quality"] = AgentStatus.ACTIVE if percent < 100 else AgentStatus.COMPLETED
    else:
        st.session_state.agent_status[phase] = AgentStatus.ERROR

    # Add to log
    add_log_entry(message, agent_name, "action")


async def run_slr_pipeline(
    research_question: str,
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    date_range: tuple
):
    """Run the SLR pipeline asynchronously."""
    orchestrator = SLROrchestrator(progress_callback=progress_callback)

    st.session_state.orchestrator = orchestrator
    st.session_state.is_running = True

    add_log_entry("Starting systematic literature review pipeline...", "Muezza", "action")

    try:
        final_state = await orchestrator.run(
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            date_range=date_range
        )

        st.session_state.slr_state = final_state

        if final_state:
            stats = final_state.get("prisma_stats", {})
            st.session_state.prisma_stats = PRISMAStats(
                identified=stats.get("identified", 0),
                duplicates_removed=stats.get("duplicates_removed", 0),
                screened=stats.get("screened", 0),
                excluded_screening=stats.get("excluded_screening", 0),
                sought_retrieval=stats.get("sought_retrieval", 0),
                not_retrieved=stats.get("not_retrieved", 0),
                assessed_eligibility=stats.get("assessed_eligibility", 0),
                excluded_eligibility=stats.get("excluded_eligibility", 0),
                included_synthesis=stats.get("included_synthesis", 0),
            )

            synthesis_papers = final_state.get("synthesis_ready", [])
            sensitivity_papers = final_state.get("sensitivity_analysis", [])
            excluded_papers = final_state.get("excluded_quality", [])

            st.session_state.quality_distribution = {
                "HIGH": sum(1 for p in synthesis_papers if p.get("quality_category") == "HIGH"),
                "MODERATE": sum(1 for p in synthesis_papers if p.get("quality_category") == "MODERATE"),
                "LOW": len(sensitivity_papers),
                "CRITICAL": len(excluded_papers),
            }

            all_assessed = final_state.get("assessed_papers", [])
            if all_assessed:
                st.session_state.results_df = pd.DataFrame([
                    {
                        "Title": p.get("title", "")[:80] + "..." if len(p.get("title", "")) > 80 else p.get("title", ""),
                        "Source": p.get("full_text_source", "N/A"),
                        "Method": p.get("retrieval_method", "N/A"),
                        "Quality": p.get("quality_score", 0),
                        "Category": p.get("quality_category", "N/A"),
                        "DOI": p.get("doi", ""),
                    }
                    for p in all_assessed
                ])

        add_log_entry("Pipeline completed successfully!", "Muezza", "success")

    except Exception as e:
        add_log_entry(f"Pipeline failed: {str(e)}", "Muezza", "error")
    finally:
        st.session_state.is_running = False


# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    """Main application entry point."""

    # ========== HEADER ==========
    st.markdown("""
    <div class="main-header">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span class="muezza-logo">🐱</span>
            <div>
                <h1>Muezza AI <span class="version-badge">v2.0</span></h1>
                <p class="tagline">Faithful Research Companion — Your Intelligent SLR Automation System</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid var(--slate-700); margin-bottom: 1rem;">
            <span style="font-size: 2.5rem;">🐱</span>
            <h2 style="margin: 0.5rem 0 0 0; color: var(--emerald-400);">Muezza AI</h2>
            <p style="font-size: 0.8rem; color: var(--slate-400); margin: 0;">Command Center</p>
        </div>
        """, unsafe_allow_html=True)

        # API Status Section
        st.markdown("### 🔌 API Status")
        config = check_configuration()
        render_api_status_indicator("Scopus", config["scopus"])
        render_api_status_indicator("Semantic Scholar", config["semantic_scholar"])
        render_api_status_indicator("CORE", config.get("core", False))
        render_api_status_indicator("Claude AI", config["anthropic"])
        render_api_status_indicator("Unpaywall", config["unpaywall"])

        st.markdown("---")

        # Research Question
        st.markdown("### 🎯 Research Question")
        research_question = st.text_area(
            "Define your research question",
            placeholder="e.g., What is the effectiveness of machine learning in medical diagnosis?",
            height=100,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Inclusion Criteria
        st.markdown("### ✅ Inclusion Criteria")
        inclusion_text = st.text_area(
            "One criterion per line",
            placeholder="Published 2019-2024\nEnglish language\nPeer-reviewed journals\nEmpirical studies",
            height=100,
            label_visibility="collapsed"
        )

        # Exclusion Criteria
        st.markdown("### ❌ Exclusion Criteria")
        exclusion_text = st.text_area(
            "One criterion per line",
            placeholder="Conference abstracts only\nCase reports\nOpinion pieces\nNon-English",
            height=100,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Date Range
        st.markdown("### 📅 Publication Period")
        date_cols = st.columns(2)
        with date_cols[0]:
            start_year = st.number_input("From", min_value=1990, max_value=2026, value=2019)
        with date_cols[1]:
            end_year = st.number_input("To", min_value=1990, max_value=2026, value=2024)

        st.markdown("---")

        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button(
                "🚀 Start",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_running
            )
        with col2:
            reset_button = st.button(
                "🔄 Reset",
                use_container_width=True
            )

        if reset_button:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()

    # ========== MAIN CONTENT ==========

    # Agent Status Cards Row
    st.markdown("""
    <div class="section-header">
        <div class="icon">🤖</div>
        <h2>Agent Status Monitor</h2>
    </div>
    """, unsafe_allow_html=True)

    agent_cols = st.columns(4)

    agents_config = [
        ("🔍", "Search Strategist", "Boolean query & database search", "search"),
        ("🔬", "Screening Specialist", "Title/Abstract AI screening", "screening"),
        ("📥", "Waterfall Retrieval", "Multi-source full-text fetch", "acquisition"),
        ("⚖️", "Quality Evaluator", "JBI critical appraisal", "quality"),
    ]

    for col, (icon, name, desc, key) in zip(agent_cols, agents_config):
        with col:
            render_agent_card(icon, name, desc, st.session_state.agent_status[key])

    st.markdown("---")

    # Two Column Layout: PRISMA + Log
    main_col1, main_col2 = st.columns([2, 1])

    with main_col1:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>PRISMA 2020 Flow</h2>
        </div>
        """, unsafe_allow_html=True)

        # PRISMA Metrics Row
        metric_cols = st.columns(5)
        stats = st.session_state.prisma_stats
        metrics_config = [
            (stats.identified, "Identified", "🔵"),
            (stats.screened, "Screened", "🟢"),
            (stats.sought_retrieval, "Retrieved", "🟡"),
            (stats.assessed_eligibility, "Assessed", "🟠"),
            (stats.included_synthesis, "Included", "✅"),
        ]

        for col, (value, label, icon) in zip(metric_cols, metrics_config):
            with col:
                render_metric_card(value, label, icon)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sankey Diagram
        st.plotly_chart(
            render_prisma_sankey(stats),
            use_container_width=True,
            config={'displayModeBar': False}
        )

    with main_col2:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Processing Log</h2>
        </div>
        """, unsafe_allow_html=True)

        render_terminal_log()

        # Quality Distribution (if data available)
        if sum(st.session_state.quality_distribution.values()) > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(
                render_quality_chart(st.session_state.quality_distribution),
                use_container_width=True,
                config={'displayModeBar': False}
            )

    # Run Pipeline
    if run_button and research_question:
        inclusion_criteria = [c.strip() for c in inclusion_text.split('\n') if c.strip()]
        exclusion_criteria = [c.strip() for c in exclusion_text.split('\n') if c.strip()]

        add_log_entry(f"Research question received: {research_question[:50]}...", "Muezza", "info")

        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("Muezza is working on your systematic review..."):
            asyncio.run(run_slr_pipeline(
                research_question=research_question,
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                date_range=(start_year, end_year)
            ))

        st.success("🎉 Systematic review completed!")
        st.balloons()
        st.rerun()

    # ========== FORENSIC AUDIT TABLE ==========
    if st.session_state.results_df is not None and not st.session_state.results_df.empty:
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <div class="icon">🔬</div>
            <h2>Forensic Audit Results</h2>
        </div>
        """, unsafe_allow_html=True)

        # Create styled dataframe
        df = st.session_state.results_df.copy()

        # Add verification button column indicator
        df['Verify'] = '🔍 Verify'

        # Display table
        st.dataframe(
            df,
            use_container_width=True,
            height=400,
            column_config={
                "Title": st.column_config.TextColumn("Paper Title", width="large"),
                "Source": st.column_config.TextColumn("Source", width="small"),
                "Method": st.column_config.TextColumn("Retrieval", width="small"),
                "Quality": st.column_config.ProgressColumn("Quality Score", min_value=0, max_value=100),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "DOI": st.column_config.TextColumn("DOI", width="medium"),
                "Verify": st.column_config.TextColumn("Action", width="small"),
            }
        )

        # Verification Modal
        st.markdown("### 🔍 Citation Verification")

        verify_cols = st.columns([3, 1])
        with verify_cols[0]:
            selected_doi = st.selectbox(
                "Select paper to verify",
                options=df['DOI'].tolist(),
                format_func=lambda x: f"{x}" if x else "No DOI available"
            )

        with verify_cols[1]:
            verify_btn = st.button("🔬 Verify Citation", type="primary", use_container_width=True)

        if verify_btn and selected_doi:
            paper_row = df[df['DOI'] == selected_doi].iloc[0]

            st.markdown(f"""
            <div class="verification-modal">
                <h4 style="color: var(--emerald-400); margin-bottom: 1rem;">📄 Verification Report</h4>
                <p><strong>Title:</strong> {paper_row['Title']}</p>
                <p><strong>DOI:</strong> <a href="https://doi.org/{selected_doi}" target="_blank" style="color: var(--gold-400);">{selected_doi}</a></p>
                <p><strong>Source:</strong> {paper_row['Source']} | <strong>Method:</strong> {paper_row['Method']}</p>

                <div class="source-text">
                    <p style="font-size: 0.9rem; color: var(--slate-400); margin-bottom: 0.5rem;">📝 Extracted Abstract/Key Passage:</p>
                    "This study investigates the application of [methodology] in [domain].
                    Our findings suggest that [key finding] with statistical significance (p < 0.05).
                    The implications for [field] are discussed..."
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <span class="confidence-badge high">✅ Verified Source</span>
                    <span class="confidence-badge medium">Quality: {paper_row['Quality']}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export Options
        st.markdown("---")
        export_cols = st.columns(4)

        with export_cols[0]:
            csv_data = st.session_state.results_df.to_csv(index=False)
            st.download_button(
                label="📄 Export CSV",
                data=csv_data,
                file_name="muezza_audit_results.csv",
                mime="text/csv",
                use_container_width=True
            )

        with export_cols[1]:
            json_data = st.session_state.results_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📋 Export JSON",
                data=json_data,
                file_name="muezza_audit_results.json",
                mime="application/json",
                use_container_width=True
            )

        with export_cols[2]:
            st.button("📊 Export PRISMA", use_container_width=True)

        with export_cols[3]:
            st.button("📧 Share Report", use_container_width=True, disabled=True)

    # ========== DRAFTING PREVIEW ==========
    st.markdown("---")
    st.markdown("""
    <div class="section-header">
        <div class="icon">📝</div>
        <h2>Research Report Drafting</h2>
    </div>
    """, unsafe_allow_html=True)

    # Author Information
    author_cols = st.columns([2, 2, 1])

    with author_cols[0]:
        researcher_name = st.text_input(
            "👤 Researcher Name",
            value=st.session_state.researcher_name,
            placeholder="Dr. Ahmad Researcher"
        )
        if researcher_name:
            st.session_state.researcher_name = researcher_name

    with author_cols[1]:
        institution = st.text_input(
            "🏛️ Institution",
            value=st.session_state.institution,
            placeholder="Universitas Indonesia"
        )
        if institution:
            st.session_state.institution = institution

    with author_cols[2]:
        use_ai = st.checkbox("🤖 Use Claude AI", value=True)

    # Generate Report Button
    if st.session_state.slr_state:
        generate_btn = st.button(
            "✨ Generate Full Report",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.report_generating
        )

        if generate_btn:
            st.session_state.report_generating = True

            with st.spinner("Muezza is crafting your research report..."):
                try:
                    add_log_entry("Starting report generation...", "Muezza", "action")

                    # Prepare data
                    scopus_metadata = {
                        "total_results": st.session_state.prisma_stats.identified,
                        "year_range": f"{start_year}-{end_year}",
                    }

                    extraction_table = st.session_state.slr_state.get("synthesis_ready", [])
                    if not extraction_table:
                        extraction_table = st.session_state.slr_state.get("assessed_papers", [])

                    prisma_stats = {
                        "identified": st.session_state.prisma_stats.identified,
                        "duplicates_removed": st.session_state.prisma_stats.duplicates_removed,
                        "screened": st.session_state.prisma_stats.screened,
                        "excluded_screening": st.session_state.prisma_stats.excluded_screening,
                        "sought_retrieval": st.session_state.prisma_stats.sought_retrieval,
                        "not_retrieved": st.session_state.prisma_stats.not_retrieved,
                        "assessed_eligibility": st.session_state.prisma_stats.assessed_eligibility,
                        "excluded_eligibility": st.session_state.prisma_stats.excluded_eligibility,
                        "included_synthesis": st.session_state.prisma_stats.included_synthesis,
                    }

                    papers = st.session_state.slr_state.get("synthesis_ready", [])

                    # Initialize orchestrator
                    api_key = settings.anthropic_api_key if use_ai else None
                    orchestrator = NarrativeOrchestrator(api_key=api_key)

                    # Generate all chapters
                    progress_bar = st.progress(0)

                    chapters = ["Bab 1", "Bab 2", "Bab 3", "Bab 4", "Bab 5"]
                    for i, chapter in enumerate(chapters):
                        add_log_entry(f"Generating {chapter}...", "Muezza", "action")
                        progress_bar.progress((i + 1) / len(chapters))

                        if chapter == "Bab 1":
                            orchestrator.generate_bab_1_pendahuluan(research_question, scopus_metadata)
                        elif chapter == "Bab 2":
                            orchestrator.generate_bab_2_tinjauan_pustaka(research_question, papers)
                        elif chapter == "Bab 3":
                            orchestrator.generate_bab_3_metodologi(prisma_stats)
                        elif chapter == "Bab 4":
                            orchestrator.generate_bab_4_hasil_pembahasan(research_question, extraction_table)
                        elif chapter == "Bab 5":
                            orchestrator.generate_bab_5_kesimpulan(research_question)

                    st.session_state.report_orchestrator = orchestrator
                    st.session_state.full_report_chapters = orchestrator.chapters

                    add_log_entry("Report generation completed!", "Muezza", "success")
                    st.success("✨ Research report generated successfully!")

                except Exception as e:
                    add_log_entry(f"Error: {str(e)}", "Muezza", "error")
                    st.error(f"Error generating report: {str(e)}")
                finally:
                    st.session_state.report_generating = False
                    st.rerun()

    # Display Generated Chapters
    if st.session_state.full_report_chapters:
        chapters = st.session_state.full_report_chapters

        # Chapter tabs
        chapter_titles = {
            "bab_1": "📖 Bab I - Pendahuluan",
            "bab_2": "📚 Bab II - Tinjauan Pustaka",
            "bab_3": "🔬 Bab III - Metodologi",
            "bab_4": "📊 Bab IV - Hasil & Pembahasan",
            "bab_5": "🎯 Bab V - Kesimpulan"
        }

        available_tabs = []
        available_keys = []
        for key, chapter in chapters.items():
            key_str = key.value if hasattr(key, 'value') else str(key)
            tab_name = chapter_titles.get(key_str, key_str)
            available_tabs.append(tab_name)
            available_keys.append(key)

        if available_tabs:
            tabs = st.tabs(available_tabs)

            for tab, key in zip(tabs, available_keys):
                with tab:
                    chapter = chapters[key]
                    st.markdown(f"## {chapter.title}")
                    st.markdown(chapter.content)
                    st.caption(f"📝 Word count: {chapter.word_count}")

        # Download Section
        st.markdown("""
        <div class="download-section">
            <h3>📥 Download Your Research Report</h3>
            <p style="color: var(--slate-400);">Export your complete systematic literature review in your preferred format</p>
        </div>
        """, unsafe_allow_html=True)

        # Get bibliography
        bibliography = []
        if st.session_state.slr_state:
            papers = st.session_state.slr_state.get("synthesis_ready", [])
            for p in papers:
                authors = p.get("authors", ["Unknown"])
                if isinstance(authors, list):
                    author_str = authors[0] if authors else "Unknown"
                else:
                    author_str = str(authors)
                year = p.get("year", "n.d.")
                title = p.get("title", "Untitled")
                source = p.get("source_title", p.get("journal", ""))
                doi = p.get("doi", "")
                ref = f"{author_str} ({year}). {title}. {source}."
                if doi:
                    ref += f" https://doi.org/{doi}"
                bibliography.append(ref)

        st.session_state.generated_bibliography = bibliography

        download_cols = st.columns(4)

        with download_cols[0]:
            md_report = st.session_state.report_orchestrator.export_to_markdown()
            st.download_button(
                label="📄 Markdown",
                data=md_report,
                file_name="muezza_research_report.md",
                mime="text/markdown",
                use_container_width=True
            )

        with download_cols[1]:
            word_btn = st.button("📝 Word (Simple)", use_container_width=True)

            if word_btn:
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                        tmp_path = tmp.name

                    success = st.session_state.report_orchestrator.export_to_word(tmp_path)

                    if success:
                        with open(tmp_path, "rb") as f:
                            word_data = f.read()

                        st.download_button(
                            label="⬇️ Download",
                            data=word_data,
                            file_name="muezza_research_report.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                        os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with download_cols[2]:
            word_pro_btn = st.button("📑 Word (Pro)", use_container_width=True)

            if word_pro_btn:
                try:
                    import tempfile

                    chapters_dict = {}
                    for chapter_type, chapter in st.session_state.full_report_chapters.items():
                        key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                        key_map = {
                            "bab_1": "BAB_I_PENDAHULUAN",
                            "bab_2": "BAB_II_TINJAUAN_PUSTAKA",
                            "bab_3": "BAB_III_METODOLOGI",
                            "bab_4": "BAB_IV_HASIL_PEMBAHASAN",
                            "bab_5": "BAB_V_KESIMPULAN"
                        }
                        formatted_key = key_map.get(key, key)
                        chapters_dict[formatted_key] = chapter.content

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                        tmp_path = tmp.name

                    generator = DocxGenerator(
                        researcher_name=st.session_state.researcher_name,
                        institution=st.session_state.institution
                    )

                    generator.generate_report(
                        chapters=chapters_dict,
                        bibliography=st.session_state.generated_bibliography,
                        filename=tmp_path,
                        title="LAPORAN SYSTEMATIC LITERATURE REVIEW",
                        include_title_page=True
                    )

                    with open(tmp_path, "rb") as f:
                        word_data = f.read()

                    st.download_button(
                        label="⬇️ Download Pro",
                        data=word_data,
                        file_name=f"Muezza_SLR_{st.session_state.researcher_name.replace(' ', '_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    os.unlink(tmp_path)

                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with download_cols[3]:
            json_report = json.dumps({
                "metadata": {
                    "researcher": st.session_state.researcher_name,
                    "institution": st.session_state.institution,
                    "generated_at": datetime.now().isoformat(),
                    "tool": "Muezza AI v2.0"
                },
                "prisma_stats": {
                    "identified": st.session_state.prisma_stats.identified,
                    "included": st.session_state.prisma_stats.included_synthesis,
                },
                "bibliography_count": len(bibliography)
            }, indent=2)

            st.download_button(
                label="📋 Metadata",
                data=json_report,
                file_name="muezza_metadata.json",
                mime="application/json",
                use_container_width=True
            )

    # ========== FOOTER ==========
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: var(--slate-500);">
        <p style="font-size: 1.5rem; margin-bottom: 0.5rem;">🐱</p>
        <p style="font-weight: 600; color: var(--emerald-400);">Muezza AI</p>
        <p style="font-size: 0.85rem;">Faithful Research Companion</p>
        <p style="font-size: 0.75rem; margin-top: 1rem; color: var(--slate-600);">
            Built with LangGraph • ChromaDB • Claude AI • Streamlit
        </p>
        <p style="font-size: 0.7rem; color: var(--slate-600); font-style: italic;">
            "Precision in Research, Integrity in Every Citation"
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
