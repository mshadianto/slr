"""
BiblioAgent AI - Scrounger Agent (Enhanced)
============================================
The Acquisition Specialist: Implements intelligent full-text retrieval
using BiblioHunter's waterfall cascade with Virtual Full-Text synthesis.

Features:
- Multi-source PDF retrieval (S2 → Unpaywall → CORE → ArXiv)
- Enhanced Virtual Full-Text (TL;DR, Citation Contexts, Related Papers)
- Parallel batch processing with progress tracking
- In-memory caching for efficiency
- Quality scoring for retrieved papers
"""

import logging
import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from .state import SLRState, AgentStatus

logger = logging.getLogger(__name__)


class RetrievalSource(Enum):
    """Full-text retrieval sources in priority order."""
    SEMANTIC_SCHOLAR_OA = "semantic_scholar_oa"
    UNPAYWALL = "unpaywall"
    CORE = "core"
    ARXIV = "arxiv"
    VIRTUAL_FULLTEXT = "virtual_fulltext"
    NONE = "none"


@dataclass
class RetrievalResult:
    """Result of attempting to retrieve full text."""
    source: RetrievalSource
    success: bool
    full_text: Optional[str] = None
    pdf_url: Optional[str] = None
    confidence: float = 0.0
    quality_score: float = 0.0
    method: str = "unknown"  # direct, preprint, virtual_fulltext
    tldr: Optional[str] = None
    citation_contexts_count: int = 0
    related_papers: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class ScroungerAgent:
    """
    Scrounger Agent (Acquisition Specialist) - Enhanced with BiblioHunter

    Leverages BiblioHunter for intelligent paper acquisition:
    1. Multi-identifier support (DOI, ArXiv, Title)
    2. Waterfall PDF retrieval across multiple sources
    3. Enhanced Virtual Full-Text with TL;DR and citation contexts
    4. Caching and parallel batch processing
    5. Quality scoring for acquired papers
    """

    def __init__(
        self,
        biblio_hunter=None,
        anthropic_client=None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ):
        """
        Initialize Scrounger Agent.

        Args:
            biblio_hunter: BiblioHunter instance for paper retrieval
            anthropic_client: Anthropic client for LLM-enhanced synthesis
            progress_callback: Optional callback(phase, percent, message)
        """
        self.biblio_hunter = biblio_hunter
        self.anthropic_client = anthropic_client
        self.progress_callback = progress_callback
        self.retrieval_log = []
        self.stats = {
            'total_processed': 0,
            'pdf_acquired': 0,
            'virtual_fulltext': 0,
            'failed': 0,
            'source_distribution': {},
        }

    def _report_progress(self, percent: int, message: str):
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback("acquisition", percent, message)

    async def retrieve_single_paper(self, paper: Dict) -> RetrievalResult:
        """
        Retrieve full text for a single paper using BiblioHunter.

        Args:
            paper: Paper metadata dict (must have doi, title, or arxiv_id)

        Returns:
            RetrievalResult with best available content
        """
        if not self.biblio_hunter:
            return RetrievalResult(
                source=RetrievalSource.NONE,
                success=False,
                method="no_hunter"
            )

        # Determine best identifier to use
        identifier = (
            paper.get("doi") or
            paper.get("arxiv_id") or
            paper.get("title", "")
        )

        if not identifier:
            logger.warning(f"No identifier found for paper: {paper}")
            return RetrievalResult(
                source=RetrievalSource.NONE,
                success=False,
                method="no_identifier"
            )

        try:
            # Use BiblioHunter to fetch paper
            result = self.biblio_hunter.hunt(identifier)

            if result:
                # Map BiblioHunter source to RetrievalSource
                source_map = {
                    'semantic_scholar_oa': RetrievalSource.SEMANTIC_SCHOLAR_OA,
                    'unpaywall': RetrievalSource.UNPAYWALL,
                    'core': RetrievalSource.CORE,
                    'arxiv': RetrievalSource.ARXIV,
                    'virtual_fulltext': RetrievalSource.VIRTUAL_FULLTEXT,
                }
                source = source_map.get(
                    result.full_text_source,
                    RetrievalSource.NONE
                )

                # Determine method
                if result.pdf_url:
                    method = "direct" if result.pdf_source != 'arxiv' else "preprint"
                elif result.is_virtual_fulltext:
                    method = "virtual_fulltext"
                else:
                    method = "metadata_only"

                return RetrievalResult(
                    source=source,
                    success=bool(result.pdf_url or result.full_text),
                    full_text=result.full_text,
                    pdf_url=result.pdf_url,
                    confidence=result.retrieval_confidence,
                    quality_score=result.quality_score,
                    method=method,
                    tldr=result.tldr,
                    citation_contexts_count=result.citation_contexts_count,
                    related_papers=result.related_papers,
                    metadata={
                        's2_paper_id': result.s2_paper_id,
                        'citation_count': result.citation_count,
                        'influential_citations': result.influential_citations,
                        'references_count': result.references_count,
                        'identifier_type': result.identifier_type,
                        'pdf_source': result.pdf_source,
                        'retrieved_at': result.retrieved_at,
                    }
                )

        except Exception as e:
            logger.error(f"BiblioHunter error for {identifier}: {e}")

        return RetrievalResult(
            source=RetrievalSource.NONE,
            success=False,
            method="error"
        )

    async def retrieve_batch(
        self,
        papers: List[Dict],
        max_workers: int = 3
    ) -> List[Dict]:
        """
        Retrieve full text for multiple papers using parallel processing.

        Args:
            papers: List of paper metadata dicts
            max_workers: Number of parallel workers

        Returns:
            List of papers with retrieval results attached
        """
        if not self.biblio_hunter:
            logger.warning("BiblioHunter not initialized")
            return papers

        total = len(papers)
        results = []

        # Extract identifiers
        identifiers = []
        for paper in papers:
            identifier = (
                paper.get("doi") or
                paper.get("arxiv_id") or
                paper.get("title", "")
            )
            identifiers.append(identifier)

        # Define progress callback for BiblioHunter
        def batch_progress(current: int, total: int, message: str):
            percent = int((current / total) * 100) if total > 0 else 0
            self._report_progress(50 + percent // 2, f"Acquiring: {message}")

        # Use BiblioHunter batch processing
        try:
            hunter_results = self.biblio_hunter.batch_hunt(
                identifiers,
                max_workers=max_workers,
                progress_callback=batch_progress
            )

            # Map results back to papers
            result_map = {r.identifier: r for r in hunter_results}

            for i, paper in enumerate(papers):
                identifier = identifiers[i]
                hunter_result = result_map.get(identifier)

                if hunter_result:
                    # Attach results to paper
                    paper["full_text"] = hunter_result.full_text
                    paper["full_text_source"] = hunter_result.full_text_source
                    paper["pdf_url"] = hunter_result.pdf_url
                    paper["retrieval_confidence"] = hunter_result.retrieval_confidence
                    paper["retrieval_quality_score"] = hunter_result.quality_score
                    paper["retrieval_method"] = (
                        "direct" if hunter_result.pdf_url
                        else "virtual_fulltext" if hunter_result.is_virtual_fulltext
                        else "metadata_only"
                    )
                    paper["tldr"] = hunter_result.tldr
                    paper["citation_contexts_count"] = hunter_result.citation_contexts_count
                    paper["related_papers"] = hunter_result.related_papers
                    paper["retrieval_metadata"] = {
                        's2_paper_id': hunter_result.s2_paper_id,
                        'citation_count': hunter_result.citation_count,
                        'influential_citations': hunter_result.influential_citations,
                    }
                    paper["retrieval_success"] = bool(
                        hunter_result.pdf_url or hunter_result.full_text
                    )

                    # Update stats
                    self.stats['total_processed'] += 1
                    source = hunter_result.full_text_source
                    self.stats['source_distribution'][source] = \
                        self.stats['source_distribution'].get(source, 0) + 1

                    if hunter_result.pdf_url:
                        self.stats['pdf_acquired'] += 1
                    elif hunter_result.is_virtual_fulltext:
                        self.stats['virtual_fulltext'] += 1
                    else:
                        self.stats['failed'] += 1
                else:
                    # No result from BiblioHunter
                    paper["full_text"] = None
                    paper["full_text_source"] = "none"
                    paper["pdf_url"] = None
                    paper["retrieval_confidence"] = 0.0
                    paper["retrieval_method"] = "failed"
                    paper["retrieval_success"] = False
                    self.stats['failed'] += 1
                    self.stats['total_processed'] += 1

                results.append(paper)

        except Exception as e:
            logger.error(f"Batch retrieval error: {e}")
            # Return papers with failed status
            for paper in papers:
                paper["retrieval_success"] = False
                paper["full_text_source"] = "error"
                results.append(paper)

        return results

    async def enhance_with_llm(
        self,
        paper: Dict,
        result: RetrievalResult
    ) -> RetrievalResult:
        """
        Enhance Virtual Full-Text using LLM synthesis.

        Args:
            paper: Original paper metadata
            result: Current retrieval result

        Returns:
            Enhanced RetrievalResult with LLM-synthesized content
        """
        if not self.anthropic_client:
            return result

        if not result.is_virtual_fulltext or not result.full_text:
            return result

        try:
            # Build synthesis prompt
            prompt = f"""Analyze this Virtual Full-Text summary and provide additional insights.

PAPER TITLE: {paper.get('title', 'Unknown')}

TL;DR: {result.tldr or 'Not available'}

CURRENT VIRTUAL FULL-TEXT:
{result.full_text[:3000]}

Based on the citation contexts and abstract, provide:
1. RESEARCH SIGNIFICANCE: Why is this paper important? (2-3 sentences)
2. METHODOLOGY INSIGHTS: What can be inferred about the methods? (2-3 sentences)
3. KEY CONTRIBUTIONS: What are the main contributions? (bullet points)
4. LIMITATIONS: What limitations might exist? (1-2 sentences)

Be concise and mark inferences with [INFERRED]."""

            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            # Append LLM synthesis to full text
            llm_synthesis = response.content[0].text
            result.full_text += f"\n\n## LLM-ENHANCED ANALYSIS\n{llm_synthesis}"
            result.confidence = min(0.85, result.confidence + 0.05)
            result.metadata['llm_enhanced'] = True

        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            result.metadata['llm_enhanced'] = False

        return result

    async def execute_acquisition(self, state: SLRState) -> SLRState:
        """
        Execute acquisition phase of SLR pipeline.

        Args:
            state: Current SLR state

        Returns:
            Updated state with acquired papers
        """
        state["agent_status"]["acquisition"] = AgentStatus.ACTIVE.value
        state["current_phase"] = "acquisition"
        state["processing_log"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Scrounger Agent: "
            f"Starting BiblioHunter waterfall retrieval..."
        )

        self._report_progress(0, "Initializing paper acquisition...")

        papers_to_acquire = state.get("screened_papers", [])

        if not papers_to_acquire:
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] No papers to acquire"
            )
            state["agent_status"]["acquisition"] = AgentStatus.COMPLETED.value
            return state

        total = len(papers_to_acquire)
        state["processing_log"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Acquiring {total} papers..."
        )

        self._report_progress(5, f"Processing {total} papers...")

        try:
            # Use batch retrieval for efficiency
            processed_papers = await self.retrieve_batch(
                papers_to_acquire,
                max_workers=3
            )

            # Separate acquired and failed
            acquired = [p for p in processed_papers if p.get("retrieval_success")]
            failed = [p for p in processed_papers if not p.get("retrieval_success")]

            # Optionally enhance top papers with LLM
            if self.anthropic_client and acquired:
                self._report_progress(90, "Enhancing key papers with LLM...")
                # Enhance top 5 Virtual Full-Text papers
                vft_papers = [
                    p for p in acquired
                    if p.get("full_text_source") == "virtual_fulltext"
                ][:5]

                for paper in vft_papers:
                    result = RetrievalResult(
                        source=RetrievalSource.VIRTUAL_FULLTEXT,
                        success=True,
                        full_text=paper.get("full_text"),
                        tldr=paper.get("tldr"),
                        confidence=paper.get("retrieval_confidence", 0.7)
                    )
                    enhanced = await self.enhance_with_llm(paper, result)
                    paper["full_text"] = enhanced.full_text
                    paper["retrieval_confidence"] = enhanced.confidence

            state["acquired_papers"] = acquired
            state["failed_acquisitions"] = failed

            # Update PRISMA stats
            state["prisma_stats"]["sought_retrieval"] = total
            state["prisma_stats"]["not_retrieved"] = len(failed)

            # Get BiblioHunter stats
            hunter_stats = {}
            if self.biblio_hunter:
                hunter_stats = self.biblio_hunter.get_stats()

            state["agent_status"]["acquisition"] = AgentStatus.COMPLETED.value
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Acquisition complete: "
                f"{len(acquired)} acquired, {len(failed)} failed. "
                f"Sources: {self.stats['source_distribution']}"
            )

            # Log detailed stats
            if hunter_stats:
                state["processing_log"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] BiblioHunter stats: "
                    f"Cache hits: {hunter_stats.get('cache_hits', 0)}, "
                    f"API requests: {hunter_stats.get('api_requests', 0)}"
                )

            self._report_progress(100, f"Completed: {len(acquired)} papers acquired")

        except Exception as e:
            state["agent_status"]["acquisition"] = AgentStatus.ERROR.value
            state["errors"].append(f"Acquisition error: {str(e)}")
            logger.error(f"Scrounger agent error: {e}")
            self._report_progress(-1, f"Error: {str(e)}")

        state["updated_at"] = datetime.now().isoformat()
        return state

    def get_retrieval_summary(self) -> Dict:
        """Get summary of retrieval statistics."""
        return {
            **self.stats,
            'success_rate': (
                (self.stats['pdf_acquired'] + self.stats['virtual_fulltext'])
                / max(1, self.stats['total_processed'])
            ),
        }


# LangGraph node function
async def acquisition_node(state: SLRState) -> SLRState:
    """LangGraph node for scrounger/acquisition agent using BiblioHunter."""
    import os
    from api.biblio_hunter import BiblioHunter
    from config import settings

    # Initialize BiblioHunter with all available API keys
    biblio_hunter = BiblioHunter(
        s2_api_key=settings.semantic_scholar_api_key,
        unpaywall_email=settings.unpaywall_email,
        core_api_key=settings.core_api_key,
        enable_cache=True,
        cache_ttl_hours=24,
    )

    # Initialize Anthropic client for LLM enhancement (optional)
    anthropic_client = None
    if settings.anthropic_api_key:
        try:
            from anthropic import AsyncAnthropic
            anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        except ImportError:
            logger.warning("Anthropic client not available for LLM enhancement")

    agent = ScroungerAgent(
        biblio_hunter=biblio_hunter,
        anthropic_client=anthropic_client,
    )

    return await agent.execute_acquisition(state)


# Standalone function for direct usage
async def acquire_papers(
    papers: List[Dict],
    s2_api_key: str = None,
    unpaywall_email: str = None,
    core_api_key: str = None,
    progress_callback: Callable = None
) -> List[Dict]:
    """
    Standalone function to acquire papers using BiblioHunter.

    Args:
        papers: List of paper dicts with doi/arxiv_id/title
        s2_api_key: Semantic Scholar API key
        unpaywall_email: Unpaywall email
        core_api_key: CORE API key
        progress_callback: Optional progress callback

    Returns:
        Papers with retrieval results attached
    """
    from api.biblio_hunter import BiblioHunter

    hunter = BiblioHunter(
        s2_api_key=s2_api_key,
        unpaywall_email=unpaywall_email,
        core_api_key=core_api_key,
        enable_cache=True,
    )

    agent = ScroungerAgent(
        biblio_hunter=hunter,
        progress_callback=progress_callback
    )

    return await agent.retrieve_batch(papers)
