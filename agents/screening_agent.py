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
    2. Semantic similarity scoring against inclusion criteria (batch optimized)
    3. LLM-based reasoning for borderline cases (confidence < 0.7)
    4. Human-in-the-loop flagging for ambiguous papers

    Performance optimizations:
    - Batch embedding computation for papers
    - Pre-computed criterion embeddings (cached)
    - Parallel LLM calls for borderline cases
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

    # Batch size for embedding computation
    EMBEDDING_BATCH_SIZE = 32

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

        # Cache for criterion embeddings (computed once)
        self._criterion_embeddings_cache = None
        self._cached_criteria = None

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

    def _get_criterion_embeddings(self, inclusion_criteria: List[str]):
        """
        Get or compute criterion embeddings (cached).

        Returns:
            Tuple of (embeddings_array, criteria_list)
        """
        if not self.embedding_model:
            return None, inclusion_criteria

        # Check cache
        criteria_key = tuple(inclusion_criteria)
        if self._criterion_embeddings_cache is not None and self._cached_criteria == criteria_key:
            return self._criterion_embeddings_cache, inclusion_criteria

        # Compute and cache
        logger.info(f"Computing embeddings for {len(inclusion_criteria)} criteria...")
        self._criterion_embeddings_cache = self.embedding_model.encode(
            inclusion_criteria,
            batch_size=self.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False
        )
        self._cached_criteria = criteria_key

        return self._criterion_embeddings_cache, inclusion_criteria

    def _batch_compute_paper_embeddings(self, papers: List[Dict]):
        """
        Compute embeddings for multiple papers in batch (much faster).

        Args:
            papers: List of paper dicts

        Returns:
            Array of embeddings (one per paper)
        """
        if not self.embedding_model:
            return None

        # Prepare texts
        texts = []
        for paper in papers:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            texts.append(f"{title}. {abstract}")

        # Batch encode (much faster than one-by-one)
        logger.info(f"Batch encoding {len(texts)} papers...")
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=self.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False
        )

        return embeddings

    def _compute_batch_similarities(
        self,
        paper_embeddings,
        criterion_embeddings,
        criteria: List[str]
    ) -> List[Tuple[float, str]]:
        """
        Compute similarities for all papers against all criteria efficiently.

        Args:
            paper_embeddings: Array of paper embeddings
            criterion_embeddings: Array of criterion embeddings
            criteria: List of criterion texts

        Returns:
            List of (max_similarity, best_criterion) tuples
        """
        import numpy as np

        results = []

        for paper_emb in paper_embeddings:
            # Compute similarity to all criteria at once
            similarities = np.dot(criterion_embeddings, paper_emb) / (
                np.linalg.norm(criterion_embeddings, axis=1) * np.linalg.norm(paper_emb)
            )

            # Find best match
            best_idx = np.argmax(similarities)
            max_sim = float(similarities[best_idx])
            best_criterion = criteria[best_idx]

            results.append((max_sim, best_criterion))

        return results

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
        Execute screening phase of SLR pipeline with batch optimization.

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
            # Phase 1: Rule-based screening (fast, no API calls)
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Phase 1: Rule-based screening..."
            )

            papers_after_rules = []
            for paper in papers_to_screen:
                rule_result = self._rule_based_screen(paper, state["exclusion_criteria"])
                if rule_result:
                    paper["screening_status"] = rule_result.decision.value
                    paper["screening_confidence"] = rule_result.confidence
                    paper["screening_reason"] = rule_result.reason
                    paper["screening_phase"] = rule_result.phase
                    excluded.append(paper)
                else:
                    papers_after_rules.append(paper)

            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Rule-based: {len(excluded)} excluded, "
                f"{len(papers_after_rules)} remaining"
            )

            # Phase 2: Batch semantic similarity (optimized)
            if papers_after_rules and self.embedding_model:
                state["processing_log"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Phase 2: Batch semantic scoring..."
                )

                # Pre-compute criterion embeddings (cached)
                criterion_embeddings, criteria = self._get_criterion_embeddings(
                    state["inclusion_criteria"]
                )

                # Batch compute paper embeddings
                paper_embeddings = self._batch_compute_paper_embeddings(papers_after_rules)

                # Compute all similarities at once
                if paper_embeddings is not None and criterion_embeddings is not None:
                    similarities = self._compute_batch_similarities(
                        paper_embeddings,
                        criterion_embeddings,
                        criteria
                    )

                    # Store similarities for each paper
                    for i, paper in enumerate(papers_after_rules):
                        paper["_semantic_similarity"] = similarities[i][0]
                        paper["_matched_criterion"] = similarities[i][1]

            # Phase 3: Make decisions based on similarity scores
            papers_for_llm = []
            semantic_threshold = 0.5
            confidence_threshold = 0.7

            for paper in papers_after_rules:
                similarity = paper.get("_semantic_similarity", 0.0)
                matched_criterion = paper.get("_matched_criterion", "")

                if similarity >= confidence_threshold:
                    paper["screening_status"] = ScreeningDecision.INCLUDE.value
                    paper["screening_confidence"] = similarity
                    paper["screening_reason"] = f"High semantic match with: {matched_criterion}"
                    paper["screening_phase"] = "semantic"
                    included.append(paper)
                elif similarity < semantic_threshold:
                    paper["screening_status"] = ScreeningDecision.EXCLUDE.value
                    paper["screening_confidence"] = 1 - similarity
                    paper["screening_reason"] = f"Low semantic relevance (score: {similarity:.2f})"
                    paper["screening_phase"] = "semantic"
                    excluded.append(paper)
                else:
                    papers_for_llm.append(paper)

            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Semantic: {len(included)} included, "
                f"{len(papers_for_llm)} need LLM review"
            )

            # Phase 4: LLM screening for borderline cases (sequential to respect rate limits)
            if papers_for_llm:
                state["processing_log"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Phase 3: LLM screening for "
                    f"{len(papers_for_llm)} borderline papers..."
                )

                for i, paper in enumerate(papers_for_llm):
                    llm_result = await self._llm_screen(
                        paper,
                        state["inclusion_criteria"],
                        state["exclusion_criteria"],
                        state["research_question"]
                    )

                    paper["screening_status"] = llm_result.decision.value
                    paper["screening_confidence"] = llm_result.confidence
                    paper["screening_reason"] = llm_result.reason
                    paper["screening_phase"] = llm_result.phase

                    if llm_result.decision == ScreeningDecision.INCLUDE:
                        included.append(paper)
                    elif llm_result.decision == ScreeningDecision.EXCLUDE:
                        excluded.append(paper)
                    else:
                        uncertain.append(paper)

                    # Log progress
                    if (i + 1) % max(1, len(papers_for_llm) // 5) == 0:
                        progress = ((i + 1) / len(papers_for_llm)) * 100
                        state["processing_log"].append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] LLM screening: {progress:.0f}%"
                        )

            # Clean up temporary fields
            for paper in papers_to_screen:
                paper.pop("_semantic_similarity", None)
                paper.pop("_matched_criterion", None)

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
