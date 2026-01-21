"""
BiblioAgent AI - ArXiv API Client
=================================
Client for ArXiv API to find preprint versions of papers.
No API key needed - completely free and open.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from urllib.parse import quote
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ArxivClient:
    """
    Async client for ArXiv API.

    API Documentation: https://arxiv.org/help/api

    ArXiv provides free access to preprints in physics, mathematics,
    computer science, biology, and more.

    No API key required. Rate limit: 1 request per 3 seconds recommended.
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    # ArXiv namespaces for XML parsing
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(self, rate_limit: float = 0.33):  # ~1 request per 3 seconds
        """
        Initialize ArXiv client.

        Args:
            rate_limit: Max requests per second (default 0.33 = 1 per 3 sec)
        """
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
        wait=wait_exponential(multiplier=1, min=3, max=30)
    )
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        params: Dict
    ) -> str:
        """Make a single API request with retry logic."""
        await self._rate_limit_wait()

        async with session.get(self.BASE_URL, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"ArXiv API error {response.status}: {error_text[:200]}")
                raise Exception(f"API error: {response.status}")

            return await response.text()

    def _parse_entry(self, entry: ET.Element) -> Dict:
        """Parse a single ArXiv entry from XML."""

        def find_text(element: ET.Element, tag: str, default: str = "") -> str:
            elem = element.find(tag, self.NAMESPACES)
            return elem.text.strip() if elem is not None and elem.text else default

        def find_all_text(element: ET.Element, tag: str) -> List[str]:
            elems = element.findall(tag, self.NAMESPACES)
            return [e.text.strip() for e in elems if e.text]

        # Extract ArXiv ID
        arxiv_id = find_text(entry, "atom:id")
        if arxiv_id:
            # Extract just the ID part from URL
            match = re.search(r"arxiv\.org/abs/(.+)$", arxiv_id)
            if match:
                arxiv_id = match.group(1)

        # Extract authors
        authors = []
        for author in entry.findall("atom:author", self.NAMESPACES):
            name = find_text(author, "atom:name")
            if name:
                authors.append(name)

        # Extract categories
        categories = []
        for cat in entry.findall("atom:category", self.NAMESPACES):
            term = cat.get("term")
            if term:
                categories.append(term)

        # Extract links
        pdf_url = None
        abs_url = None
        for link in entry.findall("atom:link", self.NAMESPACES):
            link_type = link.get("type", "")
            link_href = link.get("href", "")
            link_title = link.get("title", "")

            if link_title == "pdf" or link_type == "application/pdf":
                pdf_url = link_href
            elif "abs" in link_href:
                abs_url = link_href

        # Construct PDF URL if not found
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Extract DOI if available
        doi = ""
        doi_elem = entry.find("arxiv:doi", self.NAMESPACES)
        if doi_elem is not None and doi_elem.text:
            doi = doi_elem.text.strip()

        # Extract year from published date
        published = find_text(entry, "atom:published")
        year = 0
        if published:
            try:
                year = int(published[:4])
            except ValueError:
                pass

        return {
            "arxiv_id": arxiv_id,
            "doi": doi,
            "title": find_text(entry, "atom:title").replace("\n", " "),
            "authors": authors,
            "year": year,
            "abstract": find_text(entry, "atom:summary").replace("\n", " "),
            "categories": categories,
            "pdf_url": pdf_url,
            "abs_url": abs_url or f"https://arxiv.org/abs/{arxiv_id}",
            "published": published,
            "updated": find_text(entry, "atom:updated"),
            "comment": find_text(entry, "arxiv:comment"),
            "journal_ref": find_text(entry, "arxiv:journal_ref"),
            "source_database": "arxiv",
        }

    async def search(
        self,
        title: str = "",
        author: str = "",
        abstract: str = "",
        all_fields: str = "",
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> List[Dict]:
        """
        Search ArXiv for papers.

        Args:
            title: Search in title field
            author: Search by author name
            abstract: Search in abstract
            all_fields: Search in all fields
            max_results: Maximum results to return
            start: Pagination start index
            sort_by: relevance, lastUpdatedDate, or submittedDate
            sort_order: ascending or descending

        Returns:
            List of paper dictionaries
        """
        # Build search query
        query_parts = []

        if title:
            # Escape quotes and special characters
            title_clean = title.replace('"', '').replace(':', ' ')
            query_parts.append(f'ti:"{title_clean}"')

        if author:
            author_clean = author.replace('"', '')
            query_parts.append(f'au:"{author_clean}"')

        if abstract:
            abstract_clean = abstract.replace('"', '')[:200]
            query_parts.append(f'abs:"{abstract_clean}"')

        if all_fields:
            all_clean = all_fields.replace('"', '')
            query_parts.append(f'all:"{all_clean}"')

        if not query_parts:
            logger.warning("No search terms provided")
            return []

        search_query = " AND ".join(query_parts)

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        async with aiohttp.ClientSession() as session:
            try:
                xml_response = await self._make_request(session, params)

                # Parse XML response
                root = ET.fromstring(xml_response)

                # Check for error
                entries = root.findall("atom:entry", self.NAMESPACES)

                papers = []
                for entry in entries:
                    paper = self._parse_entry(entry)
                    papers.append(paper)

                logger.info(f"ArXiv search returned {len(papers)} papers")
                return papers

            except ET.ParseError as e:
                logger.error(f"ArXiv XML parse error: {e}")
                return []
            except Exception as e:
                logger.error(f"ArXiv search error: {e}")
                return []

    async def search_by_title_author(
        self,
        title: str,
        first_author: str = ""
    ) -> Optional[Dict]:
        """
        Search for a specific paper by title and optional first author.

        Args:
            title: Paper title
            first_author: First author name (optional)

        Returns:
            Best matching paper or None
        """
        results = await self.search(
            title=title,
            author=first_author,
            max_results=5
        )

        return results[0] if results else None

    async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get a paper by its ArXiv ID.

        Args:
            arxiv_id: ArXiv ID (e.g., "2301.07041" or "hep-th/9901001")

        Returns:
            Paper dict or None
        """
        # Clean ID
        arxiv_id = arxiv_id.strip()
        if arxiv_id.startswith("arXiv:"):
            arxiv_id = arxiv_id[6:]

        params = {
            "id_list": arxiv_id,
            "max_results": 1,
        }

        async with aiohttp.ClientSession() as session:
            try:
                xml_response = await self._make_request(session, params)
                root = ET.fromstring(xml_response)
                entries = root.findall("atom:entry", self.NAMESPACES)

                if entries:
                    return self._parse_entry(entries[0])
                return None

            except Exception as e:
                logger.error(f"ArXiv get by ID error: {e}")
                return None

    async def download_pdf(
        self,
        arxiv_id: str,
        output_path: str
    ) -> bool:
        """
        Download PDF for an ArXiv paper.

        Args:
            arxiv_id: ArXiv ID
            output_path: Path to save PDF

        Returns:
            True if successful, False otherwise
        """
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        async with aiohttp.ClientSession() as session:
            try:
                await self._rate_limit_wait()

                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        with open(output_path, 'wb') as f:
                            f.write(await response.read())
                        logger.info(f"Downloaded PDF to {output_path}")
                        return True
                    else:
                        logger.error(f"PDF download failed: {response.status}")
                        return False

            except Exception as e:
                logger.error(f"PDF download error: {e}")
                return False
