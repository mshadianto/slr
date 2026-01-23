"""
BiblioAgent AI - Scopus API Client
==================================
Client for Elsevier Scopus API to search academic papers.
Free tier: 5000 requests/week
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ScopusClient:
    """
    Async client for Scopus Search API.

    API Documentation: https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl

    Free Tier Limits:
    - 5000 requests per week
    - 25 results per request (configurable up to 200)
    - 9 requests per second rate limit
    """

    BASE_URL = "https://api.elsevier.com/content/search/scopus"

    def __init__(
        self,
        api_key: str,
        rate_limit: int = 9,  # requests per second
        results_per_page: int = 25
    ):
        """
        Initialize Scopus client.

        Args:
            api_key: Scopus API key from dev.elsevier.com
            rate_limit: Max requests per second (default 9)
            results_per_page: Results per API call (max 200)
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.results_per_page = min(results_per_page, 200)
        self._last_request_time = 0
        self._request_count = 0

    async def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        params: Dict
    ) -> Dict:
        """Make a single API request with retry logic."""
        await self._rate_limit_wait()

        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
        }

        async with session.get(
            self.BASE_URL,
            params=params,
            headers=headers
        ) as response:
            self._request_count += 1

            if response.status == 429:
                logger.warning("Rate limit exceeded, waiting...")
                await asyncio.sleep(60)
                raise Exception("Rate limit exceeded")

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Scopus API error {response.status}: {error_text}")
                raise Exception(f"API error: {response.status}")

            return await response.json()

    def _parse_entry(self, entry: Dict) -> Dict:
        """Parse a single Scopus entry into our paper format."""
        # Extract authors
        authors = []
        if "author" in entry:
            for author in entry.get("author", []):
                author_name = author.get("authname", "")
                if author_name:
                    authors.append(author_name)

        # Extract DOI
        doi = entry.get("prism:doi", "")
        if not doi:
            # Try to extract from link
            for link in entry.get("link", []):
                if link.get("@ref") == "scopus":
                    # Extract DOI from EID or other identifier
                    pass

        # Extract year
        year = 0
        cover_date = entry.get("prism:coverDate", "")
        if cover_date:
            try:
                year = int(cover_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        return {
            "doi": doi,
            "title": entry.get("dc:title", ""),
            "authors": authors,
            "year": year,
            "abstract": entry.get("dc:description", ""),
            "journal": entry.get("prism:publicationName", ""),
            "keywords": entry.get("authkeywords", "").split(" | ") if entry.get("authkeywords") else [],
            "document_type": entry.get("subtypeDescription", ""),
            "source_database": "scopus",
            "scopus_id": entry.get("dc:identifier", "").replace("SCOPUS_ID:", ""),
            "eid": entry.get("eid", ""),
            "citations_count": int(entry.get("citedby-count", 0)),
            "affiliation": entry.get("affiliation", [{}])[0].get("affilname", "") if entry.get("affiliation") else "",
        }

    async def search(
        self,
        query: str,
        max_results: int = 200,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[Dict]:
        """
        Search Scopus for papers matching the query.

        Args:
            query: Boolean search query (Scopus syntax)
            max_results: Maximum papers to return
            start_year: Filter by start year
            end_year: Filter by end year

        Returns:
            List of paper dictionaries
        """
        papers = []
        start = 0

        # Add date filter if specified
        if start_year and end_year:
            if "PUBYEAR" not in query.upper():
                query += f" AND PUBYEAR > {start_year - 1} AND PUBYEAR < {end_year + 1}"

        logger.info(f"Searching Scopus: {query[:100]}...")

        async with aiohttp.ClientSession() as session:
            while len(papers) < max_results:
                params = {
                    "query": query,
                    "start": start,
                    "count": min(self.results_per_page, max_results - len(papers)),
                    "view": "STANDARD",  # Use STANDARD view (COMPLETE requires special permissions)
                    "sort": "citedby-count",  # Sort by citations
                }

                try:
                    data = await self._make_request(session, params)

                    # Parse results
                    search_results = data.get("search-results", {})
                    total_results = int(search_results.get("opensearch:totalResults", 0))

                    if total_results == 0:
                        logger.info("No results found")
                        break

                    entries = search_results.get("entry", [])

                    if not entries:
                        break

                    for entry in entries:
                        if "error" in entry:
                            continue
                        paper = self._parse_entry(entry)
                        papers.append(paper)

                    logger.info(f"Retrieved {len(papers)}/{min(total_results, max_results)} papers")

                    # Check if we've got all results
                    if len(papers) >= total_results or len(papers) >= max_results:
                        break

                    start += self.results_per_page

                except Exception as e:
                    logger.error(f"Search error: {e}")
                    break

        logger.info(f"Search complete: {len(papers)} papers retrieved")
        return papers

    async def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """Get a single paper by DOI."""
        query = f"DOI({doi})"
        results = await self.search(query, max_results=1)
        return results[0] if results else None

    async def get_paper_by_eid(self, eid: str) -> Optional[Dict]:
        """Get a single paper by Scopus EID."""
        query = f"EID({eid})"
        results = await self.search(query, max_results=1)
        return results[0] if results else None

    def get_request_count(self) -> int:
        """Get the number of API requests made."""
        return self._request_count

    async def cached_search(
        self,
        query: str,
        max_results: int = 200,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        cache_ttl: int = 3600
    ) -> List[Dict]:
        """
        Search with caching support.

        Args:
            query: Boolean search query
            max_results: Maximum papers to return
            start_year: Filter by start year
            end_year: Filter by end year
            cache_ttl: Cache TTL in seconds (default 1 hour)

        Returns:
            List of paper dictionaries
        """
        from .search_cache import get_search_cache

        cache = get_search_cache()

        # Build cache key params
        cache_params = {
            'max_results': max_results,
            'start_year': start_year,
            'end_year': end_year
        }

        # Try cache first
        cached = cache.get(query, source="scopus", params=cache_params)
        if cached is not None:
            logger.info(f"[CACHE HIT] Scopus: {len(cached)} papers from cache")
            return cached

        # Execute actual search
        logger.info(f"[CACHE MISS] Scopus: executing search...")
        results = await self.search(query, max_results, start_year, end_year)

        # Cache results
        if results:
            cache.set(query, results, source="scopus", params=cache_params, ttl=cache_ttl)
            logger.info(f"[CACHED] Scopus: {len(results)} papers cached for {cache_ttl}s")

        return results
