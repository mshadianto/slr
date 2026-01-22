"""
Muezza AI - Google Scholar API Client
=====================================
Client for Google Scholar using scholarly library.
Note: Unofficial API with strict rate limits. Use with caution.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Try to import scholarly
try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    logger.warning("scholarly not installed. Google Scholar integration disabled.")


class GoogleScholarClient:
    """
    Client for Google Scholar search using scholarly library.

    Note: Google Scholar has strict rate limits and may block IPs.
    Use sparingly and consider using proxies for production.

    Rate Limits:
    - No official API, uses web scraping
    - ~100 requests before potential block
    - Recommend 1 request per 10 seconds minimum
    """

    def __init__(
        self,
        use_proxy: bool = False,
        rate_limit_delay: float = 10.0
    ):
        """
        Initialize Google Scholar client.

        Args:
            use_proxy: Whether to use free proxies (slower but safer)
            rate_limit_delay: Seconds between requests (default 10)
        """
        self.rate_limit_delay = rate_limit_delay
        self.use_proxy = use_proxy
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False

        if SCHOLARLY_AVAILABLE and use_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                logger.info("Google Scholar proxy enabled")
            except Exception as e:
                logger.warning(f"Failed to setup proxy: {e}")

    def _search_sync(self, query: str, max_results: int = 10) -> List[Dict]:
        """Synchronous search implementation."""
        if not SCHOLARLY_AVAILABLE:
            logger.warning("scholarly not available")
            return []

        results = []
        try:
            search_query = scholarly.search_pubs(query)

            for i, paper in enumerate(search_query):
                if i >= max_results:
                    break

                # Extract paper info
                bib = paper.get('bib', {})

                result = {
                    'title': bib.get('title', ''),
                    'authors': bib.get('author', '').split(' and ') if bib.get('author') else [],
                    'year': bib.get('pub_year', ''),
                    'abstract': bib.get('abstract', ''),
                    'venue': bib.get('venue', ''),
                    'citation_count': paper.get('num_citations', 0),
                    'url': paper.get('pub_url', ''),
                    'eprint_url': paper.get('eprint_url', ''),  # Direct PDF link if available
                    'source': 'google_scholar',
                    'gs_id': paper.get('author_id', [''])[0] if paper.get('author_id') else ''
                }

                results.append(result)

                # Rate limiting between results
                if i < max_results - 1:
                    import time
                    time.sleep(self.rate_limit_delay / max_results)

            logger.info(f"Google Scholar found {len(results)} results for: {query[:50]}...")

        except Exception as e:
            logger.error(f"Google Scholar search error: {e}")

        return results

    async def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search Google Scholar for papers.

        Args:
            query: Search query string
            max_results: Maximum number of results (default 10, keep low due to rate limits)

        Returns:
            List of paper dictionaries
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._search_sync,
            query,
            max_results
        )

    def _get_paper_sync(self, title: str) -> Optional[Dict]:
        """Synchronous paper lookup by title."""
        if not SCHOLARLY_AVAILABLE:
            return None

        try:
            search_query = scholarly.search_pubs(title)
            paper = next(search_query, None)

            if paper:
                bib = paper.get('bib', {})
                return {
                    'title': bib.get('title', ''),
                    'authors': bib.get('author', '').split(' and ') if bib.get('author') else [],
                    'year': bib.get('pub_year', ''),
                    'abstract': bib.get('abstract', ''),
                    'venue': bib.get('venue', ''),
                    'citation_count': paper.get('num_citations', 0),
                    'url': paper.get('pub_url', ''),
                    'eprint_url': paper.get('eprint_url', ''),
                    'source': 'google_scholar'
                }
        except Exception as e:
            logger.error(f"Google Scholar lookup error: {e}")

        return None

    async def get_paper_by_title(self, title: str) -> Optional[Dict]:
        """
        Look up a specific paper by title.

        Args:
            title: Paper title to search for

        Returns:
            Paper dictionary if found, None otherwise
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_paper_sync,
            title
        )

    async def get_pdf_url(self, title: str) -> Optional[str]:
        """
        Try to get direct PDF URL for a paper.

        Args:
            title: Paper title

        Returns:
            PDF URL if available, None otherwise
        """
        paper = await self.get_paper_by_title(title)
        if paper and paper.get('eprint_url'):
            return paper['eprint_url']
        return None


# Convenience function
async def search_google_scholar(
    query: str,
    max_results: int = 10,
    use_proxy: bool = False
) -> List[Dict]:
    """
    Quick search function for Google Scholar.

    Args:
        query: Search query
        max_results: Maximum results (keep low, default 10)
        use_proxy: Use free proxies

    Returns:
        List of paper dictionaries
    """
    client = GoogleScholarClient(use_proxy=use_proxy)
    return await client.search(query, max_results)
