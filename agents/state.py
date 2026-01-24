"""
BiblioAgent AI - State Definitions
==================================
LangGraph state machine state definitions for SLR workflow.
"""

from typing import TypedDict, List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AgentStatus(Enum):
    """Status of each agent in the pipeline."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class Paper:
    """Represents a single academic paper in the SLR pipeline."""
    doi: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    journal: str = ""
    keywords: List[str] = field(default_factory=list)

    # Retrieval metadata
    full_text: Optional[str] = None
    full_text_source: Optional[str] = None
    retrieval_confidence: float = 0.0
    pdf_url: Optional[str] = None

    # Screening metadata
    screening_status: str = "pending"  # pending, included, excluded, uncertain
    title_screen_passed: Optional[bool] = None
    abstract_screen_passed: Optional[bool] = None
    inclusion_reason: Optional[str] = None
    exclusion_reason: Optional[str] = None
    screening_confidence: float = 0.0

    # Quality assessment metadata
    quality_score: Optional[float] = None
    quality_category: Optional[str] = None  # HIGH, MODERATE, LOW, CRITICAL
    quality_flags: List[str] = field(default_factory=list)
    criterion_scores: Dict[str, float] = field(default_factory=dict)

    # Additional metadata
    citations_count: int = 0
    references: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)
    source_database: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "journal": self.journal,
            "keywords": self.keywords,
            "full_text_source": self.full_text_source,
            "retrieval_confidence": self.retrieval_confidence,
            "screening_status": self.screening_status,
            "quality_score": self.quality_score,
            "quality_category": self.quality_category,
        }


@dataclass
class PRISMAStats:
    """PRISMA 2020 flow diagram statistics."""
    # Identification
    identified: int = 0
    duplicates_removed: int = 0

    # Screening
    screened: int = 0
    excluded_screening: int = 0

    # Eligibility
    sought_retrieval: int = 0
    not_retrieved: int = 0
    assessed_eligibility: int = 0
    excluded_eligibility: int = 0

    # Included
    included_synthesis: int = 0

    # Detailed exclusion reasons
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "identified": self.identified,
            "duplicates_removed": self.duplicates_removed,
            "screened": self.screened,
            "excluded_screening": self.excluded_screening,
            "sought_retrieval": self.sought_retrieval,
            "not_retrieved": self.not_retrieved,
            "assessed_eligibility": self.assessed_eligibility,
            "excluded_eligibility": self.excluded_eligibility,
            "included_synthesis": self.included_synthesis,
        }


class SLRState(TypedDict):
    """
    LangGraph state for Systematic Literature Review workflow.

    This state object is passed between agents and maintains
    the complete state of the SLR process.
    """
    # Input configuration
    research_question: str
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    date_range: tuple  # (start_year, end_year)
    languages: List[str]

    # Search phase
    search_queries: List[str]
    raw_papers: List[Dict]
    deduplicated_papers: List[Dict]

    # Screening phase
    title_screened: List[Dict]
    abstract_screened: List[Dict]
    screened_papers: List[Dict]
    excluded_papers: List[Dict]
    uncertain_papers: List[Dict]  # For human review

    # Acquisition phase
    acquired_papers: List[Dict]
    failed_acquisitions: List[Dict]

    # Quality assessment phase
    assessed_papers: List[Dict]
    quality_scores: Dict[str, Dict]  # doi -> quality info

    # Synthesis phase
    synthesis_ready: List[Dict]
    sensitivity_analysis: List[Dict]
    excluded_quality: List[Dict]

    # PRISMA tracking
    prisma_stats: Dict[str, int]

    # Agent status tracking
    agent_status: Dict[str, str]

    # Citation Network Analysis (NEW)
    citation_network: Dict[str, Any]  # Network graph data (nodes, edges)
    citation_contexts_analysis: Dict[str, Dict]  # paper_id -> citation context analysis
    network_metrics: Dict[str, float]  # Centrality, cluster metrics
    key_papers: List[Dict]  # Most influential papers in network
    research_clusters: Dict[int, List[str]]  # cluster_id -> paper_ids

    # Processing metadata
    processing_log: List[str]
    errors: List[str]
    current_phase: str
    started_at: str
    updated_at: str


def create_initial_state(
    research_question: str,
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    date_range: tuple = (2018, 2025),
    languages: List[str] = None
) -> SLRState:
    """Create initial SLR state with default values."""
    if languages is None:
        languages = ["en"]

    return SLRState(
        # Input
        research_question=research_question,
        inclusion_criteria=inclusion_criteria,
        exclusion_criteria=exclusion_criteria,
        date_range=date_range,
        languages=languages,

        # Search
        search_queries=[],
        raw_papers=[],
        deduplicated_papers=[],

        # Screening
        title_screened=[],
        abstract_screened=[],
        screened_papers=[],
        excluded_papers=[],
        uncertain_papers=[],

        # Acquisition
        acquired_papers=[],
        failed_acquisitions=[],

        # Quality
        assessed_papers=[],
        quality_scores={},

        # Synthesis
        synthesis_ready=[],
        sensitivity_analysis=[],
        excluded_quality=[],

        # PRISMA
        prisma_stats=PRISMAStats().to_dict(),

        # Status
        agent_status={
            "search": AgentStatus.PENDING.value,
            "screening": AgentStatus.PENDING.value,
            "acquisition": AgentStatus.PENDING.value,
            "quality": AgentStatus.PENDING.value,
            "citation_network": AgentStatus.PENDING.value,
        },

        # Citation Network Analysis
        citation_network={},
        citation_contexts_analysis={},
        network_metrics={},
        key_papers=[],
        research_clusters={},

        # Metadata
        processing_log=[],
        errors=[],
        current_phase="initialization",
        started_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
