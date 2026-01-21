"""
BiblioAgent AI - Quality Assessment Agent
=========================================
The Evaluator: Implements automated quality assessment using
JBI Critical Appraisal Tools framework.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .state import SLRState, AgentStatus

logger = logging.getLogger(__name__)


class QualityCategory(Enum):
    """Quality score categories."""
    HIGH = "HIGH"           # >= 80: Include in primary synthesis
    MODERATE = "MODERATE"   # 60-79: Include with limitations
    LOW = "LOW"             # 40-59: Sensitivity analysis only
    CRITICAL = "CRITICAL"   # < 40: Exclude from synthesis


@dataclass
class QualityAssessment:
    """Complete quality assessment for a paper."""
    total_score: float
    category: QualityCategory
    criterion_scores: Dict[str, float]
    risk_flags: List[str]
    confidence: float
    assessment_method: str  # full_text, abstract_only, metadata_only
    notes: str = ""


class QualityAgent:
    """
    Quality Assessment Agent (The Evaluator)

    Implements JBI Critical Appraisal Tools framework with weighted criteria:
    - Study Design: 25%
    - Sample Size: 20%
    - Control Group: 15%
    - Randomization: 15%
    - Blinding: 10%
    - Statistical Methods: 10%
    - Confidence Intervals: 5%
    """

    # JBI criteria weights
    CRITERIA_WEIGHTS = {
        "study_design": 0.25,
        "sample_size": 0.20,
        "control_group": 0.15,
        "randomization": 0.15,
        "blinding": 0.10,
        "statistical_methods": 0.10,
        "confidence_intervals": 0.05,
    }

    # Study design hierarchy (higher score = better design)
    STUDY_DESIGN_SCORES = {
        "systematic_review": 1.0,
        "meta_analysis": 1.0,
        "rct": 0.95,
        "cluster_rct": 0.90,
        "quasi_experimental": 0.80,
        "prospective_cohort": 0.75,
        "retrospective_cohort": 0.65,
        "case_control": 0.60,
        "cross_sectional": 0.50,
        "case_series": 0.40,
        "case_report": 0.30,
        "qualitative": 0.70,  # Different paradigm, not necessarily lower
        "unclear": 0.30,
    }

    # Patterns for detecting study characteristics
    STUDY_DESIGN_PATTERNS = {
        "systematic_review": [
            r"systematic\s+review",
            r"systematically\s+reviewed",
        ],
        "meta_analysis": [
            r"meta-analysis",
            r"meta\s+analysis",
            r"pooled\s+analysis",
        ],
        "rct": [
            r"randomized\s+controlled\s+trial",
            r"randomised\s+controlled\s+trial",
            r"\bRCT\b",
            r"randomly\s+assigned",
            r"random\s+allocation",
        ],
        "cluster_rct": [
            r"cluster\s+random",
            r"cluster-random",
        ],
        "quasi_experimental": [
            r"quasi-experiment",
            r"non-randomized\s+trial",
            r"pre-post\s+study",
        ],
        "prospective_cohort": [
            r"prospective\s+cohort",
            r"prospective\s+study",
            r"followed\s+prospectively",
        ],
        "retrospective_cohort": [
            r"retrospective\s+cohort",
            r"retrospective\s+study",
            r"medical\s+records\s+review",
        ],
        "case_control": [
            r"case-control",
            r"case\s+control",
            r"matched\s+controls?",
        ],
        "cross_sectional": [
            r"cross-sectional",
            r"cross\s+sectional",
            r"prevalence\s+study",
            r"survey\s+study",
        ],
        "case_series": [
            r"case\s+series",
            r"consecutive\s+patients",
        ],
        "case_report": [
            r"case\s+report",
            r"single\s+case",
        ],
        "qualitative": [
            r"qualitative\s+study",
            r"interviews?",
            r"focus\s+groups?",
            r"thematic\s+analysis",
            r"grounded\s+theory",
            r"phenomenolog",
        ],
    }

    def __init__(self, anthropic_client=None):
        """Initialize Quality Agent with optional LLM client."""
        self.anthropic_client = anthropic_client
        self.assessment_log = []

    def _detect_study_design(self, text: str) -> Tuple[str, float]:
        """
        Detect study design from text using pattern matching.

        Args:
            text: Combined title, abstract, and/or full text

        Returns:
            Tuple of (design_type, confidence)
        """
        text_lower = text.lower()

        for design, patterns in self.STUDY_DESIGN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score = self.STUDY_DESIGN_SCORES.get(design, 0.3)
                    return design, score

        return "unclear", self.STUDY_DESIGN_SCORES["unclear"]

    def _extract_sample_size(self, text: str) -> Tuple[int, float]:
        """
        Extract sample size from text.

        Args:
            text: Text to search

        Returns:
            Tuple of (sample_size, normalized_score)
        """
        # Patterns for sample size extraction
        patterns = [
            r"n\s*=\s*(\d+)",
            r"(\d+)\s*participants",
            r"(\d+)\s*patients",
            r"(\d+)\s*subjects",
            r"sample\s+(?:size|of)\s*(?:was|:)?\s*(\d+)",
            r"enrolled\s+(\d+)",
            r"included\s+(\d+)",
            r"(\d+)\s*(?:were|was)\s+(?:enrolled|included|recruited)",
        ]

        max_size = 0

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    size = int(match)
                    if size > max_size and size < 1000000:  # Sanity check
                        max_size = size
                except ValueError:
                    continue

        # Normalize sample size score (larger = better, with diminishing returns)
        if max_size == 0:
            return 0, 0.0
        elif max_size < 30:
            return max_size, 0.3
        elif max_size < 100:
            return max_size, 0.5
        elif max_size < 500:
            return max_size, 0.7
        elif max_size < 1000:
            return max_size, 0.85
        else:
            return max_size, 1.0

    def _detect_control_group(self, text: str) -> Tuple[bool, float]:
        """Detect presence of control group."""
        text_lower = text.lower()

        control_patterns = [
            r"control\s+group",
            r"comparison\s+group",
            r"placebo",
            r"compared\s+(?:to|with)",
            r"versus",
            r"\bvs\b",
            r"arm\s*(?:1|2|a|b)",
            r"intervention\s+(?:and|vs)\s+control",
        ]

        for pattern in control_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True, 1.0

        return False, 0.0

    def _detect_randomization(self, text: str) -> Tuple[bool, float]:
        """Detect randomization methodology."""
        text_lower = text.lower()

        # Strong randomization indicators
        strong_patterns = [
            r"computer-generated\s+random",
            r"random\s+number\s+generator",
            r"stratified\s+random",
            r"block\s+random",
            r"permuted\s+block",
        ]

        # Basic randomization indicators
        basic_patterns = [
            r"randomly\s+(?:assigned|allocated|selected)",
            r"random\s+(?:assignment|allocation|selection)",
            r"randomization",
            r"randomised",
            r"randomized",
        ]

        for pattern in strong_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True, 1.0

        for pattern in basic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True, 0.8

        return False, 0.0

    def _detect_blinding(self, text: str) -> Tuple[str, float]:
        """
        Detect blinding methodology.

        Returns:
            Tuple of (blinding_type, score)
        """
        text_lower = text.lower()

        patterns = {
            "double_blind": (r"double[- ]blind", 1.0),
            "triple_blind": (r"triple[- ]blind", 1.0),
            "single_blind": (r"single[- ]blind", 0.7),
            "assessor_blind": (r"(?:assessor|evaluator|outcome)[- ]blind", 0.8),
            "participant_blind": (r"participant[- ]blind", 0.6),
            "open_label": (r"open[- ]label", 0.3),
        }

        for blind_type, (pattern, score) in patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return blind_type, score

        # Check for explicit mention of no blinding
        if re.search(r"(?:not|non)[- ]blind", text_lower):
            return "none", 0.0

        return "unclear", 0.2

    def _detect_statistical_methods(self, text: str) -> Tuple[List[str], float]:
        """Detect statistical methods used."""
        text_lower = text.lower()

        methods_found = []

        statistical_patterns = {
            "regression": r"(?:linear|logistic|cox|poisson)\s+regression",
            "anova": r"\banova\b|analysis\s+of\s+variance",
            "t_test": r"t-test|student'?s?\s+t",
            "chi_square": r"chi-?square|χ²",
            "mann_whitney": r"mann-?whitney|wilcoxon",
            "survival": r"kaplan-?meier|survival\s+analysis",
            "multivariate": r"multivariate|multivariable",
            "intention_to_treat": r"intention[- ]to[- ]treat|ITT",
            "per_protocol": r"per[- ]protocol",
            "power_analysis": r"power\s+(?:analysis|calculation)",
        }

        for method, pattern in statistical_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                methods_found.append(method)

        # Score based on sophistication and number of methods
        if not methods_found:
            return [], 0.2
        elif len(methods_found) == 1:
            return methods_found, 0.5
        elif len(methods_found) <= 3:
            return methods_found, 0.7
        else:
            return methods_found, 1.0

    def _detect_confidence_intervals(self, text: str) -> Tuple[bool, float]:
        """Detect reporting of confidence intervals."""
        text_lower = text.lower()

        ci_patterns = [
            r"confidence\s+interval",
            r"\bCI\b",
            r"95%\s*CI",
            r"\d+%\s*CI",
            r"\[\d+\.?\d*\s*[-–]\s*\d+\.?\d*\]",
        ]

        for pattern in ci_patterns:
            if re.search(pattern, text_lower):
                return True, 1.0

        return False, 0.0

    def assess_paper(self, paper: Dict) -> QualityAssessment:
        """
        Assess quality of a single paper.

        Args:
            paper: Paper dict with title, abstract, and optionally full_text

        Returns:
            QualityAssessment with scores and flags
        """
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        full_text = paper.get("full_text", "")

        # Combine available text
        if full_text:
            text = f"{title}. {abstract}. {full_text}"
            assessment_method = "full_text"
        elif abstract:
            text = f"{title}. {abstract}"
            assessment_method = "abstract_only"
        else:
            text = title
            assessment_method = "metadata_only"

        # Extract each criterion
        design_type, design_score = self._detect_study_design(text)
        sample_size, sample_score = self._extract_sample_size(text)
        has_control, control_score = self._detect_control_group(text)
        has_random, random_score = self._detect_randomization(text)
        blind_type, blind_score = self._detect_blinding(text)
        stat_methods, stat_score = self._detect_statistical_methods(text)
        has_ci, ci_score = self._detect_confidence_intervals(text)

        # Calculate criterion scores
        criterion_scores = {
            "study_design": design_score,
            "sample_size": sample_score,
            "control_group": control_score,
            "randomization": random_score,
            "blinding": blind_score,
            "statistical_methods": stat_score,
            "confidence_intervals": ci_score,
        }

        # Calculate weighted total score
        total_score = sum(
            criterion_scores[k] * v
            for k, v in self.CRITERIA_WEIGHTS.items()
        ) * 100  # Convert to 0-100 scale

        # Identify risk flags
        risk_flags = []
        if design_type == "unclear":
            risk_flags.append("UNCLEAR_DESIGN")
        if sample_size > 0 and sample_size < 30:
            risk_flags.append("SMALL_SAMPLE")
        if not has_control:
            risk_flags.append("NO_CONTROL_GROUP")
        if not has_random and design_type in ["rct", "cluster_rct"]:
            risk_flags.append("RANDOMIZATION_NOT_DESCRIBED")
        if blind_type in ["none", "unclear"]:
            risk_flags.append("NO_BLINDING")
        if not has_ci:
            risk_flags.append("NO_CI_REPORTED")

        # Determine category
        if total_score >= 80:
            category = QualityCategory.HIGH
        elif total_score >= 60:
            category = QualityCategory.MODERATE
        elif total_score >= 40:
            category = QualityCategory.LOW
        else:
            category = QualityCategory.CRITICAL

        # Adjust confidence based on available text
        confidence_multiplier = {
            "full_text": 1.0,
            "abstract_only": 0.8,
            "metadata_only": 0.5,
        }
        confidence = paper.get("retrieval_confidence", 1.0) * confidence_multiplier[assessment_method]

        return QualityAssessment(
            total_score=round(total_score, 2),
            category=category,
            criterion_scores=criterion_scores,
            risk_flags=risk_flags,
            confidence=confidence,
            assessment_method=assessment_method,
            notes=f"Design: {design_type}, Sample: {sample_size}, Stats: {stat_methods}",
        )

    async def execute_quality_assessment(self, state: SLRState) -> SLRState:
        """
        Execute quality assessment phase of SLR pipeline.

        Args:
            state: Current SLR state

        Returns:
            Updated state with quality assessments
        """
        state["agent_status"]["quality"] = AgentStatus.ACTIVE.value
        state["current_phase"] = "quality_assessment"
        state["processing_log"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Evaluator Agent: Starting JBI assessment..."
        )

        papers_to_assess = state["acquired_papers"]
        assessed = []
        synthesis_ready = []
        sensitivity_analysis = []
        excluded_quality = []
        quality_distribution = {"HIGH": 0, "MODERATE": 0, "LOW": 0, "CRITICAL": 0}

        total = len(papers_to_assess)

        try:
            for i, paper in enumerate(papers_to_assess):
                assessment = self.assess_paper(paper)

                # Update paper with assessment
                paper["quality_score"] = assessment.total_score
                paper["quality_category"] = assessment.category.value
                paper["quality_flags"] = assessment.risk_flags
                paper["criterion_scores"] = assessment.criterion_scores
                paper["assessment_confidence"] = assessment.confidence
                paper["assessment_method"] = assessment.assessment_method
                paper["assessment_notes"] = assessment.notes

                assessed.append(paper)
                quality_distribution[assessment.category.value] += 1

                # Categorize for synthesis
                if assessment.category in [QualityCategory.HIGH, QualityCategory.MODERATE]:
                    synthesis_ready.append(paper)
                elif assessment.category == QualityCategory.LOW:
                    sensitivity_analysis.append(paper)
                else:
                    excluded_quality.append(paper)

                # Store in quality_scores dict
                doi = paper.get("doi", f"paper_{i}")
                state["quality_scores"][doi] = {
                    "score": assessment.total_score,
                    "category": assessment.category.value,
                    "flags": assessment.risk_flags,
                    "criterion_scores": assessment.criterion_scores,
                }

                # Log progress every 10%
                if (i + 1) % max(1, total // 10) == 0:
                    progress = ((i + 1) / total) * 100
                    state["processing_log"].append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Quality Assessment: {progress:.0f}% complete"
                    )

            state["assessed_papers"] = assessed
            state["synthesis_ready"] = synthesis_ready
            state["sensitivity_analysis"] = sensitivity_analysis
            state["excluded_quality"] = excluded_quality

            state["prisma_stats"]["assessed_eligibility"] = total
            state["prisma_stats"]["excluded_eligibility"] = len(excluded_quality)
            state["prisma_stats"]["included_synthesis"] = len(synthesis_ready)

            state["agent_status"]["quality"] = AgentStatus.COMPLETED.value
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Quality assessment complete: "
                f"Distribution: {quality_distribution}"
            )

        except Exception as e:
            state["agent_status"]["quality"] = AgentStatus.ERROR.value
            state["errors"].append(f"Quality assessment error: {str(e)}")
            logger.error(f"Quality agent error: {e}")

        state["updated_at"] = datetime.now().isoformat()
        return state


# LangGraph node function
async def quality_node(state: SLRState) -> SLRState:
    """LangGraph node for quality assessment agent."""
    from anthropic import AsyncAnthropic
    from config import settings

    anthropic_client = None
    if settings.anthropic_api_key:
        anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    agent = QualityAgent(anthropic_client=anthropic_client)
    return await agent.execute_quality_assessment(state)
