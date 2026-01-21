"""
BiblioAgent AI - Semantic Scholar API Client
============================================
Client for Semantic Scholar API to get paper metadata and citations.
Free tier: 100 requests per 5 minutes without API key
"""

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """
    Async client for Semantic Scholar Academic Graph API.

    API Documentation: https://api.semanticscholar.org/api-docs/

    Semantic Scholar provides:
    - Paper metadata and abstracts
    - Citation and reference graphs
    - Open access PDF links when available
    - Citation contexts (how papers cite each other)

    Rate Limits:
    - Without API key: 100 requests per 5 minutes
    - With API key: Higher limits available
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # Fields to request from the API
    PAPER_FIELDS = [
        "paperId", "externalIds", "title", "abstract", "year",
        "authors", "venue", "publicationVenue", "citationCount",
        "influentialCitationCount", "isOpenAccess", "openAccessPdf",
        "fieldsOfStudy", "publicationTypes", "publicationDate"
    ]

    CITATION_FIELDS = [
        "paperId", "title", "year", "abstract",
        "citationCount", "isOpenAccess", "contexts"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: float = 0.33  # ~100 requests per 5 min = 0.33/sec
    ):
        """
        Initialize Semantic Scholar client.

        Args:
            api_key: Optional API key for higher rate limits
            rate_limit: Max requests per second
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._last_request_time = 0
        self._request_count = 0

    async def _rate_limit_wait(self):
        """Enforce rate limiting."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Dict = None
    ) -> Optional[Dict]:
        """Make a single API request with retry logic."""
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()

        async with session.get(url, params=params, headers=headers) as response:
            self._request_count += 1

            if response.status == 429:
                logger.warning("Semantic Scholar rate limit exceeded")
                await asyncio.sleep(60)  # Wait a minute
                raise Exception("Rate limit exceeded")

            if response.status == 404:
                return None

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"S2 API error {response.status}: {error_text[:200]}")
                raise Exception(f"API error: {response.status}")

            return await response.json()

    def _parse_paper(self, data: Dict) -> Dict:
        """Parse Semantic Scholar paper data into our format."""
        # Extract authors
        authors = []
        for author in data.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Extract DOI
        doi = ""
        external_ids = data.get("externalIds", {})
        if external_ids:
            doi = external_ids.get("DOI", "")

        # Extract open access PDF
        pdf_url = None
        oa_pdf = data.get("openAccessPdf")
        if oa_pdf:
            pdf_url = oa_pdf.get("url")

        return {
            "doi": doi,
            "title": data.get("title", ""),
            "authors": authors,
            "year": data.get("year", 0),
            "abstract": data.get("abstract", ""),
            "journal": data.get("venue", ""),
            "keywords": data.get("fieldsOfStudy", []),
            "source_database": "semantic_scholar",
            "paper_id": data.get("paperId", ""),
            "citations_count": data.get("citationCount", 0),
            "influential_citations": data.get("influentialCitationCount", 0),
            "is_open_access": data.get("isOpenAccess", False),
            "pdf_url": pdf_url,
            "publication_types": data.get("publicationTypes", []),
            "arxiv_id": external_ids.get("ArXiv", "") if external_ids else "",
            "pubmed_id": external_ids.get("PubMed", "") if external_ids else "",
        }

    async def get_paper(self, identifier: str) -> Optional[Dict]:
        """
        Get paper details by DOI, Semantic Scholar ID, or title.

        Args:
            identifier: DOI, S2 paper ID, arXiv ID, or title

        Returns:
            Paper dict or None
        """
        # Determine identifier type
        if identifier.startswith("10."):
            # DOI
            paper_id = f"DOI:{identifier}"
        elif identifier.startswith("arXiv:") or re.match(r"\d{4}\.\d{4,5}", identifier):
            # ArXiv ID
            arxiv_id = identifier.replace("arXiv:", "")
            paper_id = f"ARXIV:{arxiv_id}"
        elif len(identifier) == 40 and identifier.isalnum():
            # S2 paper ID (40 char hex)
            paper_id = identifier
        else:
            # Try as title - use search
            return await self.search_by_title(identifier)

        async with aiohttp.ClientSession() as session:
            try:
                params = {"fields": ",".join(self.PAPER_FIELDS)}
                data = await self._make_request(
                    session,
                    f"paper/{paper_id}",
                    params
                )

                if data:
                    return self._parse_paper(data)
                return None

            except Exception as e:
                logger.error(f"S2 get paper error: {e}")
                return None

    async def search_by_title(self, title: str, limit: int = 5) -> Optional[Dict]:
        """
        Search for a paper by title.

        Args:
            title: Paper title
            limit: Max results

        Returns:
            Best matching paper or None
        """
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "query": title,
                    "limit": limit,
                    "fields": ",".join(self.PAPER_FIELDS),
                }

                data = await self._make_request(
                    session,
                    "paper/search",
                    params
                )

                if data and data.get("data"):
                    # Return first (best) match
                    return self._parse_paper(data["data"][0])
                return None

            except Exception as e:
                logger.error(f"S2 search error: {e}")
                return None

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
        include_contexts: bool = True
    ) -> List[Dict]:
        """
        Get papers that cite the given paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum citations to return
            include_contexts: Include citation contexts (sentences)

        Returns:
            List of citing papers with optional contexts
        """
        async with aiohttp.ClientSession() as session:
            try:
                fields = self.CITATION_FIELDS.copy()
                if include_contexts:
                    fields.append("contexts")

                params = {
                    "fields": ",".join(fields),
                    "limit": min(limit, 1000),
                }

                data = await self._make_request(
                    session,
                    f"paper/{paper_id}/citations",
                    params
                )

                if not data or "data" not in data:
                    return []

                citations = []
                for item in data["data"]:
                    citing_paper = item.get("citingPaper", {})
                    contexts = item.get("contexts", [])

                    citation = {
                        "paper_id": citing_paper.get("paperId", ""),
                        "title": citing_paper.get("title", ""),
                        "year": citing_paper.get("year", 0),
                        "abstract": citing_paper.get("abstract", ""),
                        "is_open_access": citing_paper.get("isOpenAccess", False),
                        "citation_contexts": contexts,
                    }

                    # If there are contexts, include the first one as main context
                    if contexts:
                        citation["citationContext"] = contexts[0]

                    citations.append(citation)

                logger.info(f"Retrieved {len(citations)} citations for paper {paper_id}")
                return citations

            except Exception as e:
                logger.error(f"S2 get citations error: {e}")
                return []

    async def get_references(
        self,
        paper_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get papers referenced by the given paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum references to return

        Returns:
            List of referenced papers
        """
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "fields": ",".join(self.PAPER_FIELDS),
                    "limit": min(limit, 1000),
                }

                data = await self._make_request(
                    session,
                    f"paper/{paper_id}/references",
                    params
                )

                if not data or "data" not in data:
                    return []

                references = []
                for item in data["data"]:
                    cited_paper = item.get("citedPaper", {})
                    if cited_paper:
                        references.append(self._parse_paper(cited_paper))

                return references

            except Exception as e:
                logger.error(f"S2 get references error: {e}")
                return []

    async def batch_get_papers(
        self,
        identifiers: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, Optional[Dict]]:
        """
        Get multiple papers concurrently.

        Args:
            identifiers: List of DOIs or paper IDs
            max_concurrent: Max concurrent requests

        Returns:
            Dict mapping identifier to paper data
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_with_semaphore(identifier: str):
            async with semaphore:
                return identifier, await self.get_paper(identifier)

        tasks = [get_with_semaphore(id) for id in identifiers]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error(f"Batch get error: {item}")
            else:
                identifier, paper = item
                results[identifier] = paper

        return results


# Import re for identifier detection
import re
