"""
Citation Context Analyzer
=========================
Scite-style citation context analysis to classify citations as
Supporting, Contrasting, or Neutral/Mentioning.

Features:
- Classify citation contexts using NLP patterns and LLM
- Track citation sentiment over time
- Identify controversial vs consensus papers
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CitationType(Enum):
    """Type of citation context."""
    SUPPORTING = "supporting"
    CONTRASTING = "contrasting"
    MENTIONING = "mentioning"
    UNKNOWN = "unknown"


@dataclass
class CitationContext:
    """Represents a single citation context."""
    citing_paper_id: str
    citing_paper_title: str
    citing_paper_year: int
    context_text: str
    citation_type: CitationType = CitationType.UNKNOWN
    confidence: float = 0.0
    section: str = ""  # e.g., introduction, methods, results, discussion

    def to_dict(self) -> Dict[str, Any]:
        return {
            'citing_paper_id': self.citing_paper_id,
            'citing_paper_title': self.citing_paper_title,
            'citing_paper_year': self.citing_paper_year,
            'context_text': self.context_text,
            'citation_type': self.citation_type.value,
            'confidence': self.confidence,
            'section': self.section,
        }


@dataclass
class PaperCitationAnalysis:
    """Complete citation analysis for a paper."""
    paper_id: str
    paper_title: str
    total_citations: int = 0
    supporting_count: int = 0
    contrasting_count: int = 0
    mentioning_count: int = 0
    citation_contexts: List[CitationContext] = field(default_factory=list)
    yearly_breakdown: Dict[int, Dict[str, int]] = field(default_factory=dict)
    controversy_score: float = 0.0  # Higher = more controversial
    consensus_score: float = 0.0  # Higher = more supporting

    def to_dict(self) -> Dict[str, Any]:
        return {
            'paper_id': self.paper_id,
            'paper_title': self.paper_title,
            'total_citations': self.total_citations,
            'supporting_count': self.supporting_count,
            'contrasting_count': self.contrasting_count,
            'mentioning_count': self.mentioning_count,
            'supporting_percentage': round(self.supporting_count / max(1, self.total_citations) * 100, 1),
            'contrasting_percentage': round(self.contrasting_count / max(1, self.total_citations) * 100, 1),
            'mentioning_percentage': round(self.mentioning_count / max(1, self.total_citations) * 100, 1),
            'controversy_score': round(self.controversy_score, 3),
            'consensus_score': round(self.consensus_score, 3),
            'yearly_breakdown': self.yearly_breakdown,
            'contexts': [c.to_dict() for c in self.citation_contexts],
        }


class CitationContextAnalyzer:
    """
    Analyzes citation contexts to classify them as
    Supporting, Contrasting, or Mentioning.
    """

    # Patterns indicating supporting citations
    SUPPORTING_PATTERNS = [
        r'\b(?:confirm|support|validate|corroborate|consistent with|in line with|agree with)\b',
        r'\b(?:demonstrate|show|prove|establish|verify|replicate)\b',
        r'\b(?:as shown by|according to|building on|extending|following)\b',
        r'\b(?:similar(?:ly)?|likewise|correspondingly)\b',
        r'\b(?:found that|reported that|observed that)\b',
        r'\b(?:successfully|effectively|importantly)\b',
    ]

    # Patterns indicating contrasting citations
    CONTRASTING_PATTERNS = [
        r'\b(?:contradict|refute|challenge|dispute|disagree|contrary to)\b',
        r'\b(?:however|although|despite|whereas|while|but|yet)\b',
        r'\b(?:in contrast|on the other hand|unlike|different from)\b',
        r'\b(?:fail(?:ed)?|unable|cannot|could not|did not)\b',
        r'\b(?:incorrect|inaccurate|flawed|problematic|limited)\b',
        r'\b(?:question|debate|controversy|conflicting)\b',
        r'\b(?:overestimate|underestimate|bias|limitation)\b',
    ]

    # Patterns indicating neutral/mentioning citations
    MENTIONING_PATTERNS = [
        r'\b(?:defined by|introduced by|proposed by|developed by)\b',
        r'\b(?:reviewed in|described in|discussed in)\b',
        r'\b(?:see also|for example|e\.g\.|i\.e\.)\b',
        r'\b(?:previous(?:ly)?|prior|earlier|recent(?:ly)?)\b',
    ]

    def __init__(
        self,
        use_llm: bool = False,
        anthropic_api_key: str = None,
        confidence_threshold: float = 0.6
    ):
        """
        Initialize the citation context analyzer.

        Args:
            use_llm: Whether to use LLM for classification (more accurate)
            anthropic_api_key: API key for Claude (if use_llm=True)
            confidence_threshold: Minimum confidence for classification
        """
        self.use_llm = use_llm
        self.anthropic_api_key = anthropic_api_key
        self.confidence_threshold = confidence_threshold

        # Compile regex patterns
        self.supporting_regex = [re.compile(p, re.IGNORECASE) for p in self.SUPPORTING_PATTERNS]
        self.contrasting_regex = [re.compile(p, re.IGNORECASE) for p in self.CONTRASTING_PATTERNS]
        self.mentioning_regex = [re.compile(p, re.IGNORECASE) for p in self.MENTIONING_PATTERNS]

    def classify_context(self, context: str) -> Tuple[CitationType, float]:
        """
        Classify a single citation context.

        Args:
            context: The citation context text

        Returns:
            Tuple of (CitationType, confidence)
        """
        if not context or len(context) < 10:
            return CitationType.UNKNOWN, 0.0

        context_lower = context.lower()

        # Count pattern matches
        supporting_score = sum(1 for p in self.supporting_regex if p.search(context))
        contrasting_score = sum(1 for p in self.contrasting_regex if p.search(context))
        mentioning_score = sum(1 for p in self.mentioning_regex if p.search(context))

        total_matches = supporting_score + contrasting_score + mentioning_score

        if total_matches == 0:
            return CitationType.MENTIONING, 0.3

        # Determine type based on highest score
        max_score = max(supporting_score, contrasting_score, mentioning_score)

        if contrasting_score == max_score and contrasting_score > 0:
            # Check for negation of contrasting words
            negation_pattern = r'\b(?:not|no|never)\s+(?:contradict|refute|challenge)'
            if re.search(negation_pattern, context_lower):
                citation_type = CitationType.SUPPORTING
            else:
                citation_type = CitationType.CONTRASTING
        elif supporting_score == max_score and supporting_score > 0:
            citation_type = CitationType.SUPPORTING
        else:
            citation_type = CitationType.MENTIONING

        # Calculate confidence
        confidence = max_score / (total_matches + 1) * 0.8
        confidence = min(0.9, confidence + 0.2)  # Cap at 0.9 for pattern-based

        return citation_type, confidence

    def classify_context_with_llm(self, context: str) -> Tuple[CitationType, float]:
        """
        Classify citation context using Claude LLM.

        Args:
            context: The citation context text

        Returns:
            Tuple of (CitationType, confidence)
        """
        if not self.anthropic_api_key:
            logger.warning("No API key for LLM classification, falling back to patterns")
            return self.classify_context(context)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.anthropic_api_key)

            prompt = f"""Classify this citation context as one of:
- SUPPORTING: The citing paper agrees with, confirms, or builds on the cited work
- CONTRASTING: The citing paper disagrees with, challenges, or contradicts the cited work
- MENTIONING: The citing paper neutrally mentions or references the cited work

Citation context:
"{context}"

Respond with ONLY one word: SUPPORTING, CONTRASTING, or MENTIONING"""

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )

            result = response.content[0].text.strip().upper()

            if "SUPPORTING" in result:
                return CitationType.SUPPORTING, 0.95
            elif "CONTRASTING" in result:
                return CitationType.CONTRASTING, 0.95
            else:
                return CitationType.MENTIONING, 0.85

        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return self.classify_context(context)

    def analyze_paper_citations(
        self,
        paper_id: str,
        paper_title: str,
        citation_contexts: List[Dict],
        progress_callback: callable = None
    ) -> PaperCitationAnalysis:
        """
        Analyze all citation contexts for a paper.

        Args:
            paper_id: Paper identifier
            paper_title: Paper title
            citation_contexts: List of citation context dicts with:
                - citing_paper_id, citing_paper_title, citing_paper_year
                - context_text
            progress_callback: Optional progress callback

        Returns:
            PaperCitationAnalysis object
        """
        analysis = PaperCitationAnalysis(
            paper_id=paper_id,
            paper_title=paper_title,
            total_citations=len(citation_contexts)
        )

        yearly_data: Dict[int, Dict[str, int]] = defaultdict(
            lambda: {'supporting': 0, 'contrasting': 0, 'mentioning': 0}
        )

        for i, ctx_data in enumerate(citation_contexts):
            context_text = ctx_data.get('context_text', '') or ctx_data.get('context', '')

            # Classify context
            if self.use_llm and self.anthropic_api_key:
                citation_type, confidence = self.classify_context_with_llm(context_text)
            else:
                citation_type, confidence = self.classify_context(context_text)

            # Create context object
            context = CitationContext(
                citing_paper_id=ctx_data.get('citing_paper_id', ''),
                citing_paper_title=ctx_data.get('citing_paper_title', ''),
                citing_paper_year=ctx_data.get('citing_paper_year', 0) or ctx_data.get('year', 0),
                context_text=context_text,
                citation_type=citation_type,
                confidence=confidence,
                section=ctx_data.get('section', '')
            )

            analysis.citation_contexts.append(context)

            # Update counts
            if citation_type == CitationType.SUPPORTING:
                analysis.supporting_count += 1
            elif citation_type == CitationType.CONTRASTING:
                analysis.contrasting_count += 1
            else:
                analysis.mentioning_count += 1

            # Update yearly breakdown
            year = context.citing_paper_year
            if year > 1900:
                yearly_data[year][citation_type.value] += 1

            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(
                    int((i + 1) / len(citation_contexts) * 100),
                    f"Analyzed {i + 1}/{len(citation_contexts)} contexts"
                )

        # Convert yearly data
        analysis.yearly_breakdown = dict(yearly_data)

        # Calculate controversy and consensus scores
        total = analysis.total_citations or 1

        # Controversy: high when there are both supporting and contrasting
        if analysis.supporting_count > 0 and analysis.contrasting_count > 0:
            # Entropy-based controversy
            p_sup = analysis.supporting_count / total
            p_con = analysis.contrasting_count / total
            analysis.controversy_score = 2 * p_sup * p_con / (p_sup + p_con) if (p_sup + p_con) > 0 else 0
        else:
            analysis.controversy_score = 0

        # Consensus: high when mostly supporting
        analysis.consensus_score = analysis.supporting_count / total

        return analysis

    def get_citation_trends(
        self,
        analysis: PaperCitationAnalysis
    ) -> Dict[str, Any]:
        """
        Analyze citation sentiment trends over time.

        Args:
            analysis: PaperCitationAnalysis object

        Returns:
            Dictionary with trend analysis
        """
        if not analysis.yearly_breakdown:
            return {}

        years = sorted(analysis.yearly_breakdown.keys())

        if len(years) < 2:
            return {
                'trend': 'insufficient_data',
                'years': years
            }

        # Calculate moving averages
        support_ratios = []
        for year in years:
            data = analysis.yearly_breakdown[year]
            total = sum(data.values()) or 1
            support_ratios.append(data.get('supporting', 0) / total)

        # Simple trend detection
        first_half = support_ratios[:len(support_ratios) // 2]
        second_half = support_ratios[len(support_ratios) // 2:]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        if second_avg > first_avg + 0.1:
            trend = 'increasing_support'
        elif second_avg < first_avg - 0.1:
            trend = 'decreasing_support'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'early_support_ratio': round(first_avg, 3),
            'recent_support_ratio': round(second_avg, 3),
            'years': years,
            'yearly_support_ratios': [round(r, 3) for r in support_ratios],
        }

    def compare_papers(
        self,
        analyses: List[PaperCitationAnalysis]
    ) -> Dict[str, Any]:
        """
        Compare citation analysis across multiple papers.

        Args:
            analyses: List of PaperCitationAnalysis objects

        Returns:
            Comparison summary
        """
        if not analyses:
            return {}

        comparison = {
            'papers': [],
            'most_supported': None,
            'most_controversial': None,
            'average_support_rate': 0,
        }

        total_support_rate = 0

        for analysis in analyses:
            total = analysis.total_citations or 1
            support_rate = analysis.supporting_count / total

            paper_summary = {
                'paper_id': analysis.paper_id,
                'title': analysis.paper_title[:50],
                'total_citations': analysis.total_citations,
                'support_rate': round(support_rate, 3),
                'controversy_score': analysis.controversy_score,
            }
            comparison['papers'].append(paper_summary)
            total_support_rate += support_rate

        # Find extremes
        comparison['papers'].sort(key=lambda x: x['support_rate'], reverse=True)
        comparison['most_supported'] = comparison['papers'][0] if comparison['papers'] else None

        comparison['papers'].sort(key=lambda x: x['controversy_score'], reverse=True)
        comparison['most_controversial'] = comparison['papers'][0] if comparison['papers'] else None

        comparison['average_support_rate'] = round(total_support_rate / len(analyses), 3)

        # Reset sort
        comparison['papers'].sort(key=lambda x: x['total_citations'], reverse=True)

        return comparison


# Convenience function for integration
async def analyze_citation_contexts(
    paper_id: str,
    paper_title: str,
    citation_contexts: List[Dict],
    use_llm: bool = False,
    anthropic_api_key: str = None
) -> Dict[str, Any]:
    """
    Async function to analyze citation contexts.

    Args:
        paper_id: Paper identifier
        paper_title: Paper title
        citation_contexts: List of citation context dicts
        use_llm: Whether to use LLM for classification
        anthropic_api_key: API key for Claude

    Returns:
        Analysis dictionary
    """
    import asyncio

    analyzer = CitationContextAnalyzer(
        use_llm=use_llm,
        anthropic_api_key=anthropic_api_key
    )

    # Run synchronous analysis in executor
    loop = asyncio.get_event_loop()
    analysis = await loop.run_in_executor(
        None,
        lambda: analyzer.analyze_paper_citations(paper_id, paper_title, citation_contexts)
    )

    return analysis.to_dict()


if __name__ == "__main__":
    # Test the analyzer
    analyzer = CitationContextAnalyzer()

    # Test contexts
    test_contexts = [
        "Our results confirm the findings of Smith et al., demonstrating similar patterns.",
        "However, contrary to previous work by Jones et al., we found no significant effect.",
        "As described in the seminal work by Brown et al., this method involves...",
        "These results support the hypothesis proposed by earlier researchers.",
        "In contrast to the claims made by Lee et al., our analysis shows...",
        "The framework introduced by Wilson et al. provides a useful starting point.",
    ]

    print("Citation Context Classification Test\n" + "=" * 40)

    for context in test_contexts:
        citation_type, confidence = analyzer.classify_context(context)
        print(f"\nContext: {context[:60]}...")
        print(f"Type: {citation_type.value}, Confidence: {confidence:.2f}")

    # Test full analysis
    print("\n" + "=" * 40)
    print("Full Paper Analysis Test\n")

    sample_contexts = [
        {
            'citing_paper_id': 'paper1',
            'citing_paper_title': 'Supporting Paper 1',
            'citing_paper_year': 2020,
            'context_text': 'Our results strongly support the findings of the original study.',
        },
        {
            'citing_paper_id': 'paper2',
            'citing_paper_title': 'Contrasting Paper 1',
            'citing_paper_year': 2021,
            'context_text': 'However, we found contradictory evidence that challenges these claims.',
        },
        {
            'citing_paper_id': 'paper3',
            'citing_paper_title': 'Neutral Paper 1',
            'citing_paper_year': 2022,
            'context_text': 'As mentioned by the authors in their previous work...',
        },
    ]

    analysis = analyzer.analyze_paper_citations(
        paper_id='test_paper',
        paper_title='Test Paper Title',
        citation_contexts=sample_contexts
    )

    print(f"Total citations: {analysis.total_citations}")
    print(f"Supporting: {analysis.supporting_count}")
    print(f"Contrasting: {analysis.contrasting_count}")
    print(f"Mentioning: {analysis.mentioning_count}")
    print(f"Controversy score: {analysis.controversy_score:.3f}")
    print(f"Consensus score: {analysis.consensus_score:.3f}")
