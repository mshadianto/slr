"""
BiblioAgent AI - Agent Module
=============================
Multi-agent system for systematic literature review automation.
"""

from .state import SLRState, Paper, PRISMAStats, AgentStatus
from .orchestrator import SLROrchestrator
from .search_agent import SearchAgent
from .screening_agent import ScreeningAgent
from .scrounger_agent import ScroungerAgent
from .quality_agent import QualityAgent
from .narrative_generator import NarrativeGenerator, generate_results_chapter
from .narrative_orchestrator import NarrativeOrchestrator, generate_full_research_report
from .citation_stitcher import CitationAutoStitcher, auto_stitch_citations, CitationStyle
from .logic_continuity_agent import LogicContinuityAgent, check_report_continuity
from .forensic_audit_agent import ForensicAuditAgent, audit_narrative
from .docx_generator import DocxGenerator, generate_slr_docx

__all__ = [
    "SLRState",
    "Paper",
    "PRISMAStats",
    "AgentStatus",
    "SLROrchestrator",
    "SearchAgent",
    "ScreeningAgent",
    "ScroungerAgent",
    "QualityAgent",
    "NarrativeGenerator",
    "generate_results_chapter",
    "NarrativeOrchestrator",
    "generate_full_research_report",
    "CitationAutoStitcher",
    "auto_stitch_citations",
    "CitationStyle",
    "LogicContinuityAgent",
    "check_report_continuity",
    "ForensicAuditAgent",
    "audit_narrative",
    "DocxGenerator",
    "generate_slr_docx",
]
