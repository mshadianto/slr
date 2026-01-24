"""
Crossref API Client
====================
Client for Crossref API - metadata for 140M+ scholarly works.

API Documentation: https://api.crossref.org/swagger-ui/index.html
"""

import requests
import time
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class CrossrefWork:
    """Represents a work from Crossref."""
    doi: str
    title: str = ""
    abstract: str = ""
    year: int = 0
    authors: List[str] = field(default_factory=list)
    venue: str = ""
    publisher: str = ""
    type: str = ""  # journal-article, book-chapter, etc.
    issn: List[str] = field(default_factory=list)
    references_count: int = 0
    is_referenced_by_count: int = 0
    license_url: Optional[str] = None
    link: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'doi': self.doi,
            'title': self.title,
            'abstract': self.abstract,
            'year': self.year,
            'authors': self.authors,
            'venue': self.venue,
            'publisher': self.publisher,
            'type': self.type,
            'issn': self.issn,
            'references_count': self.references_count,
            'is_referenced_by_count': self.is_referenced_by_count,
            'license_url': self.license_url,
            'link': self.link,
        }


class CrossrefClient:
    """
    Client for Crossref API.

    Features:
    - Free API with optional polite pool
    - 140M+ scholarly works with DOI metadata
    - Reference linking and citation counts

    Rate Limits:
    - Without mailto: 50 req/sec
    - With mailto (polite pool): Higher limits, priority access
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(
        self,
        mailto: str = "",
        rate_limit_delay: float = 0.1,
        max_retries: int = 3
    ):
        """
        Initialize Crossref client.

        Args:
            mailto: Email for polite pool (recommended)
            rate_limit_delay: Delay between requests in seconds
            max_retries: Max retry attempts on failure
        """
        self.mailto = mailto
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.request_count = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            'User-Agent': 'BiblioHunter/2.0 (Academic Research Tool)',
            'Accept': 'application/json'
        }
        return headers

    def _get_params(self, params: Dict = None) -> Dict:
        """Get request parameters with mailto."""
        if params is None:
            params = {}
        if self.mailto:
            params['mailto'] = self.mailto
        return params

    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        params = self._get_params(params)

        for attempt in range(self.max_retries):
            self._rate_limit()

            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30
                )
                self.request_count += 1

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Crossref rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Crossref API error {response.status_code}: {response.text[:200]}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Crossref request error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)

        return None

    def get_work_by_doi(self, doi: str) -> Optional[CrossrefWork]:
        """
        Get work by DOI.

        Args:
            doi: DOI of the work (e.g., "10.1038/nature12373")

        Returns:
            CrossrefWork or None if not found
        """
        # Normalize DOI
        doi = doi.strip()
        if doi.startswith('https://doi.org/'):
            doi = doi[16:]
        elif doi.startswith('doi:'):
            doi = doi[4:]

        # URL encode the DOI
        encoded_doi = quote(doi, safe='')
        endpoint = f"works/{encoded_doi}"

        data = self._make_request(endpoint)

        if data and 'message' in data:
            return self._parse_work(data['message'])
        return None

    def search(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        year_range: tuple = None,
        sort: str = "relevance",
        order: str = "desc",
        type_filter: str = None
    ) -> List[CrossrefWork]:
        """
        Search for works.

        Args:
            query: Search query
            limit: Maximum results (max 1000)
            offset: Offset for pagination
            year_range: Optional (start_year, end_year) filter
            sort: Sort field (relevance, published, indexed, is-referenced-by-count)
            order: Sort order (asc, desc)
            type_filter: Filter by type (journal-article, book-chapter, etc.)

        Returns:
            List of CrossrefWork objects
        """
        params = {
            'query': query,
            'rows': min(limit, 1000),
            'offset': offset,
            'sort': sort,
            'order': order
        }

        # Add filters
        filters = []
        if year_range:
            filters.append(f"from-pub-date:{year_range[0]}")
            filters.append(f"until-pub-date:{year_range[1]}")
        if type_filter:
            filters.append(f"type:{type_filter}")

        if filters:
            params['filter'] = ','.join(filters)

        data = self._make_request('works', params)

        if data and 'message' in data:
            items = data['message'].get('items', [])
            total = data['message'].get('total-results', 0)
            logger.info(f"Crossref found {total} results for: {query[:50]}")
            return [self._parse_work(item) for item in items]

        return []

    def search_by_title(self, title: str, limit: int = 5) -> List[CrossrefWork]:
        """
        Search for works by title.

        Args:
            title: Paper title
            limit: Maximum results

        Returns:
            List of CrossrefWork objects
        """
        params = {
            'query.title': title[:200],
            'rows': min(limit, 25)
        }

        data = self._make_request('works', params)

        if data and 'message' in data:
            items = data['message'].get('items', [])
            return [self._parse_work(item) for item in items]

        return []

    def search_by_author(
        self,
        author: str,
        limit: int = 25
    ) -> List[CrossrefWork]:
        """
        Search for works by author name.

        Args:
            author: Author name
            limit: Maximum results

        Returns:
            List of CrossrefWork objects
        """
        params = {
            'query.author': author,
            'rows': min(limit, 100)
        }

        data = self._make_request('works', params)

        if data and 'message' in data:
            items = data['message'].get('items', [])
            return [self._parse_work(item) for item in items]

        return []

    def get_references(self, doi: str) -> List[Dict]:
        """
        Get references for a work.

        Args:
            doi: DOI of the work

        Returns:
            List of reference dictionaries (may include DOIs)
        """
        work = self.get_work_by_doi(doi)
        if not work:
            return []

        # The references are included in the work data
        doi = doi.strip()
        if doi.startswith('https://doi.org/'):
            doi = doi[16:]

        encoded_doi = quote(doi, safe='')
        endpoint = f"works/{encoded_doi}"

        data = self._make_request(endpoint)

        if data and 'message' in data:
            return data['message'].get('reference', [])

        return []

    def get_works_by_journal(
        self,
        issn: str,
        limit: int = 25
    ) -> List[CrossrefWork]:
        """
        Get works from a specific journal by ISSN.

        Args:
            issn: Journal ISSN
            limit: Maximum results

        Returns:
            List of CrossrefWork objects
        """
        params = {
            'filter': f'issn:{issn}',
            'rows': min(limit, 100),
            'sort': 'published',
            'order': 'desc'
        }

        data = self._make_request('works', params)

        if data and 'message' in data:
            items = data['message'].get('items', [])
            return [self._parse_work(item) for item in items]

        return []

    def _parse_work(self, data: Dict) -> CrossrefWork:
        """Parse API response into CrossrefWork."""
        # Extract title (may be a list)
        title = ""
        if data.get('title'):
            title = data['title'][0] if isinstance(data['title'], list) else data['title']

        # Extract abstract
        abstract = data.get('abstract', '')
        if abstract:
            # Clean XML tags from abstract
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)

        # Extract year from published date
        year = 0
        if data.get('published'):
            date_parts = data['published'].get('date-parts', [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        elif data.get('published-print'):
            date_parts = data['published-print'].get('date-parts', [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        elif data.get('published-online'):
            date_parts = data['published-online'].get('date-parts', [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

        # Extract authors
        authors = []
        for author in data.get('author', []):
            name_parts = []
            if author.get('given'):
                name_parts.append(author['given'])
            if author.get('family'):
                name_parts.append(author['family'])
            if name_parts:
                authors.append(' '.join(name_parts))

        # Extract venue
        venue = ""
        if data.get('container-title'):
            container = data['container-title']
            venue = container[0] if isinstance(container, list) else container

        # Extract license
        license_url = None
        if data.get('license'):
            for lic in data['license']:
                if lic.get('URL'):
                    license_url = lic['URL']
                    break

        # Extract link
        link = None
        if data.get('link'):
            for l in data['link']:
                if l.get('URL'):
                    link = l['URL']
                    break

        # Extract ISSNs
        issn = []
        if data.get('ISSN'):
            issn = data['ISSN'] if isinstance(data['ISSN'], list) else [data['ISSN']]

        return CrossrefWork(
            doi=data.get('DOI', ''),
            title=title,
            abstract=abstract,
            year=year,
            authors=authors,
            venue=venue,
            publisher=data.get('publisher', ''),
            type=data.get('type', ''),
            issn=issn,
            references_count=data.get('references-count', 0) or 0,
            is_referenced_by_count=data.get('is-referenced-by-count', 0) or 0,
            license_url=license_url,
            link=link
        )

    def get_stats(self) -> Dict[str, int]:
        """Get client statistics."""
        return {
            'total_requests': self.request_count
        }


# Convenience functions
def search_crossref(
    query: str,
    mailto: str = "",
    limit: int = 25
) -> List[Dict]:
    """
    Quick search function for Crossref.

    Args:
        query: Search query
        mailto: Email for polite pool
        limit: Maximum results

    Returns:
        List of work dictionaries
    """
    client = CrossrefClient(mailto=mailto)
    results = client.search(query, limit=limit)
    return [r.to_dict() for r in results]


def get_crossref_work(
    doi: str,
    mailto: str = ""
) -> Optional[Dict]:
    """
    Quick function to get work by DOI.

    Args:
        doi: DOI of the work
        mailto: Email for polite pool

    Returns:
        Work dictionary or None
    """
    client = CrossrefClient(mailto=mailto)
    result = client.get_work_by_doi(doi)
    return result.to_dict() if result else None


if __name__ == "__main__":
    # Test the client
    client = CrossrefClient()

    # Test DOI lookup
    print("Testing DOI lookup...")
    work = client.get_work_by_doi("10.1038/nature12373")
    if work:
        print(f"Title: {work.title[:60]}...")
        print(f"Year: {work.year}")
        print(f"Authors: {', '.join(work.authors[:3])}...")
        print(f"Venue: {work.venue}")
        print(f"Publisher: {work.publisher}")
        print(f"Citations: {work.is_referenced_by_count}")
        print(f"References: {work.references_count}")

    # Test search
    print("\nTesting search...")
    results = client.search("machine learning healthcare", limit=5)
    for r in results:
        print(f"- {r.title[:50]}... ({r.year})")

    # Test title search
    print("\nTesting title search...")
    results = client.search_by_title("Attention is all you need", limit=3)
    for r in results:
        print(f"- {r.title[:50]}... ({r.year})")

    print(f"\nStats: {client.get_stats()}")
