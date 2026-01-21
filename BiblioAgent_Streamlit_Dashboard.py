"""
BiblioAgent AI - Streamlit Dashboard
=====================================
A Real-Time PRISMA-Compliant Systematic Literature Review Interface
Free-Tier Optimized Edition

Author: BiblioAgent AI Blueprint
Version: 1.0

Usage:
    streamlit run BiblioAgent_Streamlit_Dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="BiblioAgent AI | SLR Automation",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary: #1E3A5F;
        --secondary: #2E8B57;
        --accent: #E67E22;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1E3A5F 0%, #2E8B57 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Agent status cards */
    .agent-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .agent-card.active {
        border-left-color: #10B981;
        background: #ECFDF5;
    }
    
    .agent-card.pending {
        border-left-color: #6B7280;
        background: #F9FAFB;
    }
    
    .agent-card.completed {
        border-left-color: #3B82F6;
        background: #EFF6FF;
    }
    
    /* PRISMA metrics */
    .prisma-metric {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .prisma-metric .number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
    }
    
    .prisma-metric .label {
        color: #6B7280;
        font-size: 0.9rem;
    }
    
    /* Quality badge styling */
    .quality-high { background: #10B981; color: white; }
    .quality-moderate { background: #F59E0B; color: white; }
    .quality-low { background: #EF4444; color: white; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve button styling */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA MODELS
# ============================================================================

class AgentStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class Paper:
    doi: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    journal: str
    keywords: List[str] = field(default_factory=list)
    full_text_source: Optional[str] = None
    quality_score: Optional[float] = None
    quality_category: Optional[str] = None
    screening_status: str = "pending"
    inclusion_reason: Optional[str] = None
    exclusion_reason: Optional[str] = None

@dataclass
class PRISMAStats:
    identified: int = 0
    duplicates_removed: int = 0
    screened: int = 0
    excluded_screening: int = 0
    sought_retrieval: int = 0
    not_retrieved: int = 0
    assessed_eligibility: int = 0
    excluded_eligibility: int = 0
    included_synthesis: int = 0

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "prisma_stats": PRISMAStats(),
        "papers": [],
        "agent_status": {
            "search": AgentStatus.PENDING,
            "screening": AgentStatus.PENDING,
            "acquisition": AgentStatus.PENDING,
            "quality": AgentStatus.PENDING
        },
        "current_phase": "setup",
        "research_question": "",
        "inclusion_criteria": [],
        "exclusion_criteria": [],
        "processing_log": [],
        "quality_distribution": {"HIGH": 0, "MODERATE": 0, "LOW": 0, "CRITICAL": 0}
    }
    
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ============================================================================
# VISUALIZATION COMPONENTS
# ============================================================================

def render_prisma_flowchart(stats: PRISMAStats):
    """Render interactive PRISMA 2020 flowchart using Plotly."""
    
    # Sankey diagram for PRISMA flow
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = [
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
            color = [
                "#3B82F6",  # Identified - Blue
                "#60A5FA",  # After Dedup
                "#10B981",  # Screened - Green
                "#34D399",  # Sought Retrieval
                "#F59E0B",  # Assessed - Yellow
                "#22C55E",  # Included - Success Green
                "#9CA3AF",  # Duplicates - Gray
                "#EF4444",  # Excluded Screening - Red
                "#F87171",  # Not Retrieved
                "#DC2626"   # Excluded Eligibility
            ]
        ),
        link = dict(
            source = [0, 1, 2, 2, 3, 3, 4, 4],
            target = [1, 2, 3, 7, 4, 8, 5, 9],
            value = [
                max(1, stats.identified - stats.duplicates_removed),
                max(1, stats.screened),
                max(1, stats.sought_retrieval),
                max(1, stats.excluded_screening),
                max(1, stats.assessed_eligibility),
                max(1, stats.not_retrieved),
                max(1, stats.included_synthesis),
                max(1, stats.excluded_eligibility)
            ],
            color = [
                "rgba(59, 130, 246, 0.3)",
                "rgba(16, 185, 129, 0.3)",
                "rgba(52, 211, 153, 0.3)",
                "rgba(239, 68, 68, 0.2)",
                "rgba(245, 158, 11, 0.3)",
                "rgba(248, 113, 113, 0.2)",
                "rgba(34, 197, 94, 0.3)",
                "rgba(220, 38, 38, 0.2)"
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

# ============================================================================
# MOCK PIPELINE FUNCTIONS (Replace with actual implementation)
# ============================================================================

def simulate_search_agent(query: str, progress_callback) -> List[Dict]:
    """Simulate search agent execution."""
    # In production, this would call Scopus API
    mock_papers = [
        {"doi": f"10.1000/paper{i}", "title": f"Research Paper {i}", 
         "year": 2023, "abstract": f"Abstract for paper {i}..."}
        for i in range(150)
    ]
    
    for i in range(10):
        progress_callback(i * 10, f"Searching Scopus... {i*10}%")
        time.sleep(0.2)
    
    return mock_papers

def simulate_screening_agent(papers: List[Dict], criteria: List[str], progress_callback) -> Dict:
    """Simulate screening agent execution."""
    included = []
    excluded = []
    
    for i, paper in enumerate(papers):
        progress_callback(int((i / len(papers)) * 100), f"Screening paper {i+1}/{len(papers)}")
        
        # Mock screening logic
        if i % 3 == 0:  # Simulate ~33% exclusion
            excluded.append({**paper, "exclusion_reason": "Does not meet criteria"})
        else:
            included.append(paper)
        
        time.sleep(0.05)
    
    return {"included": included, "excluded": excluded}

def simulate_waterfall_acquisition(papers: List[Dict], progress_callback) -> List[Dict]:
    """Simulate waterfall retrieval process."""
    acquired = []
    
    sources = ["Unpaywall", "CORE", "ArXiv", "Semantic Scholar", "Virtual Full-Text"]
    
    for i, paper in enumerate(papers):
        progress_callback(int((i / len(papers)) * 100), f"Acquiring paper {i+1}/{len(papers)}")
        
        # Simulate waterfall logic
        source_idx = i % len(sources)
        paper["full_text_source"] = sources[source_idx]
        paper["retrieval_confidence"] = 1.0 if source_idx < 4 else 0.7
        acquired.append(paper)
        
        time.sleep(0.05)
    
    return acquired

def simulate_quality_assessment(papers: List[Dict], progress_callback) -> List[Dict]:
    """Simulate quality assessment using JBI framework."""
    import random
    
    assessed = []
    
    for i, paper in enumerate(papers):
        progress_callback(int((i / len(papers)) * 100), f"Assessing paper {i+1}/{len(papers)}")
        
        # Simulate quality scoring
        score = random.randint(30, 95)
        
        if score >= 80:
            category = "HIGH"
        elif score >= 60:
            category = "MODERATE"
        elif score >= 40:
            category = "LOW"
        else:
            category = "CRITICAL"
        
        paper["quality_score"] = score
        paper["quality_category"] = category
        assessed.append(paper)
        
        time.sleep(0.05)
    
    return assessed

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📚 BiblioAgent AI</h1>
        <p>Intelligent Systematic Literature Review Automation | Free-Tier Optimized</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Control Panel
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
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
        
        # Batch Processing Settings
        st.subheader("⚙️ Batch Settings")
        batch_size = st.slider(
            "Papers per batch (Free-tier optimization)",
            min_value=5,
            max_value=50,
            value=20,
            help="Smaller batches stay within Claude Free Tier limits"
        )
        
        st.divider()
        
        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button("🚀 Run", type="primary", use_container_width=True)
        with col2:
            reset_button = st.button("🔄 Reset", use_container_width=True)
        
        if reset_button:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    # Main Content Area
    main_col1, main_col2 = st.columns([1, 2])
    
    # Left Column - Agent Status
    with main_col1:
        st.subheader("⚡ Agent Status")
        
        agents = [
            ("🔍 Search Agent", "search", "Crafting Boolean queries for Scopus"),
            ("🔬 Screening Agent", "screening", "Title/Abstract evaluation"),
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
            for log_entry in st.session_state.processing_log[-10:]:
                st.text(log_entry)
    
    # Right Column - PRISMA Visualization
    with main_col2:
        # PRISMA Metrics Row
        st.subheader("📊 PRISMA Metrics")
        
        metric_cols = st.columns(5)
        metrics = [
            ("Identified", st.session_state.prisma_stats.identified, "🔵"),
            ("Screened", st.session_state.prisma_stats.screened, "🟢"),
            ("Retrieved", st.session_state.prisma_stats.sought_retrieval, "🟡"),
            ("Assessed", st.session_state.prisma_stats.assessed_eligibility, "🟠"),
            ("Included", st.session_state.prisma_stats.included_synthesis, "✅")
        ]
        
        for col, (label, value, icon) in zip(metric_cols, metrics):
            with col:
                st.metric(
                    label=f"{icon} {label}",
                    value=value,
                    delta=None
                )
        
        # PRISMA Flowchart
        st.plotly_chart(
            render_prisma_flowchart(st.session_state.prisma_stats),
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)
            st.session_state.processing_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        
        # Phase 1: Search
        st.session_state.agent_status["search"] = AgentStatus.ACTIVE
        update_progress(5, "Search Agent: Initializing...")
        papers = simulate_search_agent(research_question, update_progress)
        st.session_state.prisma_stats.identified = len(papers)
        st.session_state.prisma_stats.duplicates_removed = int(len(papers) * 0.1)
        st.session_state.agent_status["search"] = AgentStatus.COMPLETED
        
        # Phase 2: Screening
        st.session_state.agent_status["screening"] = AgentStatus.ACTIVE
        update_progress(30, "Screening Agent: Applying criteria...")
        screening_result = simulate_screening_agent(papers, [], update_progress)
        st.session_state.prisma_stats.screened = len(papers) - st.session_state.prisma_stats.duplicates_removed
        st.session_state.prisma_stats.excluded_screening = len(screening_result["excluded"])
        st.session_state.agent_status["screening"] = AgentStatus.COMPLETED
        
        # Phase 3: Acquisition
        st.session_state.agent_status["acquisition"] = AgentStatus.ACTIVE
        update_progress(50, "Scrounger Agent: Waterfall retrieval...")
        acquired = simulate_waterfall_acquisition(screening_result["included"], update_progress)
        st.session_state.prisma_stats.sought_retrieval = len(screening_result["included"])
        st.session_state.prisma_stats.not_retrieved = int(len(acquired) * 0.05)
        st.session_state.agent_status["acquisition"] = AgentStatus.COMPLETED
        
        # Phase 4: Quality Assessment
        st.session_state.agent_status["quality"] = AgentStatus.ACTIVE
        update_progress(75, "Evaluator Agent: JBI assessment...")
        assessed = simulate_quality_assessment(acquired, update_progress)
        st.session_state.prisma_stats.assessed_eligibility = len(assessed)
        
        # Calculate quality distribution
        for paper in assessed:
            cat = paper.get("quality_category", "CRITICAL")
            st.session_state.quality_distribution[cat] += 1
        
        # Calculate included (HIGH + MODERATE only)
        included_count = sum(1 for p in assessed if p.get("quality_category") in ["HIGH", "MODERATE"])
        st.session_state.prisma_stats.included_synthesis = included_count
        st.session_state.prisma_stats.excluded_eligibility = len(assessed) - included_count
        
        st.session_state.agent_status["quality"] = AgentStatus.COMPLETED
        
        update_progress(100, "✅ Analysis complete!")
        st.success("🎉 Systematic review analysis completed successfully!")
        st.balloons()
        
        st.rerun()
    
    # Results Table (if papers exist)
    if st.session_state.prisma_stats.included_synthesis > 0:
        st.divider()
        st.subheader("📑 Synthesis Table")
        
        # Create sample results DataFrame
        results_data = {
            "DOI": [f"10.1000/paper{i}" for i in range(min(10, st.session_state.prisma_stats.included_synthesis))],
            "Title": [f"Research Study on Topic {i+1}" for i in range(min(10, st.session_state.prisma_stats.included_synthesis))],
            "Year": [2023 - (i % 5) for i in range(min(10, st.session_state.prisma_stats.included_synthesis))],
            "Source": ["Unpaywall", "CORE", "ArXiv", "Semantic Scholar", "Virtual Full-Text"] * 2,
            "Quality Score": [85, 72, 68, 91, 55, 78, 82, 65, 88, 71][:min(10, st.session_state.prisma_stats.included_synthesis)],
            "Category": ["HIGH", "MODERATE", "MODERATE", "HIGH", "LOW", "MODERATE", "HIGH", "MODERATE", "HIGH", "MODERATE"][:min(10, st.session_state.prisma_stats.included_synthesis)]
        }
        
        df = pd.DataFrame(results_data)
        
        # Display dataframe
        st.dataframe(df, use_container_width=True, height=400)
        
        # Export Options
        st.subheader("📤 Export Options")
        export_cols = st.columns(4)
        
        with export_cols[0]:
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name="biblioagent_synthesis.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with export_cols[1]:
            json_data = df.to_json(orient="records", indent=2)
            st.download_button(
                label="📋 Download JSON",
                data=json_data,
                file_name="biblioagent_synthesis.json",
                mime="application/json",
                use_container_width=True
            )
        
        with export_cols[2]:
            # PRISMA report placeholder
            prisma_report = f"""
PRISMA 2020 Flow Diagram Report
================================
Generated by BiblioAgent AI

IDENTIFICATION
- Records identified: {st.session_state.prisma_stats.identified}
- Duplicates removed: {st.session_state.prisma_stats.duplicates_removed}

SCREENING
- Records screened: {st.session_state.prisma_stats.screened}
- Records excluded: {st.session_state.prisma_stats.excluded_screening}

RETRIEVAL
- Reports sought: {st.session_state.prisma_stats.sought_retrieval}
- Reports not retrieved: {st.session_state.prisma_stats.not_retrieved}

INCLUDED
- Reports assessed: {st.session_state.prisma_stats.assessed_eligibility}
- Reports excluded: {st.session_state.prisma_stats.excluded_eligibility}
- Studies in synthesis: {st.session_state.prisma_stats.included_synthesis}

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
            st.button("📧 Email Report", use_container_width=True, disabled=True, help="Coming soon")

    # ============================================================================
    # ADDITIONAL TABS FOR DETAILED VIEWS
    # ============================================================================

    st.divider()
    
    # Detailed Analysis Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Search Details", 
        "🔬 Screening Log", 
        "📥 Acquisition Sources",
        "⚖️ Quality Details"
    ])
    
    with tab1:
        st.markdown("""
        ### Search Agent Configuration
        
        **Boolean Query Generator** uses the following strategy:
        
        1. **PICO/SPIDER Framework Parsing**: Extracts Population, Intervention, Comparison, Outcome elements
        2. **Synonym Expansion**: Uses MeSH terms and domain thesauri
        3. **Field Targeting**: Applies TITLE-ABS-KEY, AUTH, AFFIL operators
        4. **Iterative Refinement**: Adjusts based on result counts
        
        ```
        Example Generated Query:
        TITLE-ABS-KEY("machine learning" OR "artificial intelligence") 
        AND TITLE-ABS-KEY("systematic review" OR "meta-analysis")
        AND PUBYEAR > 2018
        ```
        """)
    
    with tab2:
        st.markdown("""
        ### Screening Agent Log
        
        **Two-Phase Screening Process:**
        
        | Phase | Method | Threshold |
        |-------|--------|-----------|
        | Title Screening | Rule-based + Semantic | Confidence > 0.5 |
        | Abstract Screening | LLM Reasoning | Confidence > 0.7 |
        
        **Exclusion Reasons Tracked:**
        - Language mismatch
        - Date range violation
        - Document type exclusion
        - Topic irrelevance
        - Population mismatch
        """)
    
    with tab3:
        st.markdown("""
        ### Waterfall Retrieval Sources
        
        | Priority | Source | Success Rate | Confidence |
        |----------|--------|--------------|------------|
        | 1 | Unpaywall (OA) | ~35% | 1.0 |
        | 2 | CORE Aggregator | ~25% | 1.0 |
        | 3 | ArXiv Preprints | ~15% | 1.0 |
        | 4 | Semantic Scholar | ~10% | 1.0 |
        | 5 | Virtual Full-Text | ~15% | 0.7 |
        
        **Virtual Full-Text Methodology:**
        - Citation Context Analysis from OA citing papers
        - Semantic Abstract Expansion using LLM
        - Confidence clearly marked for synthesis decisions
        """)
    
    with tab4:
        st.markdown("""
        ### JBI Critical Appraisal Framework
        
        **Automated Extraction Targets:**
        
        | Criterion | Weight | Extraction Method |
        |-----------|--------|-------------------|
        | Study Design | 25% | Pattern + LLM |
        | Sample Size | 20% | Numeric Extraction |
        | Control Group | 15% | Keyword Detection |
        | Randomization | 15% | Context Analysis |
        | Blinding | 10% | Pattern Matching |
        | Statistics | 10% | Method Extraction |
        | CI Reported | 5% | Numeric Detection |
        
        **Quality Categories:**
        - 🟢 **HIGH** (≥80): Include in primary synthesis
        - 🟡 **MODERATE** (60-79): Include with limitations noted
        - 🟠 **LOW** (40-59): Sensitivity analysis only
        - 🔴 **CRITICAL** (<40): Exclude, document reason
        """)

    # ============================================================================
    # FOOTER
    # ============================================================================

    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>
            <strong>BiblioAgent AI</strong> | Free-Tier Optimized Systematic Literature Review
            <br>
            Built with ❤️ using LangGraph, ChromaDB, and Streamlit
            <br>
            <em>"Diamond-grade insights on a zero-dollar budget"</em>
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
