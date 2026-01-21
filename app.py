"""
BiblioAgent AI - Main Application
=================================
Streamlit dashboard with integrated multi-agent SLR automation.

This is the main entry point that connects the Streamlit UI
with the LangGraph-based agent orchestration system.

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

# Page configuration
st.set_page_config(
    page_title="BiblioAgent AI | SLR Automation",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    :root {
        --primary: #1E3A5F;
        --secondary: #2E8B57;
        --accent: #E67E22;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
    }

    .main-header {
        background: linear-gradient(135deg, #1E3A5F 0%, #2E8B57 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }

    .main-header h1 { margin: 0; font-size: 2.2rem; }
    .main-header p { margin: 0.5rem 0 0 0; opacity: 0.9; }

    .agent-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .agent-card.active { border-left-color: #10B981; background: #ECFDF5; }
    .agent-card.pending { border-left-color: #6B7280; background: #F9FAFB; }
    .agent-card.completed { border-left-color: #3B82F6; background: #EFF6FF; }
    .agent-card.error { border-left-color: #EF4444; background: #FEF2F2; }

    .prisma-metric {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .prisma-metric .number { font-size: 2.5rem; font-weight: bold; color: #1E3A5F; }
    .prisma-metric .label { color: #6B7280; font-size: 0.9rem; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }

    .config-status {
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }
    .config-ok { background: #ECFDF5; color: #065F46; }
    .config-warn { background: #FEF3C7; color: #92400E; }
    .config-error { background: #FEF2F2; color: #991B1B; }
</style>
""", unsafe_allow_html=True)


# Initialize session state
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
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()


def check_configuration() -> Dict[str, bool]:
    """Check if required API keys are configured."""
    return {
        "anthropic": bool(settings.anthropic_api_key),
        "scopus": bool(settings.scopus_api_key),
        "unpaywall": bool(settings.unpaywall_email),
        "semantic_scholar": bool(settings.semantic_scholar_api_key),
    }


def render_config_status():
    """Render configuration status indicator."""
    config = check_configuration()

    if config["anthropic"] and config["scopus"]:
        st.markdown(
            '<div class="config-status config-ok">✅ API keys configured</div>',
            unsafe_allow_html=True
        )
    elif config["anthropic"] or config["scopus"]:
        missing = []
        if not config["anthropic"]:
            missing.append("ANTHROPIC_API_KEY")
        if not config["scopus"]:
            missing.append("SCOPUS_API_KEY")
        st.markdown(
            f'<div class="config-status config-warn">⚠️ Missing: {", ".join(missing)}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="config-status config-error">❌ No API keys configured. Create .env file.</div>',
            unsafe_allow_html=True
        )


def render_prisma_flowchart(stats: PRISMAStats):
    """Render interactive PRISMA 2020 flowchart using Plotly Sankey."""
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=[
                f"Identified\n(n={stats.identified})",
                f"After Dedup\n(n={stats.identified - stats.duplicates_removed})",
                f"Screened\n(n={stats.screened})",
                f"Sought Retrieval\n(n={stats.sought_retrieval})",
                f"Assessed\n(n={stats.assessed_eligibility})",
                f"Included\n(n={stats.included_synthesis})",
                f"Duplicates\n(n={stats.duplicates_removed})",
                f"Excluded\n(n={stats.excluded_screening})",
                f"Not Retrieved\n(n={stats.not_retrieved})",
                f"Excluded\n(n={stats.excluded_eligibility})"
            ],
            color=[
                "#3B82F6", "#60A5FA", "#10B981", "#34D399", "#F59E0B",
                "#22C55E", "#9CA3AF", "#EF4444", "#F87171", "#DC2626"
            ]
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
                "rgba(59, 130, 246, 0.3)", "rgba(16, 185, 129, 0.3)",
                "rgba(52, 211, 153, 0.3)", "rgba(239, 68, 68, 0.2)",
                "rgba(245, 158, 11, 0.3)", "rgba(248, 113, 113, 0.2)",
                "rgba(34, 197, 94, 0.3)", "rgba(220, 38, 38, 0.2)"
            ]
        )
    )])

    fig.update_layout(
        title_text="PRISMA 2020 Flow Diagram",
        font_size=12,
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def render_quality_distribution(distribution: Dict[str, int]):
    """Render quality score distribution chart."""
    colors = {
        "HIGH": "#10B981",
        "MODERATE": "#F59E0B",
        "LOW": "#EF4444",
        "CRITICAL": "#7C3AED"
    }

    fig = go.Figure(data=[
        go.Bar(
            x=list(distribution.keys()),
            y=list(distribution.values()),
            marker_color=[colors.get(k, "#6B7280") for k in distribution.keys()],
            text=list(distribution.values()),
            textposition='auto'
        )
    ])

    fig.update_layout(
        title="Quality Assessment Distribution",
        xaxis_title="Quality Category",
        yaxis_title="Number of Papers",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def render_agent_status_card(agent_name: str, status: AgentStatus, description: str):
    """Render a single agent status card."""
    status_icons = {
        AgentStatus.PENDING: "⏳",
        AgentStatus.ACTIVE: "🔄",
        AgentStatus.COMPLETED: "✅",
        AgentStatus.ERROR: "❌"
    }

    status_colors = {
        AgentStatus.PENDING: "#6B7280",
        AgentStatus.ACTIVE: "#10B981",
        AgentStatus.COMPLETED: "#3B82F6",
        AgentStatus.ERROR: "#EF4444"
    }

    st.markdown(f"""
    <div class="agent-card {status.value}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong>{status_icons[status]} {agent_name}</strong>
            <span style="color: {status_colors[status]}; font-weight: 600;">
                {status.value.upper()}
            </span>
        </div>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #6B7280;">
            {description}
        </p>
    </div>
    """, unsafe_allow_html=True)


def progress_callback(phase: str, percent: int, message: str):
    """Callback for progress updates from the orchestrator."""
    st.session_state.progress = percent
    st.session_state.progress_message = message

    # Update agent status based on phase
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
        # Error
        st.session_state.agent_status[phase] = AgentStatus.ERROR

    # Add to log
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.processing_log.append(f"[{timestamp}] {message}")


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

    try:
        final_state = await orchestrator.run(
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            date_range=date_range
        )

        st.session_state.slr_state = final_state

        # Update PRISMA stats
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

            # Update quality distribution
            synthesis_papers = final_state.get("synthesis_ready", [])
            sensitivity_papers = final_state.get("sensitivity_analysis", [])
            excluded_papers = final_state.get("excluded_quality", [])

            st.session_state.quality_distribution = {
                "HIGH": sum(1 for p in synthesis_papers if p.get("quality_category") == "HIGH"),
                "MODERATE": sum(1 for p in synthesis_papers if p.get("quality_category") == "MODERATE"),
                "LOW": len(sensitivity_papers),
                "CRITICAL": len(excluded_papers),
            }

            # Create results dataframe
            all_assessed = final_state.get("assessed_papers", [])
            if all_assessed:
                st.session_state.results_df = pd.DataFrame([
                    {
                        "DOI": p.get("doi", ""),
                        "Title": p.get("title", "")[:100],
                        "Year": p.get("year", ""),
                        "Source": p.get("full_text_source", ""),
                        "Quality Score": p.get("quality_score", 0),
                        "Category": p.get("quality_category", ""),
                    }
                    for p in all_assessed
                ])

    except Exception as e:
        st.session_state.processing_log.append(f"[ERROR] Pipeline failed: {str(e)}")
    finally:
        st.session_state.is_running = False


def main():
    """Main application entry point."""

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📚 BiblioAgent AI</h1>
        <p>Intelligent Systematic Literature Review Automation | Multi-Agent Pipeline</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")

        render_config_status()

        # File Upload
        st.subheader("📁 Data Input")
        uploaded_file = st.file_uploader(
            "Upload Bibliography",
            type=["bib", "ris", "csv", "xlsx"],
            help="Supported formats: BibTeX, RIS, CSV, Excel"
        )

        if uploaded_file:
            st.success(f"✅ Loaded: {uploaded_file.name}")

        # Research Question
        st.subheader("🎯 Research Question")
        research_question = st.text_area(
            "Enter your research question",
            placeholder="What is the effectiveness of [intervention] on [outcome] in [population]?",
            height=100
        )

        # Criteria Builder
        st.subheader("✅ Inclusion Criteria")
        inclusion_text = st.text_area(
            "Define inclusion criteria (one per line)",
            placeholder="Published 2018-2024\nEnglish language\nPeer-reviewed\nHuman subjects",
            height=100
        )

        st.subheader("❌ Exclusion Criteria")
        exclusion_text = st.text_area(
            "Define exclusion criteria (one per line)",
            placeholder="Conference abstracts\nCase reports\nNon-empirical studies",
            height=100
        )

        st.divider()

        # Date Range
        st.subheader("📅 Date Range")
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input("From", min_value=1900, max_value=2026, value=2018)
        with col2:
            end_year = st.number_input("To", min_value=1900, max_value=2026, value=2025)

        st.divider()

        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button(
                "🚀 Run",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_running
            )
        with col2:
            reset_button = st.button("🔄 Reset", use_container_width=True)

        if reset_button:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()

    # Main Content
    main_col1, main_col2 = st.columns([1, 2])

    # Left Column - Agent Status
    with main_col1:
        st.subheader("⚡ Agent Status")

        agents = [
            ("🔍 Search Agent", "search", "Boolean query generation & Scopus search"),
            ("🔬 Screening Agent", "screening", "Title/Abstract screening with Claude"),
            ("📥 Scrounger Agent", "acquisition", "Waterfall full-text retrieval"),
            ("⚖️ Evaluator Agent", "quality", "JBI quality assessment")
        ]

        for name, key, desc in agents:
            render_agent_status_card(name, st.session_state.agent_status[key], desc)

        st.divider()

        # Processing Log
        st.subheader("📋 Processing Log")
        log_container = st.container(height=200)
        with log_container:
            for log_entry in st.session_state.processing_log[-15:]:
                st.text(log_entry)

    # Right Column - Visualization
    with main_col2:
        st.subheader("📊 PRISMA Metrics")

        metric_cols = st.columns(5)
        stats = st.session_state.prisma_stats
        metrics = [
            ("Identified", stats.identified, "🔵"),
            ("Screened", stats.screened, "🟢"),
            ("Retrieved", stats.sought_retrieval, "🟡"),
            ("Assessed", stats.assessed_eligibility, "🟠"),
            ("Included", stats.included_synthesis, "✅")
        ]

        for col, (label, value, icon) in zip(metric_cols, metrics):
            with col:
                st.metric(label=f"{icon} {label}", value=value)

        # PRISMA Flowchart
        st.plotly_chart(
            render_prisma_flowchart(stats),
            use_container_width=True
        )

        # Quality Distribution
        if sum(st.session_state.quality_distribution.values()) > 0:
            st.plotly_chart(
                render_quality_distribution(st.session_state.quality_distribution),
                use_container_width=True
            )

    # Run Pipeline
    if run_button and research_question:
        inclusion_criteria = [c.strip() for c in inclusion_text.split('\n') if c.strip()]
        exclusion_criteria = [c.strip() for c in exclusion_text.split('\n') if c.strip()]

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Run async pipeline
        with st.spinner("Running SLR pipeline..."):
            asyncio.run(run_slr_pipeline(
                research_question=research_question,
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                date_range=(start_year, end_year)
            ))

        st.success("🎉 Analysis complete!")
        st.balloons()
        st.rerun()

    # Results Table
    if st.session_state.results_df is not None and not st.session_state.results_df.empty:
        st.divider()
        st.subheader("📑 Synthesis Table")

        st.dataframe(st.session_state.results_df, use_container_width=True, height=400)

        # Export Options
        st.subheader("📤 Export Options")
        export_cols = st.columns(4)

        with export_cols[0]:
            csv_data = st.session_state.results_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name="biblioagent_synthesis.csv",
                mime="text/csv",
                use_container_width=True
            )

        with export_cols[1]:
            json_data = st.session_state.results_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📋 Download JSON",
                data=json_data,
                file_name="biblioagent_synthesis.json",
                mime="application/json",
                use_container_width=True
            )

        with export_cols[2]:
            stats = st.session_state.prisma_stats
            prisma_report = f"""PRISMA 2020 Flow Diagram Report
================================
Generated by BiblioAgent AI
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

IDENTIFICATION
- Records identified: {stats.identified}
- Duplicates removed: {stats.duplicates_removed}

SCREENING
- Records screened: {stats.screened}
- Records excluded: {stats.excluded_screening}

RETRIEVAL
- Reports sought: {stats.sought_retrieval}
- Reports not retrieved: {stats.not_retrieved}

INCLUDED
- Reports assessed: {stats.assessed_eligibility}
- Reports excluded: {stats.excluded_eligibility}
- Studies in synthesis: {stats.included_synthesis}

QUALITY DISTRIBUTION
- High Quality: {st.session_state.quality_distribution.get('HIGH', 0)}
- Moderate Quality: {st.session_state.quality_distribution.get('MODERATE', 0)}
- Low Quality: {st.session_state.quality_distribution.get('LOW', 0)}
- Critical Risk: {st.session_state.quality_distribution.get('CRITICAL', 0)}
"""
            st.download_button(
                label="📊 PRISMA Report",
                data=prisma_report,
                file_name="prisma_report.txt",
                mime="text/plain",
                use_container_width=True
            )

        with export_cols[3]:
            st.button("📧 Email Report", use_container_width=True, disabled=True)

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>
            <strong>BiblioAgent AI</strong> | Multi-Agent Systematic Literature Review
            <br>
            Built with LangGraph, ChromaDB, Claude API, and Streamlit
            <br>
            <em>"Diamond-grade insights on a zero-dollar budget"</em>
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
