"""
BiblioAgent AI - Search Agent
=============================
The Query Architect: Transforms research questions into Boolean search queries
and executes searches against Scopus API.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .state import SLRState, Paper, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class PICOElements:
    """PICO/SPIDER framework elements extracted from research question."""
    population: List[str]
    intervention: List[str]
    comparison: List[str]
    outcome: List[str]
    study_type: List[str]


class SearchAgent:
    """
    Search Agent (The Query Architect)

    Responsibilities:
    - Parse PICO/SPIDER framework elements from research question
    - Generate Boolean search strings with appropriate operators
    - Apply field-specific search (TITLE-ABS-KEY, AUTH, AFFIL)
    - Implement search expansion using MeSH terms and synonyms
    """

    # Common MeSH term mappings for query expansion
    MESH_SYNONYMS = {
        "machine learning": ["artificial intelligence", "deep learning", "neural network", "ML", "AI"],
        "systematic review": ["meta-analysis", "literature review", "evidence synthesis"],
        "randomized controlled trial": ["RCT", "randomised controlled trial", "clinical trial"],
        "effectiveness": ["efficacy", "effect", "impact", "outcome"],
        "treatment": ["therapy", "intervention", "management"],
        "diagnosis": ["diagnostic", "detection", "screening"],
        "prevention": ["preventive", "prophylaxis", "prophylactic"],
        "children": ["pediatric", "paediatric", "child", "adolescent", "youth"],
        "elderly": ["older adults", "geriatric", "aged", "senior"],
        "mortality": ["death", "survival", "fatality"],
        "morbidity": ["disease", "illness", "complication"],
    }

    # Study type keywords
    STUDY_TYPES = {
        "rct": ["randomized controlled trial", "randomised controlled trial", "RCT"],
        "cohort": ["cohort study", "prospective study", "longitudinal study"],
        "case_control": ["case-control", "case control", "matched study"],
        "cross_sectional": ["cross-sectional", "cross sectional", "prevalence study"],
        "systematic_review": ["systematic review", "meta-analysis", "evidence synthesis"],
        "qualitative": ["qualitative study", "interview", "focus group", "thematic analysis"],
    }

    def __init__(self, scopus_client=None):
        """Initialize Search Agent with optional Scopus client."""
        self.scopus_client = scopus_client
        self.generated_queries = []

    def parse_pico(self, research_question: str) -> PICOElements:
        """
        Extract PICO/SPIDER elements from a research question.

        Args:
            research_question: Natural language research question

        Returns:
            PICOElements with extracted components
        """
        # Common patterns for PICO extraction
        patterns = {
            "population": [
                r"(?:in|among|for)\s+([^,]+?)(?:\s+(?:with|who|that))",
                r"(?:patients?|participants?|subjects?|individuals?)\s+(?:with\s+)?([^,]+)",
                r"(?:adults?|children|elderly|women|men)\s+(?:with\s+)?([^,]+)",
            ],
            "intervention": [
                r"(?:effect(?:iveness)?|impact|efficacy)\s+of\s+([^,]+?)(?:\s+(?:on|in|for))",
                r"(?:using|with|receiving)\s+([^,]+?)(?:\s+(?:on|for|compared))",
                r"([^,]+?)\s+(?:treatment|therapy|intervention)",
            ],
            "comparison": [
                r"compared\s+(?:to|with)\s+([^,]+)",
                r"versus\s+([^,]+)",
                r"vs\.?\s+([^,]+)",
            ],
            "outcome": [
                r"(?:on|for)\s+([^,]+?)(?:\s+(?:in|among|outcomes?))?$",
                r"(?:improve|reduce|increase|decrease)\s+([^,]+)",
                r"(?:effect on|impact on)\s+([^,]+)",
            ],
        }

        extracted = {
            "population": [],
            "intervention": [],
            "comparison": [],
            "outcome": [],
            "study_type": [],
        }

        question_lower = research_question.lower()

        # Extract each PICO element
        for element, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, question_lower, re.IGNORECASE)
                for match in matches:
                    cleaned = match.strip().strip("?.,")
                    if cleaned and len(cleaned) > 2:
                        extracted[element].append(cleaned)

        # Detect study type
        for study_type, keywords in self.STUDY_TYPES.items():
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    extracted["study_type"].append(study_type)
                    break

        return PICOElements(
            population=list(set(extracted["population"])),
            intervention=list(set(extracted["intervention"])),
            comparison=list(set(extracted["comparison"])),
            outcome=list(set(extracted["outcome"])),
            study_type=list(set(extracted["study_type"])),
        )

    def expand_terms(self, terms: List[str]) -> List[str]:
        """Expand search terms with synonyms and MeSH terms."""
        expanded = set(terms)

        for term in terms:
            term_lower = term.lower()
            # Check for exact matches in synonym dictionary
            if term_lower in self.MESH_SYNONYMS:
                expanded.update(self.MESH_SYNONYMS[term_lower])
            # Check for partial matches
            for key, synonyms in self.MESH_SYNONYMS.items():
                if key in term_lower or term_lower in key:
                    expanded.update(synonyms)

        return list(expanded)

    def _clean_term(self, term: str) -> str:
        """Clean a search term for Scopus compatibility."""
        # Remove special characters that break Scopus queries
        cleaned = re.sub(r'[^\w\s-]', '', term)
        cleaned = cleaned.strip()
        return cleaned if len(cleaned) > 2 else ""

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text as fallback."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'what', 'how', 'why', 'when', 'where', 'which', 'who', 'whom',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their',
            'effectiveness', 'effective', 'effect', 'effects', 'impact',
            'using', 'used', 'use', 'based', 'study', 'studies', 'research',
            'review', 'analysis', 'method', 'methods', 'approach', 'approaches',
            'results', 'conclusion', 'published', 'articles', 'journal',
            'between', 'among', 'through', 'during', 'before', 'after',
        }

        # Extract words with 3+ characters (lowered threshold)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]

        # Prioritize longer, more specific words
        keywords.sort(key=lambda x: len(x), reverse=True)

        # Return unique keywords (max 8)
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique[:8]

    def generate_boolean_query(
        self,
        research_question: str,
        inclusion_criteria: List[str] = None,
        date_range: Tuple[int, int] = None,
        expand_terms: bool = False  # Disabled by default for simpler queries
    ) -> str:
        """
        Generate a Scopus-compatible Boolean search query.

        Args:
            research_question: Natural language research question
            inclusion_criteria: Additional inclusion criteria
            date_range: (start_year, end_year) tuple
            expand_terms: Whether to expand terms with synonyms

        Returns:
            Boolean query string for Scopus API
        """
        # First try simple keyword extraction (more reliable)
        keywords = self._extract_keywords(research_question)

        # Also extract from inclusion criteria if available
        if inclusion_criteria:
            for criterion in inclusion_criteria[:3]:
                keywords.extend(self._extract_keywords(criterion))

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        # Use top keywords for query
        query_keywords = unique_keywords[:5]

        if not query_keywords:
            # Ultimate fallback: use whole words from question
            words = re.findall(r'\b[a-zA-Z]{3,}\b', research_question)
            query_keywords = words[:5]

        # Build simple but effective query
        if len(query_keywords) >= 2:
            # Use AND for first 2-3 important terms, makes query focused
            main_terms = query_keywords[:3]
            boolean_query = "TITLE-ABS-KEY(" + " AND ".join(main_terms) + ")"
        else:
            boolean_query = f"TITLE-ABS-KEY({query_keywords[0]})" if query_keywords else ""

        if not boolean_query:
            logger.warning("Could not generate query from research question")
            return ""

        # Add date range filter
        if date_range:
            start_year, end_year = date_range
            boolean_query += f" AND PUBYEAR > {start_year - 1} AND PUBYEAR < {end_year + 1}"

        # Only add language filter, skip DOCTYPE to get more results
        boolean_query += ' AND LANGUAGE(english)'

        self.generated_queries.append({
            "query": boolean_query,
            "keywords": query_keywords,
            "generated_at": datetime.now().isoformat(),
        })

        logger.info(f"Generated query with keywords: {query_keywords}")
        return boolean_query

    def refine_query(self, original_query: str, result_count: int, target_range: Tuple[int, int] = (100, 1000)) -> str:
        """
        Refine query based on result count.

        Args:
            original_query: The original Boolean query
            result_count: Number of results from original query
            target_range: Desired result count range

        Returns:
            Refined query string
        """
        min_target, max_target = target_range

        if result_count < min_target:
            # Too few results - broaden search
            # Remove some restrictive filters
            refined = original_query
            if "DOCTYPE" in refined:
                refined = re.sub(r"\s+AND\s+DOCTYPE\([^)]+\)", "", refined)
            if "LANGUAGE" in refined:
                refined = re.sub(r"\s+AND\s+LANGUAGE\([^)]+\)", "", refined)
            logger.info(f"Broadened query: {result_count} -> target {min_target}+")
            return refined

        elif result_count > max_target:
            # Too many results - narrow search
            # Add more specific filters
            refined = original_query
            # Add title-only search for key terms
            refined = refined.replace("TITLE-ABS-KEY", "TITLE")
            logger.info(f"Narrowed query: {result_count} -> target <{max_target}")
            return refined

        return original_query

    async def execute_search(self, state: SLRState) -> SLRState:
        """
        Execute search phase of SLR pipeline.

        Args:
            state: Current SLR state

        Returns:
            Updated state with search results
        """
        from datetime import datetime

        state["agent_status"]["search"] = AgentStatus.ACTIVE.value
        state["current_phase"] = "search"
        state["processing_log"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Search Agent: Starting...")

        try:
            # Generate Boolean query
            query = self.generate_boolean_query(
                research_question=state["research_question"],
                inclusion_criteria=state["inclusion_criteria"],
                date_range=state["date_range"],
            )
            state["search_queries"].append(query)
            state["processing_log"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Generated query: {query[:100]}...")

            # Execute search via Scopus API
            if self.scopus_client:
                results = await self.scopus_client.search(query)
                state["raw_papers"] = results
                state["prisma_stats"]["identified"] = len(results)

                # Check if we need to refine
                if len(results) < 50 or len(results) > 2000:
                    refined_query = self.refine_query(query, len(results))
                    if refined_query != query:
                        state["search_queries"].append(refined_query)
                        results = await self.scopus_client.search(refined_query)
                        state["raw_papers"] = results
                        state["prisma_stats"]["identified"] = len(results)
            else:
                # No client - return empty for testing
                state["raw_papers"] = []
                state["prisma_stats"]["identified"] = 0

            # Deduplicate results
            deduplicated = self._deduplicate(state["raw_papers"])
            state["deduplicated_papers"] = deduplicated
            state["prisma_stats"]["duplicates_removed"] = len(state["raw_papers"]) - len(deduplicated)

            state["agent_status"]["search"] = AgentStatus.COMPLETED.value
            state["processing_log"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Search complete: "
                f"{state['prisma_stats']['identified']} identified, "
                f"{state['prisma_stats']['duplicates_removed']} duplicates removed"
            )

        except Exception as e:
            state["agent_status"]["search"] = AgentStatus.ERROR.value
            state["errors"].append(f"Search error: {str(e)}")
            logger.error(f"Search agent error: {e}")

        state["updated_at"] = datetime.now().isoformat()
        return state

    def _deduplicate(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on DOI and title similarity."""
        from rapidfuzz import fuzz

        seen_dois = set()
        seen_titles = []
        unique_papers = []

        for paper in papers:
            doi = paper.get("doi", "").lower().strip()
            title = paper.get("title", "").lower().strip()

            # Check DOI
            if doi and doi in seen_dois:
                continue

            # Check title similarity
            is_duplicate = False
            for seen_title in seen_titles:
                if fuzz.ratio(title, seen_title) > 90:
                    is_duplicate = True
                    break

            if not is_duplicate:
                if doi:
                    seen_dois.add(doi)
                seen_titles.append(title)
                unique_papers.append(paper)

        return unique_papers


# LangGraph node function
async def search_node(state: SLRState) -> SLRState:
    """LangGraph node for search agent."""
    from api.scopus import ScopusClient
    from config import settings

    client = ScopusClient(api_key=settings.scopus_api_key) if settings.scopus_api_key else None
    agent = SearchAgent(scopus_client=client)
    return await agent.execute_search(state)
