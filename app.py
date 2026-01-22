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
from agents.narrative_generator import NarrativeGenerator, generate_results_chapter
from agents.narrative_orchestrator import NarrativeOrchestrator
from agents.citation_stitcher import CitationAutoStitcher, CitationStyle
from agents.logic_continuity_agent import LogicContinuityAgent
from agents.forensic_audit_agent import ForensicAuditAgent, VerificationStatus
from agents.docx_generator import DocxGenerator

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

        # Narrative Generation Section
        st.divider()
        st.subheader("📝 Generate Results Chapter (BAB IV)")
        st.markdown("""
        <div style="background: #F0FDF4; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #065F46;">
                <strong>Narrative Generator</strong> akan menyusun draf bab "Hasil dan Pembahasan"
                dalam bahasa Indonesia formal untuk laporan riset Anda.
            </p>
        </div>
        """, unsafe_allow_html=True)

        narrative_cols = st.columns([2, 1])

        with narrative_cols[0]:
            research_title = st.text_input(
                "Judul Penelitian",
                placeholder="Contoh: Systematic Review tentang Penerapan AI dalam Diagnosis Medis",
                help="Judul penelitian akan digunakan dalam konteks narasi"
            )

        with narrative_cols[1]:
            use_llm = st.checkbox(
                "Gunakan Claude AI",
                value=True,
                help="Menggunakan Claude AI untuk narasi lebih natural (memerlukan API key)"
            )

        generate_narrative_btn = st.button(
            "🖊️ Generate Narrative Chapter",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.narrative_generating
        )

        if generate_narrative_btn and st.session_state.slr_state:
            st.session_state.narrative_generating = True

            with st.spinner("Generating narrative chapter..."):
                try:
                    # Prepare SLR results for narrative generation
                    slr_results = {
                        "prisma_stats": {
                            "identified": st.session_state.prisma_stats.identified,
                            "duplicates_removed": st.session_state.prisma_stats.duplicates_removed,
                            "screened": st.session_state.prisma_stats.screened,
                            "excluded_screening": st.session_state.prisma_stats.excluded_screening,
                            "sought_retrieval": st.session_state.prisma_stats.sought_retrieval,
                            "not_retrieved": st.session_state.prisma_stats.not_retrieved,
                            "assessed_eligibility": st.session_state.prisma_stats.assessed_eligibility,
                            "excluded_eligibility": st.session_state.prisma_stats.excluded_eligibility,
                            "included_synthesis": st.session_state.prisma_stats.included_synthesis,
                        },
                        "exclusion_reasons": st.session_state.slr_state.get("exclusion_reasons", {}),
                        "synthesis_ready": st.session_state.slr_state.get("synthesis_ready", []),
                        "assessed_papers": st.session_state.slr_state.get("assessed_papers", []),
                        "research_question": st.session_state.slr_state.get("research_question", research_title or ""),
                    }

                    # Generate narrative using NarrativeGenerator directly
                    async def generate_narratives():
                        anthropic_client = None
                        if use_llm and settings.anthropic_api_key:
                            try:
                                from anthropic import AsyncAnthropic
                                anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                            except ImportError:
                                pass

                        generator = NarrativeGenerator(anthropic_client=anthropic_client)
                        narratives = await generator.generate_full_chapter(slr_results)
                        return generator, narratives

                    generator, narratives = asyncio.run(generate_narratives())
                    st.session_state.generated_narratives = narratives
                    st.session_state.narrative_generator = generator

                    st.success("Narrative chapter generated successfully!")

                except Exception as e:
                    st.error(f"Error generating narrative: {str(e)}")
                finally:
                    st.session_state.narrative_generating = False
                    st.rerun()

        # Display Generated Narratives
        if st.session_state.generated_narratives:
            st.divider()
            st.subheader("📖 Generated Chapter Preview")

            narratives = st.session_state.generated_narratives

            # Section tabs
            section_tabs = st.tabs([
                "4.1 PRISMA Flow",
                "4.2 Karakteristik",
                "4.3 Kualitas",
                "4.4 Sintesis Tematik",
                "4.5 Pembahasan",
                "4.6 Keterbatasan"
            ])

            section_keys = [
                "prisma_flow", "study_characteristics", "quality_assessment",
                "thematic_synthesis", "discussion", "limitations"
            ]

            for tab, key in zip(section_tabs, section_keys):
                with tab:
                    if key in narratives:
                        narrative = narratives[key]
                        st.markdown(f"### {narrative.title}")
                        st.markdown(narrative.content)
                        st.caption(f"Word count: {narrative.word_count}")

            # Export Narrative Options
            st.divider()
            st.subheader("📤 Export Narrative")
            narrative_export_cols = st.columns(3)

            with narrative_export_cols[0]:
                # Export to Markdown
                if st.session_state.narrative_generator:
                    md_content = st.session_state.narrative_generator.export_to_markdown()
                    st.download_button(
                        label="📄 Download Markdown",
                        data=md_content,
                        file_name="bab_iv_hasil_pembahasan.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

            with narrative_export_cols[1]:
                # Export to Word
                word_btn = st.button(
                    "📝 Generate Word Document",
                    use_container_width=True
                )

                if word_btn and st.session_state.narrative_generator:
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                            tmp_path = tmp.name

                        success = st.session_state.narrative_generator.export_to_word(tmp_path)

                        if success:
                            with open(tmp_path, "rb") as f:
                                word_data = f.read()

                            st.download_button(
                                label="⬇️ Download Word File",
                                data=word_data,
                                file_name="bab_iv_hasil_pembahasan.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )
                            os.unlink(tmp_path)
                        else:
                            st.warning("python-docx not installed. Install with: pip install python-docx")
                    except Exception as e:
                        st.error(f"Error creating Word document: {str(e)}")

            with narrative_export_cols[2]:
                # Copy to clipboard button (via text area)
                if st.button("📋 Show Full Text", use_container_width=True):
                    full_text = st.session_state.narrative_generator.export_to_markdown()
                    st.text_area(
                        "Full Narrative (copy from here)",
                        value=full_text,
                        height=400
                    )

        # Full Research Report Section
        st.divider()
        st.subheader("📚 Generate Full Research Report (5 Chapters)")
        st.markdown("""
        <div style="background: #EEF2FF; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #3730A3;">
                <strong>Full Report Generator</strong> akan menyusun laporan penelitian lengkap 5 bab
                dalam bahasa Indonesia formal akademik standar jurnal Q1.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Author Information
        author_cols = st.columns([2, 2])

        with author_cols[0]:
            researcher_name = st.text_input(
                "Nama Peneliti",
                value=st.session_state.researcher_name,
                placeholder="Contoh: M. Sopian Hadianto",
                key="researcher_name_input"
            )
            if researcher_name:
                st.session_state.researcher_name = researcher_name

        with author_cols[1]:
            institution = st.text_input(
                "Institusi",
                value=st.session_state.institution,
                placeholder="Contoh: Universitas Indonesia",
                key="institution_input"
            )
            if institution:
                st.session_state.institution = institution

        report_cols = st.columns([2, 1, 1])

        with report_cols[0]:
            report_title = st.text_input(
                "Judul Penelitian Lengkap",
                value=st.session_state.slr_state.get("research_question", "") if st.session_state.slr_state else "",
                placeholder="Contoh: Systematic Review Penerapan AI dalam Diagnosis Kanker",
                key="report_title_input"
            )

        with report_cols[1]:
            use_llm_report = st.checkbox(
                "Gunakan Claude AI",
                value=True,
                help="Menggunakan Claude AI untuk narasi lebih natural",
                key="use_llm_report"
            )

        with report_cols[2]:
            selected_chapters = st.multiselect(
                "Pilih Bab",
                options=["Bab 1", "Bab 2", "Bab 3", "Bab 4", "Bab 5"],
                default=["Bab 1", "Bab 3", "Bab 4", "Bab 5"],
                help="Pilih bab yang ingin di-generate"
            )

        generate_report_btn = st.button(
            "📝 Generate Full Report",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.report_generating,
            key="generate_report_btn"
        )

        if generate_report_btn and st.session_state.slr_state:
            st.session_state.report_generating = True

            with st.spinner("Generating full research report... This may take a few minutes."):
                try:
                    # Prepare data
                    scopus_metadata = {
                        "total_results": st.session_state.prisma_stats.identified,
                        "year_range": f"{st.session_state.slr_state.get('date_range', (2018, 2024))}",
                        "top_sources": [],
                        "publication_trend": {}
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
                    api_key = settings.anthropic_api_key if use_llm_report else None
                    orchestrator = NarrativeOrchestrator(api_key=api_key)

                    # Generate selected chapters
                    progress_bar = st.progress(0)
                    chapter_map = {
                        "Bab 1": ("generate_bab_1_pendahuluan", [report_title, scopus_metadata]),
                        "Bab 2": ("generate_bab_2_tinjauan_pustaka", [report_title, papers]),
                        "Bab 3": ("generate_bab_3_metodologi", [prisma_stats]),
                        "Bab 4": ("generate_bab_4_hasil_pembahasan", [report_title, extraction_table]),
                        "Bab 5": ("generate_bab_5_kesimpulan", [report_title]),
                    }

                    for i, chapter_name in enumerate(selected_chapters):
                        if chapter_name in chapter_map:
                            method_name, args = chapter_map[chapter_name]
                            method = getattr(orchestrator, method_name)
                            st.text(f"Generating {chapter_name}...")
                            method(*args)
                            progress_bar.progress((i + 1) / len(selected_chapters))

                    st.session_state.report_orchestrator = orchestrator
                    st.session_state.full_report_chapters = orchestrator.chapters

                    st.success(f"Full report generated! {len(orchestrator.chapters)} chapters created.")

                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
                finally:
                    st.session_state.report_generating = False
                    st.rerun()

        # Display Full Report
        if st.session_state.full_report_chapters:
            st.divider()
            st.subheader("📖 Full Report Preview")

            chapters = st.session_state.full_report_chapters

            # Create tabs for each chapter
            chapter_titles = {
                "bab_1": "Bab I Pendahuluan",
                "bab_2": "Bab II Tinjauan Pustaka",
                "bab_3": "Bab III Metodologi",
                "bab_4": "Bab IV Hasil",
                "bab_5": "Bab V Kesimpulan"
            }

            available_tabs = []
            available_keys = []
            for key, chapter in chapters.items():
                tab_name = chapter_titles.get(key.value if hasattr(key, 'value') else str(key), str(key))
                available_tabs.append(tab_name)
                available_keys.append(key)

            if available_tabs:
                report_tabs = st.tabs(available_tabs)

                for tab, key in zip(report_tabs, available_keys):
                    with tab:
                        chapter = chapters[key]
                        st.markdown(f"### {chapter.title}")
                        st.markdown(chapter.content)
                        st.caption(f"Word count: {chapter.word_count}")

            # Export Full Report
            st.divider()
            st.subheader("📤 Export Full Report")

            # Get bibliography for export
            bibliography = []
            if st.session_state.citation_stitcher:
                bibliography = st.session_state.citation_stitcher.get_used_references()
            elif st.session_state.slr_state:
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

            report_export_cols = st.columns(4)

            with report_export_cols[0]:
                if st.session_state.report_orchestrator:
                    md_report = st.session_state.report_orchestrator.export_to_markdown()
                    st.download_button(
                        label="📄 Markdown",
                        data=md_report,
                        file_name="laporan_penelitian_lengkap.md",
                        mime="text/markdown",
                        use_container_width=True,
                        key="download_full_md"
                    )

            with report_export_cols[1]:
                word_report_btn = st.button(
                    "📝 Word (Simple)",
                    use_container_width=True,
                    key="generate_full_word"
                )

                if word_report_btn and st.session_state.report_orchestrator:
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                            tmp_path = tmp.name

                        success = st.session_state.report_orchestrator.export_to_word(tmp_path)

                        if success:
                            with open(tmp_path, "rb") as f:
                                word_data = f.read()

                            st.download_button(
                                label="⬇️ Download Word",
                                data=word_data,
                                file_name="laporan_penelitian_lengkap.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                                key="download_full_docx"
                            )
                            os.unlink(tmp_path)
                        else:
                            st.warning("python-docx not installed")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            with report_export_cols[2]:
                word_pro_btn = st.button(
                    "📑 Word (Pro)",
                    use_container_width=True,
                    key="generate_pro_word",
                    help="Dokumen profesional dengan halaman judul, styling, dan daftar pustaka"
                )

                if word_pro_btn and st.session_state.full_report_chapters:
                    try:
                        import tempfile

                        # Prepare chapters dict for DocxGenerator
                        chapters_dict = {}
                        for chapter_type, chapter in st.session_state.full_report_chapters.items():
                            key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                            # Convert to proper format
                            key_map = {
                                "bab_1": "BAB_I_PENDAHULUAN",
                                "bab_2": "BAB_II_TINJAUAN_PUSTAKA",
                                "bab_3": "BAB_III_METODOLOGI",
                                "bab_4": "BAB_IV_HASIL_PEMBAHASAN",
                                "bab_5": "BAB_V_KESIMPULAN"
                            }
                            formatted_key = key_map.get(key, key)
                            chapters_dict[formatted_key] = chapter.content

                        # Create temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                            tmp_path = tmp.name

                        # Generate with DocxGenerator
                        generator = DocxGenerator(
                            researcher_name=st.session_state.researcher_name,
                            institution=st.session_state.institution
                        )

                        report_title_val = report_title if report_title else "LAPORAN SYSTEMATIC LITERATURE REVIEW"

                        generator.generate_report(
                            chapters=chapters_dict,
                            bibliography=st.session_state.generated_bibliography,
                            filename=tmp_path,
                            title=report_title_val,
                            include_title_page=True
                        )

                        with open(tmp_path, "rb") as f:
                            word_data = f.read()

                        st.download_button(
                            label="⬇️ Download Pro",
                            data=word_data,
                            file_name=f"Laporan_SLR_{st.session_state.researcher_name.replace(' ', '_')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key="download_pro_docx"
                        )
                        os.unlink(tmp_path)
                        st.success("Professional document generated!")

                    except Exception as e:
                        st.error(f"Error creating document: {str(e)}")

            with report_export_cols[3]:
                if st.button("📋 Show Text", use_container_width=True, key="show_full_report"):
                    full_report = st.session_state.report_orchestrator.export_to_markdown()
                    st.text_area(
                        "Full Report (copy from here)",
                        value=full_report,
                        height=500,
                        key="full_report_text"
                    )

            # Bibliography Preview
            if st.session_state.generated_bibliography:
                with st.expander(f"📚 Daftar Pustaka ({len(st.session_state.generated_bibliography)} entri)"):
                    for ref in sorted(st.session_state.generated_bibliography)[:20]:
                        st.markdown(f"- {ref}")

        # Expert Features Section
        st.divider()
        st.subheader("🎓 Expert Features")

        expert_tabs = st.tabs(["📚 Citation Auto-Stitcher", "🔗 Logic Continuity Check", "🔬 Forensic Audit"])

        # Tab 1: Citation Auto-Stitcher
        with expert_tabs[0]:
            st.markdown("""
            <div style="background: #FEF3C7; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <p style="margin: 0; color: #92400E;">
                    <strong>Citation Auto-Stitcher</strong> secara otomatis mencocokkan nama penulis
                    dalam narasi dengan daftar pustaka dari Scopus. Menghilangkan proses manual yang membosankan!
                </p>
            </div>
            """, unsafe_allow_html=True)

            citation_cols = st.columns([2, 1])

            with citation_cols[0]:
                bib_file = st.file_uploader(
                    "Upload Bibliography File",
                    type=["bib", "ris", "csv", "json"],
                    help="Upload file dari Scopus export (.bib, .ris, .csv) atau JSON",
                    key="bib_upload"
                )

            with citation_cols[1]:
                citation_style = st.selectbox(
                    "Citation Style",
                    options=["APA 7th Edition", "Vancouver", "Harvard", "IEEE"],
                    index=0,
                    key="citation_style_select"
                )

            style_map = {
                "APA 7th Edition": CitationStyle.APA7,
                "Vancouver": CitationStyle.VANCOUVER,
                "Harvard": CitationStyle.HARVARD,
                "IEEE": CitationStyle.IEEE
            }

            if bib_file:
                # Save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{bib_file.name.split('.')[-1]}") as tmp:
                    tmp.write(bib_file.getvalue())
                    tmp_path = tmp.name

                # Initialize stitcher
                stitcher = CitationAutoStitcher(citation_style=style_map[citation_style])

                # Load based on file type
                ext = bib_file.name.split('.')[-1].lower()
                if ext == 'bib':
                    count = stitcher.load_bibtex(tmp_path)
                elif ext == 'ris':
                    count = stitcher.load_ris(tmp_path)
                elif ext == 'csv':
                    count = stitcher.load_scopus_csv(tmp_path)
                elif ext == 'json':
                    count = stitcher.load_json(tmp_path)
                else:
                    count = 0

                os.unlink(tmp_path)

                if count > 0:
                    st.success(f"Loaded {count} bibliography entries")
                    st.session_state.citation_stitcher = stitcher
                    st.session_state.bibliography_loaded = True

            # Also load from SLR papers if available
            if st.session_state.slr_state and not st.session_state.bibliography_loaded:
                papers = st.session_state.slr_state.get("synthesis_ready", [])
                if papers:
                    stitcher = CitationAutoStitcher(citation_style=style_map[citation_style])
                    count = stitcher.load_from_papers(papers)
                    if count > 0:
                        st.info(f"Auto-loaded {count} entries from SLR results")
                        st.session_state.citation_stitcher = stitcher

            if st.session_state.citation_stitcher and st.session_state.full_report_chapters:
                if st.button("🔄 Auto-Stitch Citations", type="primary", use_container_width=True, key="stitch_btn"):
                    with st.spinner("Stitching citations..."):
                        stitcher = st.session_state.citation_stitcher
                        stitched_chapters = {}

                        for chapter_type, chapter in st.session_state.full_report_chapters.items():
                            result = stitcher.stitch_citations(chapter.content)
                            chapter.content = result.stitched_text
                            stitched_chapters[chapter_type] = result

                        total_citations = sum(r.citations_added for r in stitched_chapters.values())
                        st.success(f"Added {total_citations} citations across all chapters!")

                        # Show warnings if any
                        all_warnings = []
                        for result in stitched_chapters.values():
                            all_warnings.extend(result.warnings)

                        if all_warnings:
                            with st.expander(f"Warnings ({len(all_warnings)})"):
                                for w in all_warnings[:10]:
                                    st.warning(w)

                        # Generate bibliography
                        bibliography = stitcher.format_bibliography()
                        st.markdown("### Generated Bibliography")
                        st.markdown(bibliography)

        # Tab 2: Logic Continuity Check
        with expert_tabs[1]:
            st.markdown("""
            <div style="background: #DBEAFE; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <p style="margin: 0; color: #1E40AF;">
                    <strong>Logic Continuity Agent</strong> membaca Bab 1-5 untuk memastikan
                    "benang merah" riset tidak terputus. Dijalankan sebelum finalisasi dokumen.
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.full_report_chapters:
                continuity_cols = st.columns([3, 1])

                with continuity_cols[0]:
                    rq_input = st.text_input(
                        "Research Question (optional)",
                        value=st.session_state.slr_state.get("research_question", "") if st.session_state.slr_state else "",
                        placeholder="Pertanyaan penelitian utama...",
                        key="rq_continuity"
                    )

                with continuity_cols[1]:
                    use_llm_check = st.checkbox(
                        "Use Claude AI",
                        value=True,
                        help="Analisis mendalam dengan Claude AI",
                        key="use_llm_continuity"
                    )

                if st.button("🔍 Check Logic Continuity", type="primary", use_container_width=True, key="check_continuity_btn"):
                    with st.spinner("Analyzing report continuity..."):
                        # Prepare chapters dict
                        chapters_dict = {}
                        for chapter_type, chapter in st.session_state.full_report_chapters.items():
                            key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                            chapters_dict[key] = chapter.content

                        # Run analysis
                        api_key = settings.anthropic_api_key if use_llm_check else None
                        agent = LogicContinuityAgent(anthropic_api_key=api_key)
                        report = agent.analyze_report(chapters_dict, rq_input)

                        st.session_state.continuity_report = report

                # Display continuity report
                if st.session_state.continuity_report:
                    report = st.session_state.continuity_report

                    # Overall score with color
                    score_color = "#10B981" if report.overall_score >= 70 else "#F59E0B" if report.overall_score >= 50 else "#EF4444"

                    st.markdown(f"""
                    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, {score_color}22, {score_color}11); border-radius: 12px; margin: 1rem 0;">
                        <h1 style="color: {score_color}; margin: 0; font-size: 3rem;">{report.overall_score:.0f}</h1>
                        <p style="color: #6B7280; margin: 0.5rem 0 0 0;">Skor Kontinuitas Logis</p>
                        <p style="color: {score_color}; font-weight: bold;">{'✅ COHERENT' if report.is_coherent else '⚠️ NEEDS REVISION'}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Score breakdown
                    score_cols = st.columns(5)
                    scores = [
                        ("RQ Alignment", report.research_question_alignment),
                        ("Method-Result", report.methodology_results_match),
                        ("Conclusion", report.conclusion_support_score),
                        ("Terminology", report.terminology_consistency),
                        ("Transitions", report.transition_quality),
                    ]

                    for col, (label, score) in zip(score_cols, scores):
                        with col:
                            st.metric(label, f"{score:.0f}%")

                    # Issues
                    if report.issues:
                        st.markdown("### Issues Found")

                        critical = [i for i in report.issues if i.level.value == "critical"]
                        warnings = [i for i in report.issues if i.level.value == "warning"]
                        suggestions = [i for i in report.issues if i.level.value == "suggestion"]

                        if critical:
                            st.error(f"**{len(critical)} Critical Issues**")
                            for issue in critical:
                                st.markdown(f"- **{issue.chapter}**: {issue.description}")
                                st.caption(f"  💡 {issue.suggestion}")

                        if warnings:
                            st.warning(f"**{len(warnings)} Warnings**")
                            for issue in warnings:
                                st.markdown(f"- **{issue.chapter}**: {issue.description}")
                                st.caption(f"  💡 {issue.suggestion}")

                        if suggestions:
                            with st.expander(f"📝 {len(suggestions)} Suggestions"):
                                for issue in suggestions:
                                    st.markdown(f"- **{issue.chapter}**: {issue.description}")
                                    st.caption(f"  💡 {issue.suggestion}")

                    # Recommendations
                    if report.recommendations:
                        st.markdown("### Recommendations")
                        for rec in report.recommendations:
                            st.markdown(rec)

                    # Download report
                    agent = LogicContinuityAgent()
                    report_text = agent.format_report(report)
                    st.download_button(
                        "📥 Download Continuity Report",
                        data=report_text,
                        file_name="continuity_analysis_report.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="download_continuity"
                    )

            else:
                st.info("Generate full report first to run continuity check.")

        # Tab 3: Forensic Audit
        with expert_tabs[2]:
            st.markdown("""
            <div style="background: #FEE2E2; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <p style="margin: 0; color: #991B1B;">
                    <strong>Forensic Audit Agent</strong> memverifikasi setiap sitasi dalam narasi
                    dengan sumber asli di database. Memastikan setiap klaim didukung bukti!
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.full_report_chapters:
                audit_cols = st.columns([3, 1])

                with audit_cols[0]:
                    audit_chapter = st.selectbox(
                        "Select Chapter to Audit",
                        options=["All Chapters"] + [
                            f"{k.value if hasattr(k, 'value') else k}"
                            for k in st.session_state.full_report_chapters.keys()
                        ],
                        key="audit_chapter_select"
                    )

                with audit_cols[1]:
                    use_llm_audit = st.checkbox(
                        "LLM Verification",
                        value=True,
                        help="Gunakan Claude AI untuk verifikasi mendalam",
                        key="use_llm_audit"
                    )

                if st.button("🔬 Run Forensic Audit", type="primary", use_container_width=True, key="run_audit_btn"):
                    with st.spinner("Auditing citations... This may take a moment."):
                        # Initialize auditor with papers from SLR
                        papers = []
                        if st.session_state.slr_state:
                            papers = st.session_state.slr_state.get("synthesis_ready", [])
                            papers.extend(st.session_state.slr_state.get("assessed_papers", []))

                        api_key = settings.anthropic_api_key if use_llm_audit else None
                        auditor = ForensicAuditAgent(
                            papers_data=papers,
                            anthropic_api_key=api_key
                        )

                        if audit_chapter == "All Chapters":
                            # Audit all chapters
                            all_results = {}
                            for chapter_type, chapter in st.session_state.full_report_chapters.items():
                                key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                                result = auditor.verify_narrative(chapter.content, key)
                                all_results[key] = result

                            # Combine results
                            total_citations = sum(r.total_citations for r in all_results.values())
                            total_verified = sum(r.verified_count for r in all_results.values())
                            total_partial = sum(r.partial_count for r in all_results.values())
                            total_unverified = sum(r.unverified_count for r in all_results.values())
                            total_not_found = sum(r.not_found_count for r in all_results.values())

                            # Create combined evidences
                            all_evidences = []
                            for chapter_id, result in all_results.items():
                                for ev in result.evidences:
                                    ev.notes = f"[{chapter_id}] {ev.notes}"
                                    all_evidences.append(ev)

                            from agents.forensic_audit_agent import AuditResult
                            combined_result = AuditResult(
                                document_id="Full Report",
                                total_citations=total_citations,
                                verified_count=total_verified,
                                partial_count=total_partial,
                                unverified_count=total_unverified,
                                not_found_count=total_not_found,
                                verification_rate=(total_verified + total_partial * 0.5) / total_citations * 100 if total_citations > 0 else 0,
                                evidences=all_evidences,
                                summary=f"Combined audit of {len(all_results)} chapters"
                            )
                            st.session_state.forensic_audit_result = combined_result

                        else:
                            # Audit single chapter
                            for chapter_type, chapter in st.session_state.full_report_chapters.items():
                                key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                                if key in audit_chapter or audit_chapter in key:
                                    result = auditor.verify_narrative(chapter.content, key)
                                    st.session_state.forensic_audit_result = result
                                    break

                        st.success("Forensic audit complete!")

                # Display audit results
                if st.session_state.forensic_audit_result:
                    result = st.session_state.forensic_audit_result

                    # Verification rate with color
                    rate = result.verification_rate
                    rate_color = "#10B981" if rate >= 70 else "#F59E0B" if rate >= 40 else "#EF4444"

                    st.markdown(f"""
                    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, {rate_color}22, {rate_color}11); border-radius: 12px; margin: 1rem 0;">
                        <h1 style="color: {rate_color}; margin: 0; font-size: 3rem;">{rate:.0f}%</h1>
                        <p style="color: #6B7280; margin: 0.5rem 0 0 0;">Tingkat Verifikasi Sitasi</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Statistics
                    stat_cols = st.columns(4)
                    stats = [
                        ("✅ Verified", result.verified_count, "#10B981"),
                        ("🔶 Partial", result.partial_count, "#F59E0B"),
                        ("❌ Unverified", result.unverified_count, "#EF4444"),
                        ("❓ Not Found", result.not_found_count, "#6B7280"),
                    ]

                    for col, (label, count, color) in zip(stat_cols, stats):
                        with col:
                            st.markdown(f"""
                            <div style="text-align: center; padding: 0.5rem; background: {color}11; border-radius: 8px;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{count}</div>
                                <div style="font-size: 0.8rem; color: #6B7280;">{label}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    # Evidence details
                    if result.evidences:
                        st.markdown("### Citation Evidence Details")

                        # Filter options
                        filter_status = st.multiselect(
                            "Filter by Status",
                            options=["verified", "partial", "unverified", "not_found", "needs_review"],
                            default=["unverified", "not_found"],
                            key="audit_filter"
                        )

                        filtered = [e for e in result.evidences if e.status.value in filter_status]

                        for i, evidence in enumerate(filtered[:20], 1):  # Show max 20
                            status_color = {
                                VerificationStatus.VERIFIED: "#10B981",
                                VerificationStatus.PARTIALLY_VERIFIED: "#F59E0B",
                                VerificationStatus.UNVERIFIED: "#EF4444",
                                VerificationStatus.SOURCE_NOT_FOUND: "#6B7280",
                                VerificationStatus.NEEDS_REVIEW: "#8B5CF6"
                            }

                            with st.expander(f"{i}. [{evidence.status.value.upper()}] {evidence.citation_id[:40]}..."):
                                st.markdown(f"**Klaim:** {evidence.original_claim}")
                                st.markdown(f"**Similarity:** {evidence.similarity_score:.0%}")

                                if evidence.source_title:
                                    st.markdown(f"**Sumber:** {evidence.source_title}")

                                if evidence.source_snippet:
                                    st.markdown(f"**Snippet:** {evidence.source_snippet[:200]}...")

                                st.caption(f"Notes: {evidence.notes}")

                    # Download audit report
                    auditor = ForensicAuditAgent()
                    report_text = auditor.format_audit_report(result)
                    st.download_button(
                        "📥 Download Audit Report",
                        data=report_text,
                        file_name="forensic_audit_report.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="download_audit"
                    )

            else:
                st.info("Generate full report first to run forensic audit.")

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
