"""
BiblioAgent AI - CORE API Client
================================
Client for CORE API to search 200M+ open access research papers.
Free tier: 10 requests/second
"""

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class COREClient:
    """
    Async client for CORE API v3.

    API Documentation: https://core.ac.uk/documentation/api

    CORE aggregates open access content from repositories
    and journals worldwide - 200M+ research outputs.

    Free Tier: 10 requests/second
    """

    BASE_URL = "https://api.core.ac.uk/v3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: int = 10  # requests per second
    ):
        """
        Initialize CORE client.

        Args:
            api_key: Optional API key (increases rate limits)
            rate_limit: Max requests per second
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._last_request_time = 0

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
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        method: str = "GET",
        params: Dict = None,
        json_data: Dict = None
    ) -> Optional[Dict]:
        """Make a single API request with retry logic."""
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()

        if method == "GET":
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 429:
                    logger.warning("CORE rate limit exceeded")
                    await asyncio.sleep(10)
                    raise Exception("Rate limit exceeded")

                if response.status != 200:
                    return None

                return await response.json()
        else:  # POST
            async with session.post(url, json=json_data, headers=headers) as response:
                if response.status == 429:
                    await asyncio.sleep(10)
                    raise Exception("Rate limit exceeded")

                if response.status not in [200, 201]:
                    return None

                return await response.json()

    def _parse_work(self, work: Dict) -> Dict:
        """Parse a CORE work into our paper format."""
        # Extract authors
        authors = []
        for author in work.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Get full text if available
        full_text = work.get("fullText", "")

        return {
            "doi": work.get("doi", ""),
            "title": work.get("title", ""),
            "authors": authors,
            "year": work.get("yearPublished", 0),
            "abstract": work.get("abstract", ""),
            "journal": work.get("publisher", ""),
            "keywords": [],
            "full_text": full_text,
            "source_database": "core",
            "core_id": work.get("id", ""),
            "download_url": work.get("downloadUrl", ""),
            "repository": work.get("repositoryDocument", {}).get("name", ""),
            "language": work.get("language", {}).get("name", ""),
        }

    async def search(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search CORE for papers.

        Args:
            query: Search query string
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of paper dictionaries
        """
        async with aiohttp.ClientSession() as session:
            try:
                # Use the search endpoint
                params = {
                    "q": query,
                    "limit": min(limit, 100),
                    "offset": offset,
                }

                data = await self._make_request(
                    session,
                    "search/works",
                    params=params
                )

                if not data:
                    return []

                results = data.get("results", [])
                papers = [self._parse_work(work) for work in results]

                logger.info(f"CORE search returned {len(papers)} papers")
                return papers

            except Exception as e:
                logger.error(f"CORE search error: {e}")
                return []

    async def search_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Search for a paper by DOI.

        Args:
            doi: The DOI to search for

        Returns:
            Paper dict or None
        """
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("http://doi.org/"):
            doi = doi[15:]

        query = f'doi:"{doi}"'
        results = await self.search(query, limit=1)
        return results[0] if results else None

    async def search_by_title(self, title: str) -> Optional[Dict]:
        """
        Search for a paper by title.

        Args:
            title: The paper title

        Returns:
            Paper dict or None
        """
        # Escape special characters and search
        title_clean = title.replace('"', '\\"')
        query = f'title:"{title_clean}"'
        results = await self.search(query, limit=5)

        # Return best match (first result)
        return results[0] if results else None

    async def get_work(self, core_id: str) -> Optional[Dict]:
        """
        Get a specific work by CORE ID.

        Args:
            core_id: The CORE work ID

        Returns:
            Paper dict or None
        """
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._make_request(
                    session,
                    f"works/{core_id}"
                )

                if data:
                    return self._parse_work(data)
                return None

            except Exception as e:
                logger.error(f"CORE get work error: {e}")
                return None

    async def get_full_text(self, core_id: str) -> Optional[str]:
        """
        Get full text of a paper by CORE ID.

        Args:
            core_id: The CORE work ID

        Returns:
            Full text string or None
        """
        work = await self.get_work(core_id)
        if work:
            return work.get("full_text")
        return None
