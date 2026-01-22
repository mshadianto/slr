"""
Muezza AI - DOAJ API Client
===========================
Client for Directory of Open Access Journals (DOAJ) API.
Free official API - all articles are guaranteed Open Access.

API Documentation: https://doaj.org/api/v3/docs
"""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DOAJClient:
    """
    Async client for DOAJ (Directory of Open Access Journals) API.

    Benefits:
    - Official free API
    - All articles are Open Access (guaranteed downloadable)
    - No authentication required
    - Good coverage of OA journals worldwide

    Rate Limits:
    - No strict limits, but be respectful
    - Recommend ~2 requests per second
    """

    BASE_URL = "https://doaj.org/api"
    SEARCH_URL = f"{BASE_URL}/search/articles"

    def __init__(
        self,
        rate_limit: float = 2.0,  # requests per second
        timeout: int = 30
    ):
        """
        Initialize DOAJ client.

        Args:
            rate_limit: Max requests per second (default 2)
            timeout: Request timeout in seconds
        """
        self.rate_limit = rate_limit
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._last_request_time = 0
        self._semaphore = asyncio.Semaphore(2)

    async def _rate_limit_wait(self):
        """Enforce rate limiting."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _make_request(self, url: str, params: Dict = None) -> Dict:
        """Make HTTP request with retry logic."""
        async with self._semaphore:
            await self._rate_limit_wait()

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("DOAJ rate limited, backing off...")
                        raise Exception("Rate limited")
                    else:
                        logger.error(f"DOAJ API error: {response.status}")
                        return {}

    def _parse_article(self, article: Dict) -> Dict:
        """Parse DOAJ article response into standard format."""
        bibjson = article.get('bibjson', {})
        admin = article.get('admin', {})

        # Get authors
        authors = []
        for author in bibjson.get('author', []):
            name = author.get('name', '')
            if name:
                authors.append(name)

        # Get identifiers
        identifiers = bibjson.get('identifier', [])
        doi = None
        for ident in identifiers:
            if ident.get('type') == 'doi':
                doi = ident.get('id', '')
                break

        # Get journal info
        journal = bibjson.get('journal', {})

        # Get links (for PDF)
        links = bibjson.get('link', [])
        pdf_url = None
        fulltext_url = None
        for link in links:
            if link.get('type') == 'fulltext':
                if link.get('content_type') == 'application/pdf':
                    pdf_url = link.get('url')
                else:
                    fulltext_url = link.get('url')

        return {
            'title': bibjson.get('title', ''),
            'authors': authors,
            'year': bibjson.get('year', ''),
            'month': bibjson.get('month', ''),
            'abstract': bibjson.get('abstract', ''),
            'doi': doi,
            'journal': journal.get('title', ''),
            'publisher': journal.get('publisher', ''),
            'issn': journal.get('issns', []),
            'volume': journal.get('volume', ''),
            'issue': journal.get('number', ''),
            'start_page': bibjson.get('start_page', ''),
            'end_page': bibjson.get('end_page', ''),
            'keywords': bibjson.get('keywords', []),
            'subject': [s.get('term', '') for s in bibjson.get('subject', [])],
            'pdf_url': pdf_url,
            'fulltext_url': fulltext_url or pdf_url,
            'doaj_id': article.get('id', ''),
            'source': 'doaj',
            'is_open_access': True,  # All DOAJ articles are OA
            'license': bibjson.get('license', [{}])[0].get('type', '') if bibjson.get('license') else ''
        }

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 25,
        sort: str = None
    ) -> Dict:
        """
        Search DOAJ for articles.

        Args:
            query: Search query (supports Lucene query syntax)
            page: Page number (1-indexed)
            page_size: Results per page (max 100)
            sort: Sort field (e.g., 'created_date:desc')

        Returns:
            Dict with 'results' list and 'total' count
        """
        params = {
            'q': query,
            'page': page,
            'pageSize': min(page_size, 100)
        }

        if sort:
            params['sort'] = sort

        url = self.SEARCH_URL

        try:
            response = await self._make_request(url, params)

            results = []
            for article in response.get('results', []):
                parsed = self._parse_article(article)
                results.append(parsed)

            total = response.get('total', 0)

            logger.info(f"DOAJ found {len(results)} results (total: {total}) for: {query[:50]}...")

            return {
                'results': results,
                'total': total,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"DOAJ search error: {e}")
            return {'results': [], 'total': 0, 'page': page, 'page_size': page_size}

    async def search_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Search for article by DOI.

        Args:
            doi: DOI identifier

        Returns:
            Article dict if found, None otherwise
        """
        # Clean DOI
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')

        query = f'doi:"{doi}"'
        result = await self.search(query, page_size=1)

        if result['results']:
            return result['results'][0]
        return None

    async def search_by_title(self, title: str) -> Optional[Dict]:
        """
        Search for article by title.

        Args:
            title: Article title

        Returns:
            Article dict if found (best match), None otherwise
        """
        # Escape special characters
        title_escaped = title.replace('"', '\\"')
        query = f'bibjson.title:"{title_escaped}"'

        result = await self.search(query, page_size=5)

        if result['results']:
            # Return best match (first result)
            return result['results'][0]
        return None

    async def get_pdf_url(self, doi: str = None, title: str = None) -> Optional[str]:
        """
        Get PDF URL for an article.

        Args:
            doi: DOI identifier
            title: Article title (used if DOI not provided)

        Returns:
            PDF URL if available, None otherwise
        """
        article = None

        if doi:
            article = await self.search_by_doi(doi)

        if not article and title:
            article = await self.search_by_title(title)

        if article:
            return article.get('pdf_url') or article.get('fulltext_url')

        return None

    async def search_all(
        self,
        query: str,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search and return all results up to max_results.

        Args:
            query: Search query
            max_results: Maximum total results to return

        Returns:
            List of article dictionaries
        """
        all_results = []
        page = 1
        page_size = min(100, max_results)

        while len(all_results) < max_results:
            result = await self.search(query, page=page, page_size=page_size)

            if not result['results']:
                break

            all_results.extend(result['results'])

            if len(result['results']) < page_size:
                break

            page += 1

        return all_results[:max_results]


# Convenience functions
async def search_doaj(query: str, max_results: int = 25) -> List[Dict]:
    """
    Quick search function for DOAJ.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        List of article dictionaries
    """
    client = DOAJClient()
    return await client.search_all(query, max_results)


async def get_doaj_pdf(doi: str = None, title: str = None) -> Optional[str]:
    """
    Get PDF URL from DOAJ.

    Args:
        doi: DOI identifier
        title: Article title

    Returns:
        PDF URL if found, None otherwise
    """
    client = DOAJClient()
    return await client.get_pdf_url(doi=doi, title=title)
