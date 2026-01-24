"""
OpenAlex API Client
===================
Client for OpenAlex API - free open catalog of the global research system.
250M+ works, completely free, no API key required.

API Documentation: https://docs.openalex.org/
"""

import requests
import time
import logging
import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OpenAlexWork:
    """Represents a work from OpenAlex."""
    openalex_id: str
    doi: Optional[str] = None
    title: str = ""
    abstract: str = ""
    year: int = 0
    authors: List[str] = field(default_factory=list)
    venue: str = ""
    pdf_url: Optional[str] = None
    is_oa: bool = False
    citation_count: int = 0
    concepts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'openalex_id': self.openalex_id,
            'doi': self.doi,
            'title': self.title,
            'abstract': self.abstract,
            'year': self.year,
            'authors': self.authors,
            'venue': self.venue,
            'pdf_url': self.pdf_url,
            'is_oa': self.is_oa,
            'citation_count': self.citation_count,
            'concepts': self.concepts,
        }


class OpenAlexClient:
    """
    Client for OpenAlex API.

    Features:
    - No API key required
    - 100K requests/day with polite pool (include email in User-Agent)
    - Rich metadata including OA status, concepts, citations

    Rate Limits:
    - Without email: 10 req/sec, 100K/day
    - With email (polite pool): higher limits
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(
        self,
        email: str = "",
        rate_limit_delay: float = 0.1,
        max_retries: int = 3
    ):
        """
        Initialize OpenAlex client.

        Args:
            email: Email for polite pool (recommended for higher rate limits)
            rate_limit_delay: Delay between requests in seconds
            max_retries: Max retry attempts on failure
        """
        self.email = email
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.request_count = 0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        user_agent = "BiblioHunter/2.0 (Academic Research Tool)"
        if self.email:
            user_agent += f"; mailto:{self.email}"
        return {
            'User-Agent': user_agent,
            'Accept': 'application/json'
        }

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
                    logger.warning(f"OpenAlex rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OpenAlex API error {response.status_code}: {response.text[:200]}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"OpenAlex request error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)

        return None

    def get_work_by_doi(self, doi: str) -> Optional[OpenAlexWork]:
        """
        Get work by DOI.

        Args:
            doi: DOI of the work (e.g., "10.1038/nature12373")

        Returns:
            OpenAlexWork or None if not found
        """
        # Normalize DOI
        doi = doi.strip().lower()
        if doi.startswith('https://doi.org/'):
            doi = doi[16:]
        elif doi.startswith('doi:'):
            doi = doi[4:]

        endpoint = f"works/https://doi.org/{doi}"
        data = self._make_request(endpoint)

        if data:
            return self._parse_work(data)
        return None

    def get_work_by_id(self, openalex_id: str) -> Optional[OpenAlexWork]:
        """
        Get work by OpenAlex ID.

        Args:
            openalex_id: OpenAlex ID (e.g., "W2741809807")

        Returns:
            OpenAlexWork or None if not found
        """
        # Normalize ID
        if openalex_id.startswith('https://openalex.org/'):
            openalex_id = openalex_id.split('/')[-1]

        endpoint = f"works/{openalex_id}"
        data = self._make_request(endpoint)

        if data:
            return self._parse_work(data)
        return None

    def search(
        self,
        query: str,
        limit: int = 25,
        page: int = 1,
        year_range: tuple = None,
        is_oa: bool = None,
        sort_by: str = "relevance_score"
    ) -> List[OpenAlexWork]:
        """
        Search for works.

        Args:
            query: Search query
            limit: Maximum results per page (max 200)
            page: Page number
            year_range: Optional (start_year, end_year) filter
            is_oa: Filter by open access status
            sort_by: Sort field (relevance_score, cited_by_count, publication_date)

        Returns:
            List of OpenAlexWork objects
        """
        params = {
            'search': query,
            'per_page': min(limit, 200),
            'page': page,
            'sort': sort_by
        }

        # Build filter string
        filters = []
        if year_range:
            filters.append(f"publication_year:{year_range[0]}-{year_range[1]}")
        if is_oa is not None:
            filters.append(f"is_oa:{str(is_oa).lower()}")

        if filters:
            params['filter'] = ','.join(filters)

        data = self._make_request('works', params)

        if data and 'results' in data:
            logger.info(f"OpenAlex found {data.get('meta', {}).get('count', 0)} results for: {query[:50]}")
            return [self._parse_work(w) for w in data['results']]

        return []

    def search_by_title(self, title: str, limit: int = 5) -> List[OpenAlexWork]:
        """
        Search for works by title.

        Args:
            title: Paper title
            limit: Maximum results

        Returns:
            List of OpenAlexWork objects
        """
        params = {
            'filter': f'title.search:{title[:200]}',
            'per_page': min(limit, 25)
        }

        data = self._make_request('works', params)

        if data and 'results' in data:
            return [self._parse_work(w) for w in data['results']]

        return []

    def get_citations(
        self,
        openalex_id: str,
        limit: int = 100
    ) -> List[OpenAlexWork]:
        """
        Get works that cite this work.

        Args:
            openalex_id: OpenAlex ID of the cited work
            limit: Maximum citations to return

        Returns:
            List of citing works
        """
        if openalex_id.startswith('https://openalex.org/'):
            openalex_id = openalex_id.split('/')[-1]

        params = {
            'filter': f'cites:{openalex_id}',
            'per_page': min(limit, 200),
            'sort': 'cited_by_count:desc'
        }

        data = self._make_request('works', params)

        if data and 'results' in data:
            return [self._parse_work(w) for w in data['results']]

        return []

    def get_references(
        self,
        openalex_id: str,
        limit: int = 100
    ) -> List[OpenAlexWork]:
        """
        Get works referenced by this work.

        Args:
            openalex_id: OpenAlex ID of the citing work
            limit: Maximum references to return

        Returns:
            List of referenced works
        """
        # First get the work to get referenced_works
        work_data = self._make_request(f"works/{openalex_id}")

        if not work_data:
            return []

        referenced_ids = work_data.get('referenced_works', [])[:limit]

        if not referenced_ids:
            return []

        # Fetch referenced works in batch
        refs = []
        for ref_id in referenced_ids:
            ref_work = self.get_work_by_id(ref_id)
            if ref_work:
                refs.append(ref_work)

        return refs

    def get_related_works(
        self,
        openalex_id: str,
        limit: int = 10
    ) -> List[OpenAlexWork]:
        """
        Get related works based on OpenAlex's related_works field.

        Args:
            openalex_id: OpenAlex ID
            limit: Maximum related works to return

        Returns:
            List of related works
        """
        work_data = self._make_request(f"works/{openalex_id}")

        if not work_data:
            return []

        related_ids = work_data.get('related_works', [])[:limit]

        if not related_ids:
            return []

        related = []
        for rel_id in related_ids:
            rel_work = self.get_work_by_id(rel_id)
            if rel_work:
                related.append(rel_work)

        return related

    def _parse_work(self, data: Dict) -> OpenAlexWork:
        """Parse API response into OpenAlexWork."""
        # Extract DOI
        doi = None
        if data.get('doi'):
            doi = data['doi'].replace('https://doi.org/', '')

        # Extract authors
        authors = []
        for authorship in data.get('authorships', []):
            author = authorship.get('author', {})
            if author.get('display_name'):
                authors.append(author['display_name'])

        # Extract venue
        venue = ""
        primary_location = data.get('primary_location', {}) or {}
        source = primary_location.get('source', {}) or {}
        venue = source.get('display_name', '')

        # Extract PDF URL
        pdf_url = None
        best_oa = data.get('best_oa_location', {}) or {}
        if best_oa.get('pdf_url'):
            pdf_url = best_oa['pdf_url']
        elif primary_location.get('pdf_url'):
            pdf_url = primary_location['pdf_url']

        # Extract concepts
        concepts = []
        for concept in data.get('concepts', [])[:10]:
            if concept.get('display_name'):
                concepts.append(concept['display_name'])

        # Extract abstract (inverted index format)
        abstract = ""
        if data.get('abstract_inverted_index'):
            abstract = self._reconstruct_abstract(data['abstract_inverted_index'])

        return OpenAlexWork(
            openalex_id=data.get('id', '').replace('https://openalex.org/', ''),
            doi=doi,
            title=data.get('title', '') or '',
            abstract=abstract,
            year=data.get('publication_year', 0) or 0,
            authors=authors,
            venue=venue,
            pdf_url=pdf_url,
            is_oa=data.get('is_oa', False),
            citation_count=data.get('cited_by_count', 0) or 0,
            concepts=concepts
        )

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """
        Reconstruct abstract from OpenAlex inverted index format.

        OpenAlex stores abstracts as {word: [positions]} for compression.
        """
        if not inverted_index:
            return ""

        # Create position -> word mapping
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))

        # Sort by position and join
        word_positions.sort(key=lambda x: x[0])
        return ' '.join(word for pos, word in word_positions)

    def get_stats(self) -> Dict[str, int]:
        """Get client statistics."""
        return {
            'total_requests': self.request_count
        }


# Convenience functions
def search_openalex(
    query: str,
    email: str = "",
    limit: int = 25
) -> List[Dict]:
    """
    Quick search function for OpenAlex.

    Args:
        query: Search query
        email: Email for polite pool
        limit: Maximum results

    Returns:
        List of work dictionaries
    """
    client = OpenAlexClient(email=email)
    results = client.search(query, limit=limit)
    return [r.to_dict() for r in results]


def get_openalex_work(
    doi: str,
    email: str = ""
) -> Optional[Dict]:
    """
    Quick function to get work by DOI.

    Args:
        doi: DOI of the work
        email: Email for polite pool

    Returns:
        Work dictionary or None
    """
    client = OpenAlexClient(email=email)
    result = client.get_work_by_doi(doi)
    return result.to_dict() if result else None


if __name__ == "__main__":
    # Test the client
    client = OpenAlexClient()

    # Test DOI lookup
    print("Testing DOI lookup...")
    work = client.get_work_by_doi("10.1038/nature12373")
    if work:
        print(f"Title: {work.title[:60]}...")
        print(f"Year: {work.year}")
        print(f"Authors: {', '.join(work.authors[:3])}...")
        print(f"OA: {work.is_oa}")
        print(f"PDF: {work.pdf_url}")
        print(f"Citations: {work.citation_count}")

    # Test search
    print("\nTesting search...")
    results = client.search("machine learning healthcare", limit=5)
    for r in results:
        print(f"- {r.title[:50]}... ({r.year})")

    print(f"\nStats: {client.get_stats()}")
