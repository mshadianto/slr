"""
BiblioAgent AI - BiblioHunter Enhanced
======================================
Advanced paper retrieval with multi-source PDF acquisition
and intelligent Virtual Full-Text synthesis.

Features:
- Multi-identifier support (DOI, ArXiv, PMID, Semantic Scholar ID)
- Waterfall PDF retrieval (S2 → Unpaywall → CORE → ArXiv)
- Enhanced Virtual Full-Text with TL;DR, references, related papers
- In-memory caching to reduce API calls
- Parallel batch processing with progress callbacks
- PDF download capability
- Title-based search fallback
"""

import requests
import time
import logging
import re
import os
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Callable, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PaperResult:
    """Structured result for paper retrieval."""
    identifier: str
    identifier_type: str  # doi, arxiv, pmid, s2id, title
    title: str = ""
    abstract: str = ""
    year: int = 0
    authors: List[str] = field(default_factory=list)
    venue: str = ""
    pdf_url: Optional[str] = None
    pdf_source: Optional[str] = None  # semantic_scholar, unpaywall, core, arxiv
    full_text: Optional[str] = None
    full_text_source: str = "none"  # semantic_scholar_oa, unpaywall, core, arxiv, virtual_fulltext
    retrieval_confidence: float = 0.0
    citation_count: int = 0
    influential_citations: int = 0
    is_virtual_fulltext: bool = False
    citation_contexts_count: int = 0
    tldr: Optional[str] = None
    references_count: int = 0
    related_papers: List[Dict] = field(default_factory=list)
    quality_score: float = 0.0
    s2_paper_id: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'identifier': self.identifier,
            'identifier_type': self.identifier_type,
            'doi': self.identifier if self.identifier_type == 'doi' else None,
            'title': self.title,
            'abstract': self.abstract,
            'year': self.year,
            'authors': self.authors,
            'venue': self.venue,
            'pdf_url': self.pdf_url,
            'pdf_source': self.pdf_source,
            'full_text': self.full_text,
            'full_text_source': self.full_text_source,
            'retrieval_confidence': self.retrieval_confidence,
            'citation_count': self.citation_count,
            'influential_citations': self.influential_citations,
            'is_virtual_fulltext': self.is_virtual_fulltext,
            'citation_contexts_count': self.citation_contexts_count,
            'tldr': self.tldr,
            'references_count': self.references_count,
            'related_papers': self.related_papers,
            'quality_score': self.quality_score,
            's2_paper_id': self.s2_paper_id,
            'retrieved_at': self.retrieved_at,
        }


class BiblioHunterCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_hours: int = 24):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = timedelta(hours=ttl_hours)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """Cache a value."""
        self._cache[key] = (value, datetime.now())

    def clear(self):
        """Clear all cached values."""
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class BiblioHunter:
    """
    Enhanced paper retrieval with multi-source PDF acquisition
    and intelligent Virtual Full-Text generation.

    Supports:
    - DOI lookup
    - ArXiv ID lookup
    - PMID lookup
    - Semantic Scholar Paper ID lookup
    - Title-based search fallback

    PDF Sources (waterfall):
    1. Semantic Scholar Open Access
    2. Unpaywall
    3. CORE
    4. ArXiv

    When no PDF available:
    - Generates Virtual Full-Text from abstract + citation contexts + TL;DR
    """

    def __init__(
        self,
        s2_api_key: str = None,
        unpaywall_email: str = None,
        core_api_key: str = None,
        enable_cache: bool = True,
        cache_ttl_hours: int = 24,
        download_dir: str = None
    ):
        """
        Initialize BiblioHunter.

        Args:
            s2_api_key: Semantic Scholar API key (optional but recommended)
            unpaywall_email: Email for Unpaywall API (required for Unpaywall)
            core_api_key: CORE API key (optional)
            enable_cache: Whether to cache results
            cache_ttl_hours: Cache TTL in hours
            download_dir: Directory for downloaded PDFs
        """
        self.s2_api_key = s2_api_key
        self.unpaywall_email = unpaywall_email
        self.core_api_key = core_api_key

        self.s2_base_url = "https://api.semanticscholar.org/graph/v1"
        self.unpaywall_base_url = "https://api.unpaywall.org/v2"
        self.core_base_url = "https://api.core.ac.uk/v3"
        self.arxiv_base_url = "http://export.arxiv.org/api/query"

        self.request_count = 0
        self.last_request_time = 0

        self.cache = BiblioHunterCache(ttl_hours=cache_ttl_hours) if enable_cache else None
        self.download_dir = Path(download_dir) if download_dir else None
        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)

        # Stats tracking
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'pdf_found': 0,
            'virtual_fulltext_generated': 0,
            'not_found': 0,
        }

    def _rate_limit(self, min_interval: float = 1.1):
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _get_headers(self, api_type: str = 's2') -> Dict:
        """Get headers for API requests."""
        headers = {'User-Agent': 'BiblioHunter/2.0 (Academic Research Tool)'}
        if api_type == 's2' and self.s2_api_key:
            headers['x-api-key'] = self.s2_api_key
        elif api_type == 'core' and self.core_api_key:
            headers['Authorization'] = f'Bearer {self.core_api_key}'
        return headers

    def _detect_identifier_type(self, identifier: str) -> Tuple[str, str]:
        """
        Detect the type of identifier and normalize it.

        Returns:
            Tuple of (normalized_identifier, identifier_type)
        """
        identifier = identifier.strip()

        # ArXiv ID patterns
        arxiv_patterns = [
            r'^arxiv:(\d{4}\.\d{4,5})(v\d+)?$',  # arxiv:2303.08774
            r'^(\d{4}\.\d{4,5})(v\d+)?$',  # 2303.08774
            r'^https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?',  # URL
            r'^arXiv:(\d{4}\.\d{4,5})(v\d+)?$',  # arXiv:2303.08774
        ]
        for pattern in arxiv_patterns:
            match = re.match(pattern, identifier, re.IGNORECASE)
            if match:
                return match.group(1), 'arxiv'

        # Old ArXiv format (e.g., hep-ph/9901312)
        old_arxiv = re.match(r'^([a-z-]+/\d{7})$', identifier, re.IGNORECASE)
        if old_arxiv:
            return old_arxiv.group(1), 'arxiv'

        # DOI patterns
        doi_patterns = [
            r'^https?://doi\.org/(10\.\d{4,}/[^\s]+)$',  # URL
            r'^doi:(10\.\d{4,}/[^\s]+)$',  # doi:10.xxxx/...
            r'^(10\.\d{4,}/[^\s]+)$',  # 10.xxxx/...
        ]
        for pattern in doi_patterns:
            match = re.match(pattern, identifier, re.IGNORECASE)
            if match:
                return match.group(1), 'doi'

        # PMID
        pmid_match = re.match(r'^(?:pmid:?)?(\d{7,8})$', identifier, re.IGNORECASE)
        if pmid_match:
            return pmid_match.group(1), 'pmid'

        # Semantic Scholar Paper ID (40-char hex)
        if re.match(r'^[a-f0-9]{40}$', identifier, re.IGNORECASE):
            return identifier.lower(), 's2id'

        # Assume it's a title for search
        if len(identifier) > 20 and ' ' in identifier:
            return identifier, 'title'

        # Default to DOI format attempt
        return identifier, 'doi'

    def hunt(
        self,
        identifier: str,
        enable_waterfall: bool = True,
        enable_virtual_fulltext: bool = True,
        max_retries: int = 3
    ) -> Optional[PaperResult]:
        """
        Hunt for a paper using any identifier type.

        Args:
            identifier: DOI, ArXiv ID, PMID, S2 Paper ID, or title
            enable_waterfall: Try multiple PDF sources
            enable_virtual_fulltext: Generate VFT if no PDF found
            max_retries: Max retry attempts

        Returns:
            PaperResult or None if not found
        """
        self.stats['total_requests'] += 1

        # Check cache
        cache_key = hashlib.md5(identifier.encode()).hexdigest()
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.stats['cache_hits'] += 1
                logger.info(f"Cache hit for {identifier[:50]}")
                return cached

        # Detect identifier type
        normalized_id, id_type = self._detect_identifier_type(identifier)
        logger.info(f"Hunting paper: {normalized_id} (type: {id_type})")

        # Get paper from Semantic Scholar
        paper_data = self._fetch_from_semantic_scholar(normalized_id, id_type, max_retries)

        if not paper_data:
            # Try title search as fallback
            if id_type != 'title':
                logger.info(f"Trying title search fallback for {identifier[:50]}")
                paper_data = self._search_by_title(identifier)

            if not paper_data:
                self.stats['not_found'] += 1
                logger.warning(f"Paper not found: {identifier}")
                return None

        # Build result
        result = self._build_paper_result(normalized_id, id_type, paper_data)

        # Check for PDF availability
        if paper_data.get('openAccessPdf'):
            result.pdf_url = paper_data['openAccessPdf'].get('url')
            result.pdf_source = 'semantic_scholar'
            result.full_text_source = 'semantic_scholar_oa'
            result.retrieval_confidence = 1.0
            self.stats['pdf_found'] += 1
            logger.info(f"PDF found via Semantic Scholar: {result.title[:50]}")

        # Waterfall PDF retrieval
        elif enable_waterfall and id_type == 'doi':
            result = self._waterfall_pdf_retrieval(result, normalized_id)

        # Generate Virtual Full-Text if no PDF
        if not result.pdf_url and enable_virtual_fulltext:
            result = self._generate_virtual_fulltext(result, paper_data)
            self.stats['virtual_fulltext_generated'] += 1

        # Calculate quality score
        result.quality_score = self._calculate_quality_score(result)

        # Cache result
        if self.cache:
            self.cache.set(cache_key, result)

        return result

    def _fetch_from_semantic_scholar(
        self,
        identifier: str,
        id_type: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """Fetch paper data from Semantic Scholar."""

        # Build endpoint based on identifier type
        if id_type == 'doi':
            endpoint = f"{self.s2_base_url}/paper/DOI:{identifier}"
        elif id_type == 'arxiv':
            endpoint = f"{self.s2_base_url}/paper/ARXIV:{identifier}"
        elif id_type == 'pmid':
            endpoint = f"{self.s2_base_url}/paper/PMID:{identifier}"
        elif id_type == 's2id':
            endpoint = f"{self.s2_base_url}/paper/{identifier}"
        else:
            return None

        params = {
            'fields': 'paperId,title,abstract,year,authors,venue,openAccessPdf,'
                      'citationCount,influentialCitationCount,tldr,referenceCount,'
                      'fieldsOfStudy,publicationTypes,externalIds'
        }

        for attempt in range(max_retries):
            self._rate_limit()

            try:
                response = requests.get(
                    endpoint,
                    params=params,
                    headers=self._get_headers('s2'),
                    timeout=30
                )
                self.request_count += 1

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"S2 API error {response.status_code}")
                    return None

            except Exception as e:
                logger.error(f"Error fetching from S2: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        return None

    def _search_by_title(self, title: str, limit: int = 5) -> Optional[Dict]:
        """Search for paper by title as fallback."""
        self._rate_limit()

        endpoint = f"{self.s2_base_url}/paper/search"
        params = {
            'query': title[:200],  # Limit query length
            'limit': limit,
            'fields': 'paperId,title,abstract,year,authors,venue,openAccessPdf,'
                      'citationCount,influentialCitationCount,tldr,referenceCount'
        }

        try:
            response = requests.get(
                endpoint,
                params=params,
                headers=self._get_headers('s2'),
                timeout=30
            )
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])

                if papers:
                    # Return best match (first result)
                    best = papers[0]
                    logger.info(f"Found via title search: {best.get('title', '')[:50]}")
                    return best
        except Exception as e:
            logger.error(f"Title search error: {e}")

        return None

    def _build_paper_result(
        self,
        identifier: str,
        id_type: str,
        data: Dict
    ) -> PaperResult:
        """Build PaperResult from API data."""

        # Extract TL;DR
        tldr = None
        if data.get('tldr'):
            tldr = data['tldr'].get('text')

        return PaperResult(
            identifier=identifier,
            identifier_type=id_type,
            title=data.get('title', ''),
            abstract=data.get('abstract', ''),
            year=data.get('year', 0) or 0,
            authors=[a.get('name', '') for a in data.get('authors', [])],
            venue=data.get('venue', ''),
            citation_count=data.get('citationCount', 0) or 0,
            influential_citations=data.get('influentialCitationCount', 0) or 0,
            tldr=tldr,
            references_count=data.get('referenceCount', 0) or 0,
            s2_paper_id=data.get('paperId'),
        )

    def _waterfall_pdf_retrieval(
        self,
        result: PaperResult,
        doi: str
    ) -> PaperResult:
        """Try multiple sources to find PDF."""

        # 1. Try Unpaywall
        if self.unpaywall_email:
            pdf_url = self._try_unpaywall(doi)
            if pdf_url:
                result.pdf_url = pdf_url
                result.pdf_source = 'unpaywall'
                result.full_text_source = 'unpaywall'
                result.retrieval_confidence = 1.0
                self.stats['pdf_found'] += 1
                logger.info(f"PDF found via Unpaywall: {doi}")
                return result

        # 2. Try CORE
        if self.core_api_key:
            pdf_url = self._try_core(doi)
            if pdf_url:
                result.pdf_url = pdf_url
                result.pdf_source = 'core'
                result.full_text_source = 'core'
                result.retrieval_confidence = 0.95
                self.stats['pdf_found'] += 1
                logger.info(f"PDF found via CORE: {doi}")
                return result

        # 3. Try ArXiv (check if paper has ArXiv version)
        arxiv_url = self._try_arxiv_for_doi(doi, result.title)
        if arxiv_url:
            result.pdf_url = arxiv_url
            result.pdf_source = 'arxiv'
            result.full_text_source = 'arxiv'
            result.retrieval_confidence = 0.9
            self.stats['pdf_found'] += 1
            logger.info(f"PDF found via ArXiv: {doi}")
            return result

        return result

    def _try_unpaywall(self, doi: str) -> Optional[str]:
        """Try to get PDF from Unpaywall."""
        if not self.unpaywall_email:
            return None

        self._rate_limit(0.5)  # Unpaywall allows faster requests

        try:
            url = f"{self.unpaywall_base_url}/{doi}"
            params = {'email': self.unpaywall_email}
            response = requests.get(url, params=params, timeout=15)
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                # Get best OA location
                best_oa = data.get('best_oa_location')
                if best_oa and best_oa.get('url_for_pdf'):
                    return best_oa['url_for_pdf']
        except Exception as e:
            logger.debug(f"Unpaywall error for {doi}: {e}")

        return None

    def _try_core(self, doi: str) -> Optional[str]:
        """Try to get PDF from CORE."""
        if not self.core_api_key:
            return None

        self._rate_limit()

        try:
            url = f"{self.core_base_url}/search/works"
            params = {'q': f'doi:"{doi}"', 'limit': 1}
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers('core'),
                timeout=15
            )
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    download_url = results[0].get('downloadUrl')
                    if download_url:
                        return download_url
        except Exception as e:
            logger.debug(f"CORE error for {doi}: {e}")

        return None

    def _try_arxiv_for_doi(self, doi: str, title: str) -> Optional[str]:
        """Search ArXiv for a paper by title."""
        if not title:
            return None

        self._rate_limit(3)  # ArXiv requires 3s between requests

        try:
            # Search by title
            clean_title = re.sub(r'[^\w\s]', '', title)[:100]
            params = {
                'search_query': f'ti:"{clean_title}"',
                'max_results': 3
            }
            response = requests.get(self.arxiv_base_url, params=params, timeout=15)
            self.request_count += 1

            if response.status_code == 200:
                # Parse Atom feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}

                entries = root.findall('atom:entry', ns)
                for entry in entries:
                    arxiv_title = entry.find('atom:title', ns)
                    if arxiv_title is not None:
                        # Check title similarity
                        arxiv_title_clean = re.sub(r'\s+', ' ', arxiv_title.text).strip()
                        if self._title_similarity(title, arxiv_title_clean) > 0.8:
                            # Get PDF link
                            for link in entry.findall('atom:link', ns):
                                if link.get('title') == 'pdf':
                                    return link.get('href')
        except Exception as e:
            logger.debug(f"ArXiv search error: {e}")

        return None

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity."""
        t1 = set(title1.lower().split())
        t2 = set(title2.lower().split())

        if not t1 or not t2:
            return 0.0

        intersection = len(t1 & t2)
        union = len(t1 | t2)
        return intersection / union if union > 0 else 0.0

    def _generate_virtual_fulltext(
        self,
        result: PaperResult,
        paper_data: Dict
    ) -> PaperResult:
        """Generate Virtual Full-Text content."""
        logger.info(f"Generating Virtual Full-Text for: {result.title[:50]}")

        content_sections = []

        # 1. TL;DR Summary
        if result.tldr:
            content_sections.append(f"## TL;DR\n{result.tldr}")

        # 2. Abstract
        if result.abstract:
            content_sections.append(f"## ABSTRACT\n{result.abstract}")

        # 3. Fetch citation contexts
        citation_contexts = []
        if result.s2_paper_id:
            citation_contexts = self._get_citation_contexts(result.s2_paper_id)

        if citation_contexts:
            content_sections.append("\n## CITATION CONTEXTS (How others describe this work)")
            for i, ctx in enumerate(citation_contexts[:12], 1):
                content_sections.append(f"\n### Context {i}")
                content_sections.append(f"From: {ctx['citing_paper']}")
                content_sections.append(f'"{ctx["context"]}"')
            result.citation_contexts_count = len(citation_contexts)

        # 4. Fetch related papers
        if result.s2_paper_id:
            related = self._get_related_papers(result.s2_paper_id)
            if related:
                result.related_papers = related[:5]
                content_sections.append("\n## RELATED PAPERS")
                for rp in related[:5]:
                    content_sections.append(f"- {rp['title']} ({rp['year']})")

        # 5. Key references (if available)
        if result.s2_paper_id:
            refs = self._get_key_references(result.s2_paper_id)
            if refs:
                content_sections.append("\n## KEY REFERENCES")
                for ref in refs[:8]:
                    content_sections.append(f"- {ref['title']} ({ref['year']})")

        # Combine content
        result.full_text = "\n".join(content_sections)
        result.full_text_source = 'virtual_fulltext'
        result.is_virtual_fulltext = True

        # Calculate confidence based on content richness
        confidence = 0.5  # Base
        if result.abstract:
            confidence += 0.1
        if result.tldr:
            confidence += 0.1
        if citation_contexts:
            confidence += min(0.2, len(citation_contexts) * 0.02)
        if result.related_papers:
            confidence += 0.1

        result.retrieval_confidence = min(0.85, confidence)

        return result

    def _get_citation_contexts(self, paper_id: str, limit: int = 50) -> List[Dict]:
        """Fetch citation contexts with offset search."""
        citation_contexts = []
        offsets_to_try = [0, 100, 500, 1000]

        for offset in offsets_to_try:
            if len(citation_contexts) >= 12:
                break

            self._rate_limit()

            try:
                endpoint = f"{self.s2_base_url}/paper/{paper_id}/citations"
                params = {
                    'fields': 'contexts,title,year',
                    'limit': limit,
                    'offset': offset
                }

                response = requests.get(
                    endpoint,
                    params=params,
                    headers=self._get_headers('s2'),
                    timeout=30
                )
                self.request_count += 1

                if response.status_code == 200:
                    data = response.json()

                    for item in data.get('data', []):
                        contexts = item.get('contexts', []) or []
                        citing_paper = item.get('citingPaper', {})
                        title = citing_paper.get('title', 'Unknown')
                        year = citing_paper.get('year', '')

                        for ctx in contexts[:2]:
                            if ctx and len(ctx) > 50:
                                citation_contexts.append({
                                    'citing_paper': f"{title} ({year})" if year else title,
                                    'context': ctx,
                                    'year': year
                                })

                        if len(citation_contexts) >= 15:
                            break

                elif response.status_code == 429:
                    time.sleep(2)

            except Exception as e:
                logger.debug(f"Error fetching citations: {e}")

        logger.info(f"Fetched {len(citation_contexts)} citation contexts")
        return citation_contexts[:15]

    def _get_related_papers(self, paper_id: str) -> List[Dict]:
        """Fetch related/recommended papers."""
        self._rate_limit()

        try:
            endpoint = f"{self.s2_base_url}/recommendations/v1/papers/forpaper/{paper_id}"
            params = {'fields': 'title,year,authors,citationCount', 'limit': 10}

            response = requests.get(
                endpoint,
                params=params,
                headers=self._get_headers('s2'),
                timeout=15
            )
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        'title': p.get('title', ''),
                        'year': p.get('year', 0),
                        'authors': [a.get('name', '') for a in p.get('authors', [])[:3]],
                        'citations': p.get('citationCount', 0)
                    }
                    for p in data.get('recommendedPapers', [])
                ]
        except Exception as e:
            logger.debug(f"Error fetching related papers: {e}")

        return []

    def _get_key_references(self, paper_id: str) -> List[Dict]:
        """Fetch key references from the paper."""
        self._rate_limit()

        try:
            endpoint = f"{self.s2_base_url}/paper/{paper_id}/references"
            params = {
                'fields': 'title,year,citationCount,isInfluential',
                'limit': 20
            }

            response = requests.get(
                endpoint,
                params=params,
                headers=self._get_headers('s2'),
                timeout=15
            )
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                refs = []

                for item in data.get('data', []):
                    cited = item.get('citedPaper', {})
                    if cited.get('title'):
                        refs.append({
                            'title': cited.get('title', ''),
                            'year': cited.get('year', 0),
                            'citations': cited.get('citationCount', 0),
                            'influential': item.get('isInfluential', False)
                        })

                # Sort by influential first, then by citations
                refs.sort(key=lambda x: (not x['influential'], -x['citations']))
                return refs[:10]

        except Exception as e:
            logger.debug(f"Error fetching references: {e}")

        return []

    def _calculate_quality_score(self, result: PaperResult) -> float:
        """Calculate quality score for the retrieval result."""
        score = 0.0

        # Base score from retrieval confidence
        score += result.retrieval_confidence * 0.4

        # Citation impact
        if result.citation_count > 0:
            citation_score = min(1.0, result.citation_count / 100) * 0.2
            score += citation_score

        # Content completeness
        if result.abstract:
            score += 0.1
        if result.tldr:
            score += 0.05
        if result.citation_contexts_count > 5:
            score += 0.1
        elif result.citation_contexts_count > 0:
            score += 0.05

        # PDF availability bonus
        if result.pdf_url:
            score += 0.15

        return min(1.0, score)

    def download_pdf(
        self,
        result: PaperResult,
        filename: str = None
    ) -> Optional[Path]:
        """Download PDF if available."""
        if not result.pdf_url:
            logger.warning("No PDF URL available")
            return None

        if not self.download_dir:
            logger.warning("Download directory not configured")
            return None

        # Generate filename
        if not filename:
            safe_title = re.sub(r'[^\w\s-]', '', result.title)[:50]
            filename = f"{safe_title}_{result.year}.pdf"

        filepath = self.download_dir / filename

        try:
            response = requests.get(
                result.pdf_url,
                headers={'User-Agent': 'BiblioHunter/2.0'},
                timeout=60,
                stream=True
            )

            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Downloaded PDF: {filepath}")
                return filepath
            else:
                logger.warning(f"Failed to download PDF: {response.status_code}")

        except Exception as e:
            logger.error(f"PDF download error: {e}")

        return None

    def batch_hunt(
        self,
        identifiers: List[str],
        max_workers: int = 3,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> List[PaperResult]:
        """
        Hunt multiple papers with parallel processing.

        Args:
            identifiers: List of DOIs/ArXiv IDs/titles
            max_workers: Number of parallel workers
            progress_callback: Callback(current, total, message)

        Returns:
            List of PaperResult objects
        """
        results = []
        total = len(identifiers)
        completed = 0

        # Use ThreadPoolExecutor for parallel requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_id = {
                executor.submit(self.hunt, identifier): identifier
                for identifier in identifiers
            }

            # Process completed tasks
            for future in as_completed(future_to_id):
                identifier = future_to_id[future]
                completed += 1

                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        status = "found" if result.pdf_url else "VFT"
                    else:
                        status = "not found"

                    if progress_callback:
                        progress_callback(
                            completed,
                            total,
                            f"{status}: {identifier[:40]}"
                        )

                except Exception as e:
                    logger.error(f"Error processing {identifier}: {e}")
                    if progress_callback:
                        progress_callback(completed, total, f"error: {identifier[:40]}")

        return results

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_range: Tuple[int, int] = None
    ) -> List[Dict]:
        """
        Search for papers by keyword query.

        Args:
            query: Search query
            limit: Maximum results
            year_range: Optional (start_year, end_year) filter

        Returns:
            List of paper dicts
        """
        self._rate_limit()

        endpoint = f"{self.s2_base_url}/paper/search"
        params = {
            'query': query,
            'limit': min(limit, 100),
            'fields': 'paperId,externalIds,title,abstract,year,authors,venue,'
                      'openAccessPdf,citationCount,tldr'
        }

        if year_range:
            params['year'] = f"{year_range[0]}-{year_range[1]}"

        try:
            response = requests.get(
                endpoint,
                params=params,
                headers=self._get_headers('s2'),
                timeout=30
            )
            self.request_count += 1

            if response.status_code == 200:
                data = response.json()
                papers = []

                for item in data.get('data', []):
                    # Extract DOI if available
                    external_ids = item.get('externalIds', {}) or {}
                    doi = external_ids.get('DOI')
                    arxiv_id = external_ids.get('ArXiv')

                    papers.append({
                        'paper_id': item.get('paperId', ''),
                        'doi': doi,
                        'arxiv_id': arxiv_id,
                        'title': item.get('title', ''),
                        'abstract': item.get('abstract', ''),
                        'year': item.get('year', 0),
                        'authors': [a.get('name', '') for a in item.get('authors', [])],
                        'venue': item.get('venue', ''),
                        'has_pdf': bool(item.get('openAccessPdf')),
                        'citation_count': item.get('citationCount', 0),
                        'tldr': item.get('tldr', {}).get('text') if item.get('tldr') else None,
                    })

                logger.info(f"Found {len(papers)} papers for query: {query[:50]}")
                return papers
            else:
                logger.error(f"Search error {response.status_code}")

        except Exception as e:
            logger.error(f"Search error: {e}")

        return []

    def get_stats(self) -> Dict:
        """Get retrieval statistics."""
        return {
            **self.stats,
            'cache_size': self.cache.size if self.cache else 0,
            'api_requests': self.request_count,
        }

    # Backwards compatibility methods
    def get_paper_data(self, doi: str, max_retries: int = 3) -> Optional[Dict]:
        """Legacy method - use hunt() instead."""
        result = self.hunt(doi, max_retries=max_retries)
        return result.to_dict() if result else None

    def batch_get_papers(self, dois: List[str]) -> List[Dict]:
        """Legacy method - use batch_hunt() instead."""
        results = self.batch_hunt(dois)
        return [r.to_dict() for r in results]


# Convenience functions
def hunt_paper(
    identifier: str,
    s2_api_key: str = None,
    unpaywall_email: str = None
) -> Optional[Dict]:
    """
    Quick function to hunt for a paper.

    Args:
        identifier: DOI, ArXiv ID, or title
        s2_api_key: Optional Semantic Scholar API key
        unpaywall_email: Optional email for Unpaywall

    Returns:
        Paper data dict or None
    """
    hunter = BiblioHunter(
        s2_api_key=s2_api_key,
        unpaywall_email=unpaywall_email
    )
    result = hunter.hunt(identifier)
    return result.to_dict() if result else None


def batch_hunt_papers(
    identifiers: List[str],
    s2_api_key: str = None,
    unpaywall_email: str = None,
    max_workers: int = 3
) -> List[Dict]:
    """
    Hunt multiple papers in parallel.

    Args:
        identifiers: List of DOIs/ArXiv IDs/titles
        s2_api_key: Optional Semantic Scholar API key
        unpaywall_email: Optional email for Unpaywall
        max_workers: Parallel workers

    Returns:
        List of paper data dicts
    """
    hunter = BiblioHunter(
        s2_api_key=s2_api_key,
        unpaywall_email=unpaywall_email
    )
    results = hunter.batch_hunt(identifiers, max_workers=max_workers)
    return [r.to_dict() for r in results]


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv

    load_dotenv()

    hunter = BiblioHunter(
        s2_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        unpaywall_email=os.getenv("UNPAYWALL_EMAIL"),
    )

    # Test different identifier types
    test_ids = [
        "10.18653/v1/N19-1423",  # BERT DOI
        "2303.08774",  # GPT-4 ArXiv
        "attention is all you need",  # Title search
    ]

    for identifier in test_ids:
        print(f"\n{'='*60}")
        print(f"Hunting: {identifier}")
        result = hunter.hunt(identifier)

        if result:
            print(f"Title: {result.title[:60]}...")
            print(f"Type: {result.identifier_type}")
            print(f"Source: {result.full_text_source}")
            print(f"Confidence: {result.retrieval_confidence:.2f}")
            print(f"Quality Score: {result.quality_score:.2f}")
            if result.pdf_url:
                print(f"PDF: {result.pdf_url[:60]}...")
            if result.is_virtual_fulltext:
                print(f"VFT Contexts: {result.citation_contexts_count}")
        else:
            print("Not found")

    # Print stats
    print(f"\n{'='*60}")
    print("Stats:", hunter.get_stats())
