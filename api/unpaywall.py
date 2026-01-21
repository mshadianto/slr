"""
BiblioAgent AI - Unpaywall API Client
=====================================
Client for Unpaywall API to find open access versions of papers.
Free tier: 100,000 requests/day (just need email)
"""

import asyncio
import logging
from typing import Dict, Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class UnpaywallClient:
    """
    Async client for Unpaywall API.

    API Documentation: https://unpaywall.org/products/api

    Unpaywall finds legal open access versions of papers:
    - Gold OA: Publisher makes freely available
    - Green OA: Author self-archived in repository
    - Bronze OA: Free to read but unclear license
    - Hybrid: In subscription journal but made OA

    No API key needed - just your email address.
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        email: str,
        rate_limit: int = 100  # requests per second (generous limit)
    ):
        """
        Initialize Unpaywall client.

        Args:
            email: Your email address (required by API)
            rate_limit: Max requests per second
        """
        self.email = email
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        doi: str
    ) -> Optional[Dict]:
        """Make a single API request with retry logic."""
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/{doi}"
        params = {"email": self.email}

        async with session.get(url, params=params) as response:
            if response.status == 404:
                logger.debug(f"DOI not found in Unpaywall: {doi}")
                return None

            if response.status == 422:
                logger.warning(f"Invalid DOI format: {doi}")
                return None

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Unpaywall API error {response.status}: {error_text}")
                raise Exception(f"API error: {response.status}")

            return await response.json()

    async def get_oa_location(self, doi: str) -> Optional[Dict]:
        """
        Get open access information for a DOI.

        Args:
            doi: The DOI to look up (e.g., "10.1038/nature12373")

        Returns:
            Dict with OA information or None if not found
        """
        # Clean DOI
        doi = doi.strip().lower()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("http://doi.org/"):
            doi = doi[15:]
        elif doi.startswith("doi:"):
            doi = doi[4:]

        if not doi:
            return None

        async with aiohttp.ClientSession() as session:
            try:
                data = await self._make_request(session, doi)

                if data and data.get("is_oa"):
                    return {
                        "is_oa": True,
                        "oa_status": data.get("oa_status"),  # gold, green, bronze, hybrid
                        "best_oa_location": data.get("best_oa_location"),
                        "all_oa_locations": data.get("oa_locations", []),
                        "title": data.get("title"),
                        "journal": data.get("journal_name"),
                        "year": data.get("year"),
                        "publisher": data.get("publisher"),
                    }
                elif data:
                    return {
                        "is_oa": False,
                        "oa_status": "closed",
                        "best_oa_location": None,
                        "title": data.get("title"),
                        "journal": data.get("journal_name"),
                    }

                return None

            except Exception as e:
                logger.error(f"Unpaywall lookup failed for {doi}: {e}")
                return None

    async def get_pdf_url(self, doi: str) -> Optional[str]:
        """
        Get the best PDF URL for a DOI.

        Args:
            doi: The DOI to look up

        Returns:
            PDF URL or None if not available
        """
        result = await self.get_oa_location(doi)

        if result and result.get("best_oa_location"):
            location = result["best_oa_location"]
            # Prefer PDF URL, fall back to landing page
            return location.get("url_for_pdf") or location.get("url")

        return None

    async def batch_lookup(
        self,
        dois: list,
        max_concurrent: int = 10
    ) -> Dict[str, Optional[Dict]]:
        """
        Look up multiple DOIs concurrently.

        Args:
            dois: List of DOIs to look up
            max_concurrent: Max concurrent requests

        Returns:
            Dict mapping DOI to result
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def lookup_with_semaphore(doi: str):
            async with semaphore:
                return doi, await self.get_oa_location(doi)

        tasks = [lookup_with_semaphore(doi) for doi in dois]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                logger.error(f"Batch lookup error: {item}")
            else:
                doi, result = item
                results[doi] = result

        return results
