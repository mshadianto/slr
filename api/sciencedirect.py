"""
Muezza AI - ScienceDirect API Client
====================================
Client for Elsevier ScienceDirect API to retrieve full-text articles.
Requires institutional access or Text Mining API key.

API Documentation: https://dev.elsevier.com/sciencedirect.html
"""

import asyncio
import logging
from typing import Optional, Dict, List
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ScienceDirectClient:
    """
    Async client for ScienceDirect Article Retrieval API.

    Provides access to full-text articles from Elsevier journals.
    Requires API key from dev.elsevier.com with institutional entitlement.

    Rate Limits:
    - 2 requests per second for article retrieval
    - 10,000 requests per week (institutional)
    """

    BASE_URL = "https://api.elsevier.com/content/article"
    SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"

    def __init__(
        self,
        api_key: str,
        inst_token: Optional[str] = None,
        rate_limit: float = 2.0
    ):
        """
        Initialize ScienceDirect client.

        Args:
            api_key: Elsevier API key from dev.elsevier.com
            inst_token: Institutional token (optional, for off-campus access)
            rate_limit: Max requests per second (default 2)
        """
        self.api_key = api_key
        self.inst_token = inst_token
        self.rate_limit = rate_limit
        self._last_request_time = 0
        self._request_count = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
        }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token
        return headers

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
    async def get_article_by_doi(
        self,
        doi: str,
        full_text: bool = True
    ) -> Optional[Dict]:
        """
        Retrieve article by DOI.

        Args:
            doi: Article DOI
            full_text: Whether to retrieve full text (requires entitlement)

        Returns:
            Article data dict or None if not found/not entitled
        """
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/doi/{doi}"
        params = {"view": "FULL"} if full_text else {"view": "META"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=self._get_headers()
                ) as response:
                    self._request_count += 1

                    if response.status == 404:
                        logger.debug(f"Article not found: {doi}")
                        return None

                    if response.status == 401:
                        logger.warning(f"Not entitled to access: {doi}")
                        return None

                    if response.status == 429:
                        logger.warning("Rate limit exceeded")
                        await asyncio.sleep(60)
                        raise Exception("Rate limit exceeded")

                    if response.status != 200:
                        logger.error(f"ScienceDirect API error: {response.status}")
                        return None

                    data = await response.json()
                    return self._parse_article(data, doi)

            except aiohttp.ClientError as e:
                logger.error(f"Request failed for {doi}: {e}")
                return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def get_article_by_pii(
        self,
        pii: str,
        full_text: bool = True
    ) -> Optional[Dict]:
        """
        Retrieve article by PII (Publisher Item Identifier).

        Args:
            pii: Article PII
            full_text: Whether to retrieve full text

        Returns:
            Article data dict or None
        """
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/pii/{pii}"
        params = {"view": "FULL"} if full_text else {"view": "META"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=self._get_headers()
                ) as response:
                    self._request_count += 1

                    if response.status not in [200, 404, 401]:
                        logger.error(f"ScienceDirect API error: {response.status}")
                        return None

                    if response.status in [404, 401]:
                        return None

                    data = await response.json()
                    return self._parse_article(data, pii)

            except aiohttp.ClientError as e:
                logger.error(f"Request failed for PII {pii}: {e}")
                return None

    def _parse_article(self, data: Dict, identifier: str) -> Optional[Dict]:
        """Parse article response into standard format."""
        try:
            article = data.get("full-text-retrieval-response", {})

            if not article:
                return None

            coredata = article.get("coredata", {})

            # Extract full text from originalText or body
            full_text = None
            original_text = article.get("originalText")
            if original_text:
                full_text = original_text
            else:
                # Try to extract from structured body
                body = article.get("body", {})
                if body:
                    full_text = self._extract_body_text(body)

            # Extract authors
            authors = []
            author_data = coredata.get("dc:creator", [])
            if isinstance(author_data, list):
                for author in author_data:
                    if isinstance(author, dict):
                        authors.append(author.get("$", ""))
                    else:
                        authors.append(str(author))
            elif author_data:
                authors.append(str(author_data))

            return {
                "doi": coredata.get("prism:doi", identifier),
                "pii": coredata.get("pii", ""),
                "title": coredata.get("dc:title", ""),
                "abstract": coredata.get("dc:description", ""),
                "authors": authors,
                "journal": coredata.get("prism:publicationName", ""),
                "year": self._extract_year(coredata.get("prism:coverDate", "")),
                "full_text": full_text,
                "full_text_source": "sciencedirect" if full_text else None,
                "pdf_url": self._extract_pdf_link(article),
                "open_access": coredata.get("openaccess", "0") == "1",
                "source": "sciencedirect",
            }

        except Exception as e:
            logger.error(f"Error parsing article {identifier}: {e}")
            return None

    def _extract_body_text(self, body: Dict) -> str:
        """Extract plain text from structured body."""
        texts = []

        def extract_text(node):
            if isinstance(node, str):
                texts.append(node)
            elif isinstance(node, dict):
                if "$" in node:
                    texts.append(node["$"])
                for key, value in node.items():
                    if key != "$":
                        extract_text(value)
            elif isinstance(node, list):
                for item in node:
                    extract_text(item)

        extract_text(body)
        return "\n".join(texts)

    def _extract_year(self, date_str: str) -> int:
        """Extract year from date string."""
        if not date_str:
            return 0
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return 0

    def _extract_pdf_link(self, article: Dict) -> Optional[str]:
        """Extract PDF download link if available."""
        links = article.get("link", [])
        for link in links:
            if isinstance(link, dict):
                if link.get("@rel") == "scidir" or "pdf" in link.get("@href", "").lower():
                    return link.get("@href")
        return None

    async def search(
        self,
        query: str,
        max_results: int = 25,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[Dict]:
        """
        Search ScienceDirect for articles.

        Args:
            query: Search query
            max_results: Maximum results to return
            start_year: Filter by start year
            end_year: Filter by end year

        Returns:
            List of article metadata dicts
        """
        await self._rate_limit_wait()

        params = {
            "query": query,
            "count": min(max_results, 100),
            "view": "COMPLETE",
        }

        if start_year:
            params["date"] = f"{start_year}-{end_year or 2030}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self.SEARCH_URL,
                    params=params,
                    headers=self._get_headers()
                ) as response:
                    self._request_count += 1

                    if response.status != 200:
                        logger.error(f"Search failed: {response.status}")
                        return []

                    data = await response.json()
                    results = data.get("search-results", {}).get("entry", [])

                    return [
                        {
                            "doi": r.get("prism:doi", ""),
                            "pii": r.get("pii", ""),
                            "title": r.get("dc:title", ""),
                            "authors": r.get("authors", {}).get("author", []),
                            "journal": r.get("prism:publicationName", ""),
                            "year": self._extract_year(r.get("prism:coverDate", "")),
                            "open_access": r.get("openaccess", "0") == "1",
                        }
                        for r in results
                        if not r.get("error")
                    ]

            except aiohttp.ClientError as e:
                logger.error(f"Search failed: {e}")
                return []

    def get_request_count(self) -> int:
        """Get total API requests made."""
        return self._request_count


# Convenience functions
async def get_sciencedirect_fulltext(
    doi: str,
    api_key: str,
    inst_token: Optional[str] = None
) -> Optional[str]:
    """
    Quick function to get full text from ScienceDirect.

    Args:
        doi: Article DOI
        api_key: Elsevier API key
        inst_token: Institutional token (optional)

    Returns:
        Full text string or None
    """
    client = ScienceDirectClient(api_key, inst_token)
    result = await client.get_article_by_doi(doi, full_text=True)

    if result and result.get("full_text"):
        return result["full_text"]
    return None
