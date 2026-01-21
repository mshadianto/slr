"""
BiblioAgent AI - Screening Agent
================================
The Gatekeeper: Performs automated title and abstract screening using
Claude API with semantic similarity and rule-based filters.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .state import SLRState, AgentStatus

logger = logging.getLogger(__name__)


class ScreeningDecision(Enum):
    """Screening decision outcomes."""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


@dataclass
class ScreeningResult:
    """Result of screening a single paper."""
    decision: ScreeningDecision
    confidence: float
    reason: str
    phase: str  # title or abstract


class ScreeningAgent:
    """
    Screening Agent (The Gatekeeper)

    Four-phase screening process:
    1. Rule-based exclusion (language, date range, document type)
    2. Semantic similarity scoring against inclusion criteria
    3. LLM-based reasoning for borderline cases (confidence < 0.7)
    4. Human-in-the-loop flagging for ambiguous papers
    """

    # Rule-based exclusion patterns
    EXCLUDED_DOC_TYPES = [
        "editorial", "letter to editor", "commentary", "erratum",
        "corrigendum", "retraction", "book review", "news"
    ]

    EXCLUDED_TITLE_PATTERNS = [
        r"^re:\s",  # Reply articles
        r"^comment\s+on",
        r"^response\s+to",
        r"^erratum",
        r"^correction",
        r"^retracted",
    ]

    def __init__(self, anthropic_client=None, embedding_model=None):
        """
        Initialize Screening Agent.

        Args:
            anthropic_client: Anthropic API client for LLM screening
            embedding_model: Sentence transformer model for semantic similarity
        """
        self.anthropic_client = anthropic_client
        self.embedding_model = embedding_model
        self.screening_log = []

    def _rule_based_screen(self, paper: Dict, exclusion_criteria: List[str]) -> Optional[ScreeningResult]:
        """
        Phase 1: Apply rule-based exclusion filters.

        Returns:
            ScreeningResult if excluded, None if passed
        """
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        doc_type = paper.get("document_type", "").lower()
        year = paper.get("year", 0)
        language = paper.get("language", "english").lower()

        # Check document type
        for excluded_type in self.EXCLUDED_DOC_TYPES:
            if excluded_type in doc_type:
                return ScreeningResult(
                    decision=ScreeningDecision.EXCLUDE,
                    confidence=1.0,
                    reason=f"Excluded document type: {doc_type}",
                    phase="rule_based"
                )

        # Check title patterns
        for pattern in self.EXCLUDED_TITLE_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return ScreeningResult(
                    decision=ScreeningDecision.EXCLUDE,
                    confidence=1.0,
                    reason=f"Excluded title pattern: {pattern}",
                    phase="rule_based"
                )

        # Check language (if specified in criteria)
        if language != "english" and "english" in str(exclusion_criteria).lower():
            return ScreeningResult(
                decision=ScreeningDecision.EXCLUDE,
                confidence=1.0,
                reason=f"Non-English language: {language}",
                phase="rule_based"
            )

        # Check user-defined exclusion criteria keywords
        combined_text = f"{title} {abstract}"
        for criterion in exclusion_criteria:
            criterion_lower = criterion.lower()
            # Simple keyword matching for explicit exclusions
            if criterion_lower.startswith("exclude") or criterion_lower.startswith("not"):
                keywords = re.findall(r'\b\w+\b', criterion_lower)
                for keyword in keywords:
                    if len(keyword) > 3 and keyword in combined_text:
                        return ScreeningResult(
                            decision=ScreeningDecision.EXCLUDE,
                            confidence=0.8,
                            reason=f"Matches exclusion criterion: {criterion}",
                            phase="rule_based"
                        )

        return None  # Passed rule-based screening

    def _compute_semantic_similarity(
        self,
        paper: Dict,
        inclusion_criteria: List[str]
    ) -> Tuple[float, str]:
        """
        Phase 2: Compute semantic similarity against inclusion criteria.

        Returns:
            Tuple of (similarity_score, most_relevant_criterion)
        """
        if not self.embedding_model:
            # Fallback to keyword matching if no embedding model
            return self._keyword_similarity(paper, inclusion_criteria)

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        paper_text = f"{title}. {abstract}"

        # Encode paper text
        paper_embedding = self.embedding_model.encode(paper_text)

        # Encode each criterion and compute similarity
        max_similarity = 0.0
        best_criterion = ""

        for criterion in inclusion_criteria:
            criterion_embedding = self.embedding_model.encode(criterion)

            # Cosine similarity
            similarity = self._cosine_similarity(paper_embedding, criterion_embedding)

            if similarity > max_similarity:
                max_similarity = similarity
                best_criterion = criterion

        return max_similarity, best_criterion

    def _keyword_similarity(
        self,
        paper: Dict,
        inclusion_criteria: List[str]
    ) -> Tuple[float, str]:
        """Fallback keyword-based similarity when no embedding model."""
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        combined = f"{title} {abstract}"

        max_score = 0.0
        best_criterion = ""

        for criterion in inclusion_criteria:
            # Extract keywords from criterion
            keywords = re.findall(r'\b\w{4,}\b', criterion.lower())
            if not keywords:
                continue

            # Count matches
            matches = sum(1 for kw in keywords if kw in combined)
            score = matches / len(keywords) if keywords else 0

            if score > max_score:
                max_score = score
                best_criterion = criterion

        return max_score, best_criterion

    @staticmethod
    def _cosine_similarity(vec1, vec2) -> float:
        """Compute cosine similarity between two vectors."""
        import numpy as np
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    async def _llm_screen(
        self,
        paper: Dict,
        inclusion_criteria: List[str],
        exclusion_criteria: List[str],
        research_question: str
    ) -> ScreeningResult:
        """
        Phase 3: LLM-based screening for borderline cases.

        Uses Claude API to make nuanced screening decisions.
        """
        if not self.anthropic_client:
            # Return uncertain if no LLM client
            return ScreeningResult(
                decision=ScreeningDecision.UNCERTAIN,
                confidence=0.5,
                reason="No LLM client available for detailed screening",
                phase="llm"
            )

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        prompt = f"""You are a systematic literature review screening expert. Evaluate whether this paper should be INCLUDED or EXCLUDED based on the criteria below.

RESEARCH QUESTION:
{research_question}

INCLUSION CRITERIA:
{chr(10).join(f"- {c}" for c in inclusion_criteria)}

EXCLUSION CRITERIA:
{chr(10).join(f"- {c}" for c in exclusion_criteria)}

PAPER TO SCREEN:
Title: {title}
Abstract: {abstract}

Provide your decision in the following format:
DECISION: [INCLUDE/EXCLUDE/UNCERTAIN]
CONFIDENCE: [0.0-1.0]
REASON: [Brief explanation]

Be conservative - if uncertain, mark as UNCERTAIN for human review."""

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse response
            decision = ScreeningDecision.UNCERTAIN
            confidence = 0.5
            reason = "Could not parse LLM response"

            if "DECISION:" in result_text:
                decision_match = re.search(r"DECISION:\s*(INCLUDE|EXCLUDE|UNCERTAIN)", result_text, re.IGNORECASE)
                if decision_match:
                    decision_str = decision_match.group(1).upper()
                    decision = ScreeningDecision[decision_str]

            if "CONFIDENCE:" in result_text:
                conf_match = re.search(r"CONFIDENCE:\s*([\d.]+)", result_text)
                if conf_match:
                    confidence = float(conf_match.group(1))

            if "REASON:" in result_text:
                reason_match = re.search(r"REASON:\s*(.+?)(?:\n|$)", result_text, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()

            return ScreeningResult(
                decision=decision,
                confidence=confidence,
                reason=reason,
                phase="llm"
            )

        except Exception as e:
            logger.error(f"LLM screening error: {e}")
            return ScreeningResult(
                decision=ScreeningDecision.UNCERTAIN,
                confidence=0.0,
                reason=f"LLM error: {str(e)}",
                phase="llm"
            )

    async def screen_paper(
        self,
        paper: Dict,
        inclusion_criteria: List[str],
        exclusion_criteria: List[str],
        research_question: str,
        semantic_threshold: float = 0.5,
        confidence_threshold: float = 0.7
    ) -> ScreeningResult:
        """
        Screen a single paper through all phases.

        Args:
            paper: Paper metadata dict
            inclusion_criteria: List of inclusion criteria
            exclusion_criteria: List of exclusion criteria
            research_question: The research question
            semantic_threshold: Minimum semantic similarity for inclusion
            confidence_threshold: Below this, use LLM screening

        Returns:
            Final ScreeningResult
        """
        # Phase 1: Rule-based screening
        rule_result = self._rule_based_screen(paper, exclusion_criteria)
        if rule_result:
            return rule_result

        # Phase 2: Semantic similarity
        similarity, matched_criterion = self._compute_semantic_similarity(
            paper, inclusion_criteria
        )

        if similarity >= confidence_threshold:
            return ScreeningResult(
                decision=ScreeningDecision.INCLUDE,
                confidence=similarity,
                reason=f"High semantic match with: {matched_criterion}",
                phase="semantic"
            )
        elif similarity < semantic_threshold:
            return ScreeningResult(
                decision=ScreeningDecision.EXCLUDE,
                confidence=1 - similarity,
                reason=f"Low semantic relevance (score: {similarity:.2f})",
                phase="semantic"
            )

        # Phase 3: LLM screening for borderline cases
        llm_result = await self._llm_screen(
            paper, inclusion_criteria, exclusion_criteria, research_question
        )

        # Phase 4: Flag for human review if still uncertain
        if llm_result.decision == ScreeningDecision.UNCERTAIN or llm_result.confidence < 0.6:
            return ScreeningResult(
                decision=ScreeningDecision.UNCERTAIN,
                confidence=llm_result.confidence,
                reason=f"Requires human review: {llm_result.reason}",
                phase="human_review"
            )

        return llm_result

    async def execute_screening(self, state: SLRState) -> SLRState:
        """
        Execute screening phase of SLR pipeline.

        Args:
            state: Current SLR state

        Returns:
            Updated state with screening results
        """
        state["agent_status"]["screening"] = AgentStatus.ACTIVE.value
        state["current_phase"] = "screening"
        state["processing_log"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Screening Agent: Starting..."
        )

        papers_to_screen = state["deduplicated_papers"]
        included = []
        excluded = []
        uncertain = []

        total = len(papers_to_screen)

        try:
            for i, paper in enumerate(papers_to_screen):
                result = await self.screen_paper(
                    paper=paper,
                    inclusion_criteria=state["inclusion_criteria"],
                    exclusion_criteria=state["exclusion_criteria"],
                    research_question=state["research_question"]
                )

                paper["screening_status"] = result.decision.value
                paper["screening_confidence"] = result.confidence
                paper["screening_reason"] = result.reason
                paper["screening_phase"] = result.phase

                if result.decision == ScreeningDecision.INCLUDE:
                    included.append(paper)
                elif result.decision == ScreeningDecision.EXCLUDE:
                    excluded.append(paper)
                else:
                    uncertain.append(paper)

                # Log progress every 10%
                if (i + 1) % max(1, total // 10) == 0:
                    progress = ((i + 1) / total) * 100
                    state["processing_log"].append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Screening: {progress:.0f}% complete"
                    )

            state["screened_papers"] = included
            state["excluded_papers"] = excluded
            state["uncertain_papers"] = uncertain

            state["prisma_stats"]["screened"] = total
            state["prisma_stats"]["excluded_screening"] = len(excluded)

            state["agent_status"]["screening"] = AgentStatus.COMPLETED.value
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Screening complete: "
                f"{len(included)} included, {len(excluded)} excluded, {len(uncertain)} uncertain"
            )

        except Exception as e:
            state["agent_status"]["screening"] = AgentStatus.ERROR.value
            state["errors"].append(f"Screening error: {str(e)}")
            logger.error(f"Screening agent error: {e}")

        state["updated_at"] = datetime.now().isoformat()
        return state


# LangGraph node function
async def screening_node(state: SLRState) -> SLRState:
    """LangGraph node for screening agent."""
    from anthropic import AsyncAnthropic
    from config import settings

    anthropic_client = None
    if settings.anthropic_api_key:
        anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Try to load embedding model
    embedding_model = None
    try:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    except ImportError:
        logger.warning("sentence-transformers not installed, using keyword matching")

    agent = ScreeningAgent(
        anthropic_client=anthropic_client,
        embedding_model=embedding_model
    )
    return await agent.execute_screening(state)
