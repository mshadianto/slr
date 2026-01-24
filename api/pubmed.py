"""
PubMed/NCBI API Client
======================
Client for PubMed E-utilities API - 35M+ biomedical citations.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import requests
import time
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PubMedArticle:
    """Represents an article from PubMed."""
    pmid: str
    doi: Optional[str] = None
    pmc_id: Optional[str] = None
    title: str = ""
    abstract: str = ""
    year: int = 0
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    mesh_terms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    publication_types: List[str] = field(default_factory=list)
    pmc_pdf_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pmid': self.pmid,
            'doi': self.doi,
            'pmc_id': self.pmc_id,
            'title': self.title,
            'abstract': self.abstract,
            'year': self.year,
            'authors': self.authors,
            'journal': self.journal,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'mesh_terms': self.mesh_terms,
            'keywords': self.keywords,
            'publication_types': self.publication_types,
            'pmc_pdf_url': self.pmc_pdf_url,
        }


class PubMedClient:
    """
    Client for PubMed E-utilities API.

    Features:
    - 35M+ biomedical literature citations
    - MeSH term indexing
    - PubMed Central (PMC) free full-text access

    Rate Limits:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        api_key: str = None,
        email: str = "",
        rate_limit_delay: float = 0.35,
        max_retries: int = 3
    ):
        """
        Initialize PubMed client.

        Args:
            api_key: NCBI API key (optional, increases rate limit)
            email: Email for NCBI (recommended)
            rate_limit_delay: Delay between requests in seconds
            max_retries: Max retry attempts on failure
        """
        self.api_key = api_key
        self.email = email
        # Adjust rate limit based on API key
        self.rate_limit_delay = 0.1 if api_key else rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.request_count = 0

    def _get_base_params(self) -> Dict:
        """Get base request parameters."""
        params = {'db': 'pubmed', 'retmode': 'xml'}
        if self.api_key:
            params['api_key'] = self.api_key
        if self.email:
            params['email'] = self.email
        return params

    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[str]:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        if params is None:
            params = {}
        params.update(self._get_base_params())

        for attempt in range(self.max_retries):
            self._rate_limit()

            try:
                response = requests.get(url, params=params, timeout=30)
                self.request_count += 1

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"PubMed rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"PubMed API error {response.status_code}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"PubMed request error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)

        return None

    def search(
        self,
        query: str,
        limit: int = 25,
        year_range: tuple = None,
        sort: str = "relevance"
    ) -> List[str]:
        """
        Search PubMed and return PMIDs.

        Args:
            query: Search query (supports PubMed syntax)
            limit: Maximum results
            year_range: Optional (start_year, end_year) filter
            sort: Sort by (relevance, pub_date, author, journal)

        Returns:
            List of PMIDs
        """
        # Build query with date filter
        full_query = query
        if year_range:
            full_query += f" AND {year_range[0]}:{year_range[1]}[dp]"

        params = {
            'term': full_query,
            'retmax': min(limit, 10000),
            'sort': sort,
            'usehistory': 'n'
        }

        xml_data = self._make_request('esearch.fcgi', params)

        if not xml_data:
            return []

        try:
            root = ET.fromstring(xml_data)
            pmids = [id_elem.text for id_elem in root.findall('.//Id') if id_elem.text]
            total = root.find('.//Count')
            total_count = int(total.text) if total is not None else 0
            logger.info(f"PubMed found {total_count} results for: {query[:50]}")
            return pmids

        except ET.ParseError as e:
            logger.error(f"PubMed XML parse error: {e}")
            return []

    def fetch_articles(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch full article details for PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []

        # Batch fetch (max 200 per request)
        all_articles = []
        batch_size = 200

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            params = {
                'id': ','.join(batch),
                'rettype': 'xml'
            }

            xml_data = self._make_request('efetch.fcgi', params)

            if xml_data:
                articles = self._parse_articles(xml_data)
                all_articles.extend(articles)

        return all_articles

    def get_article_by_pmid(self, pmid: str) -> Optional[PubMedArticle]:
        """
        Get article by PMID.

        Args:
            pmid: PubMed ID

        Returns:
            PubMedArticle or None
        """
        articles = self.fetch_articles([pmid])
        return articles[0] if articles else None

    def get_article_by_doi(self, doi: str) -> Optional[PubMedArticle]:
        """
        Get article by DOI.

        Args:
            doi: DOI

        Returns:
            PubMedArticle or None
        """
        # Clean DOI
        doi = doi.strip()
        if doi.startswith('https://doi.org/'):
            doi = doi[16:]
        elif doi.startswith('doi:'):
            doi = doi[4:]

        # Search by DOI
        pmids = self.search(f'{doi}[doi]', limit=1)

        if pmids:
            return self.get_article_by_pmid(pmids[0])
        return None

    def search_and_fetch(
        self,
        query: str,
        limit: int = 25,
        year_range: tuple = None
    ) -> List[PubMedArticle]:
        """
        Search and fetch articles in one call.

        Args:
            query: Search query
            limit: Maximum results
            year_range: Optional date filter

        Returns:
            List of PubMedArticle objects
        """
        pmids = self.search(query, limit=limit, year_range=year_range)
        return self.fetch_articles(pmids)

    def get_pmc_fulltext_url(self, pmc_id: str) -> Optional[str]:
        """
        Get PubMed Central full-text PDF URL.

        Args:
            pmc_id: PMC ID (e.g., "PMC1234567")

        Returns:
            PDF URL or None
        """
        if not pmc_id:
            return None

        # Normalize PMC ID
        pmc_id = pmc_id.upper()
        if not pmc_id.startswith('PMC'):
            pmc_id = f'PMC{pmc_id}'

        # PMC PDF URL pattern
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"

    def get_related_articles(
        self,
        pmid: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get related articles using PubMed's related articles feature.

        Args:
            pmid: PubMed ID
            limit: Maximum related articles

        Returns:
            List of related PMIDs
        """
        params = {
            'dbfrom': 'pubmed',
            'id': pmid,
            'linkname': 'pubmed_pubmed',
            'retmax': limit
        }

        xml_data = self._make_request('elink.fcgi', params)

        if not xml_data:
            return []

        try:
            root = ET.fromstring(xml_data)
            pmids = []
            for link_set in root.findall('.//LinkSetDb'):
                if link_set.find('LinkName').text == 'pubmed_pubmed':
                    for link in link_set.findall('.//Link/Id'):
                        if link.text and link.text != pmid:
                            pmids.append(link.text)
            return pmids[:limit]

        except ET.ParseError as e:
            logger.error(f"PubMed XML parse error: {e}")
            return []

    def get_citing_articles(
        self,
        pmid: str,
        limit: int = 100
    ) -> List[str]:
        """
        Get articles that cite this article using PubMed Central.

        Args:
            pmid: PubMed ID
            limit: Maximum citing articles

        Returns:
            List of citing PMIDs
        """
        params = {
            'dbfrom': 'pubmed',
            'db': 'pubmed',
            'id': pmid,
            'linkname': 'pubmed_pubmed_citedin',
            'retmax': limit
        }

        xml_data = self._make_request('elink.fcgi', params)

        if not xml_data:
            return []

        try:
            root = ET.fromstring(xml_data)
            pmids = []
            for link in root.findall('.//Link/Id'):
                if link.text and link.text != pmid:
                    pmids.append(link.text)
            return pmids[:limit]

        except ET.ParseError as e:
            logger.error(f"PubMed XML parse error: {e}")
            return []

    def _parse_articles(self, xml_data: str) -> List[PubMedArticle]:
        """Parse efetch XML response into PubMedArticle objects."""
        articles = []

        try:
            root = ET.fromstring(xml_data)

            for article_elem in root.findall('.//PubmedArticle'):
                article = self._parse_single_article(article_elem)
                if article:
                    articles.append(article)

        except ET.ParseError as e:
            logger.error(f"PubMed XML parse error: {e}")

        return articles

    def _parse_single_article(self, elem: ET.Element) -> Optional[PubMedArticle]:
        """Parse a single PubmedArticle element."""
        try:
            medline = elem.find('.//MedlineCitation')
            if medline is None:
                return None

            # PMID
            pmid_elem = medline.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ""

            article_data = medline.find('.//Article')
            if article_data is None:
                return None

            # Title
            title_elem = article_data.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""

            # Abstract
            abstract_parts = []
            abstract_elem = article_data.find('.//Abstract')
            if abstract_elem is not None:
                for text_elem in abstract_elem.findall('.//AbstractText'):
                    label = text_elem.get('Label', '')
                    text = text_elem.text or ''
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = ' '.join(abstract_parts)

            # Year
            year = 0
            pub_date = article_data.find('.//PubDate')
            if pub_date is not None:
                year_elem = pub_date.find('Year')
                if year_elem is not None and year_elem.text:
                    try:
                        year = int(year_elem.text)
                    except ValueError:
                        pass

            # Authors
            authors = []
            author_list = article_data.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')
                    if last_name is not None and last_name.text:
                        name = last_name.text
                        if fore_name is not None and fore_name.text:
                            name = f"{fore_name.text} {name}"
                        authors.append(name)

            # Journal
            journal = ""
            journal_elem = article_data.find('.//Journal/Title')
            if journal_elem is not None:
                journal = journal_elem.text or ""

            # Volume, Issue, Pages
            volume = ""
            issue = ""
            pages = ""

            journal_issue = article_data.find('.//JournalIssue')
            if journal_issue is not None:
                vol_elem = journal_issue.find('Volume')
                volume = vol_elem.text if vol_elem is not None else ""
                iss_elem = journal_issue.find('Issue')
                issue = iss_elem.text if iss_elem is not None else ""

            pagination = article_data.find('.//Pagination/MedlinePgn')
            if pagination is not None:
                pages = pagination.text or ""

            # DOI and PMC ID
            doi = None
            pmc_id = None
            article_ids = elem.find('.//PubmedData/ArticleIdList')
            if article_ids is not None:
                for id_elem in article_ids.findall('ArticleId'):
                    id_type = id_elem.get('IdType', '')
                    if id_type == 'doi' and id_elem.text:
                        doi = id_elem.text
                    elif id_type == 'pmc' and id_elem.text:
                        pmc_id = id_elem.text

            # MeSH terms
            mesh_terms = []
            mesh_list = medline.find('.//MeshHeadingList')
            if mesh_list is not None:
                for mesh in mesh_list.findall('.//DescriptorName'):
                    if mesh.text:
                        mesh_terms.append(mesh.text)

            # Keywords
            keywords = []
            keyword_list = medline.find('.//KeywordList')
            if keyword_list is not None:
                for kw in keyword_list.findall('Keyword'):
                    if kw.text:
                        keywords.append(kw.text)

            # Publication types
            pub_types = []
            pub_type_list = article_data.find('.//PublicationTypeList')
            if pub_type_list is not None:
                for pt in pub_type_list.findall('PublicationType'):
                    if pt.text:
                        pub_types.append(pt.text)

            # PMC PDF URL
            pmc_pdf_url = self.get_pmc_fulltext_url(pmc_id) if pmc_id else None

            return PubMedArticle(
                pmid=pmid,
                doi=doi,
                pmc_id=pmc_id,
                title=title,
                abstract=abstract,
                year=year,
                authors=authors,
                journal=journal,
                volume=volume,
                issue=issue,
                pages=pages,
                mesh_terms=mesh_terms,
                keywords=keywords,
                publication_types=pub_types,
                pmc_pdf_url=pmc_pdf_url
            )

        except Exception as e:
            logger.error(f"Error parsing PubMed article: {e}")
            return None

    def get_stats(self) -> Dict[str, int]:
        """Get client statistics."""
        return {
            'total_requests': self.request_count
        }


# Convenience functions
def search_pubmed(
    query: str,
    limit: int = 25,
    api_key: str = None
) -> List[Dict]:
    """
    Quick search function for PubMed.

    Args:
        query: Search query
        limit: Maximum results
        api_key: Optional NCBI API key

    Returns:
        List of article dictionaries
    """
    client = PubMedClient(api_key=api_key)
    articles = client.search_and_fetch(query, limit=limit)
    return [a.to_dict() for a in articles]


def get_pubmed_article(
    identifier: str,
    api_key: str = None
) -> Optional[Dict]:
    """
    Quick function to get article by PMID or DOI.

    Args:
        identifier: PMID or DOI
        api_key: Optional NCBI API key

    Returns:
        Article dictionary or None
    """
    client = PubMedClient(api_key=api_key)

    # Check if identifier looks like a DOI
    if identifier.startswith('10.') or 'doi' in identifier.lower():
        result = client.get_article_by_doi(identifier)
    else:
        result = client.get_article_by_pmid(identifier)

    return result.to_dict() if result else None


if __name__ == "__main__":
    # Test the client
    client = PubMedClient()

    # Test search
    print("Testing PubMed search...")
    pmids = client.search("machine learning diagnosis", limit=5)
    print(f"Found PMIDs: {pmids}")

    # Fetch articles
    if pmids:
        print("\nFetching articles...")
        articles = client.fetch_articles(pmids)
        for article in articles:
            print(f"- {article.title[:50]}...")
            print(f"  Year: {article.year}, Journal: {article.journal[:30]}")
            print(f"  DOI: {article.doi}")
            print(f"  PMC: {article.pmc_id}")
            if article.mesh_terms:
                print(f"  MeSH: {', '.join(article.mesh_terms[:3])}...")

    # Test DOI lookup
    print("\nTesting DOI lookup...")
    article = client.get_article_by_doi("10.1001/jama.2020.3227")
    if article:
        print(f"Found: {article.title[:60]}...")

    print(f"\nStats: {client.get_stats()}")
