"""
Forensic Audit Agent
====================
Verifies citations in narrative text against source database.
Ensures every claim is backed by actual evidence from papers.

Features:
- Citation detection (DOI, Author-Year, numbered references)
- Source verification from ChromaDB/vector store
- Claim-to-evidence matching with LLM
- Audit trail generation
- Plagiarism-style similarity checking
"""

import re
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Status of citation verification."""
    VERIFIED = "verified"              # Claim matches source
    PARTIALLY_VERIFIED = "partial"     # Some support found
    UNVERIFIED = "unverified"          # No support in source
    SOURCE_NOT_FOUND = "not_found"     # DOI/reference not in database
    NEEDS_REVIEW = "needs_review"      # Requires manual check


@dataclass
class CitationEvidence:
    """Evidence found for a citation."""
    citation_id: str
    citation_type: str  # doi, author_year, numbered
    original_claim: str
    source_snippet: str
    source_title: str
    source_authors: List[str]
    source_year: str
    similarity_score: float
    status: VerificationStatus
    notes: str = ""


@dataclass
class AuditResult:
    """Complete audit result for a document."""
    document_id: str
    total_citations: int
    verified_count: int
    partial_count: int
    unverified_count: int
    not_found_count: int
    verification_rate: float
    evidences: List[CitationEvidence]
    summary: str
    audited_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ForensicAuditAgent:
    """
    Agent that audits narrative text by verifying citations
    against source documents in a vector database.
    """

    def __init__(
        self,
        vector_db=None,
        papers_data: List[Dict] = None,
        anthropic_api_key: str = None,
        use_llm: bool = True
    ):
        """
        Initialize the audit agent.

        Args:
            vector_db: ChromaDB collection or similar vector store
            papers_data: Fallback list of paper dictionaries
            anthropic_api_key: API key for LLM verification
            use_llm: Whether to use LLM for claim verification
        """
        self.vector_db = vector_db
        self.papers_data = papers_data or []
        self.papers_index: Dict[str, Dict] = {}
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_llm = use_llm and bool(self.api_key)
        self.llm_client = None

        # Build papers index
        self._build_papers_index()

        if self.use_llm:
            self._initialize_llm()

    def _build_papers_index(self):
        """Build index of papers by DOI and other identifiers."""
        for paper in self.papers_data:
            # Index by DOI
            if paper.get('doi'):
                doi = paper['doi'].lower().strip()
                self.papers_index[doi] = paper
                # Also index without prefix
                if doi.startswith('10.'):
                    self.papers_index[doi] = paper

            # Index by title (normalized)
            if paper.get('title'):
                title_key = self._normalize_title(paper['title'])
                self.papers_index[title_key] = paper

            # Index by first author + year
            authors = paper.get('authors', [])
            year = paper.get('year', '')
            if authors and year:
                first_author = authors[0] if isinstance(authors, list) else authors.split(',')[0]
                surname = self._extract_surname(first_author)
                key = f"{surname.lower()}_{year}"
                self.papers_index[key] = paper

        logger.info(f"Built papers index with {len(self.papers_index)} entries")

    def _normalize_title(self, title: str) -> str:
        """Normalize title for matching."""
        return re.sub(r'[^\w\s]', '', title.lower())[:50]

    def _extract_surname(self, author: str) -> str:
        """Extract surname from author name."""
        author = author.strip()
        if ',' in author:
            return author.split(',')[0].strip()
        parts = author.split()
        return parts[-1] if parts else author

    def _initialize_llm(self):
        """Initialize LLM client for verification."""
        try:
            from anthropic import Anthropic
            self.llm_client = Anthropic(api_key=self.api_key)
            logger.info("LLM client initialized for forensic audit")
        except ImportError:
            logger.warning("Anthropic package not available")
            self.use_llm = False

    def load_papers(self, papers: List[Dict]) -> int:
        """
        Load papers data for verification.

        Args:
            papers: List of paper dictionaries

        Returns:
            Number of papers loaded
        """
        self.papers_data.extend(papers)
        self._build_papers_index()
        return len(papers)

    def detect_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect all citations in text.

        Supports:
        - DOI format: [DOI: 10.xxx/xxx] or (DOI: 10.xxx)
        - Author-Year: (Smith, 2023) or Smith (2023) or Smith et al. (2023)
        - Numbered: [1], [2,3], [1-5]

        Returns:
            List of detected citations with metadata
        """
        citations = []

        # DOI citations
        doi_patterns = [
            (r'\[DOI:\s*(10\.\d+/[^\]]+)\]', 'doi_bracket'),
            (r'\(DOI:\s*(10\.\d+/[^)]+)\)', 'doi_paren'),
            (r'https?://doi\.org/(10\.\d+/\S+)', 'doi_url'),
            (r'\b(10\.\d{4,}/\S+)\b', 'doi_plain'),
        ]

        for pattern, citation_type in doi_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                doi = match.group(1).strip().rstrip('.,;')
                # Get surrounding context
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                citations.append({
                    'id': doi,
                    'type': 'doi',
                    'match': match.group(0),
                    'position': match.start(),
                    'context': context,
                    'claim': self._extract_claim(text, match.start())
                })

        # Author-Year citations
        author_year_patterns = [
            # (Author, Year) or (Author & Author, Year)
            (r'\(([A-Z][a-z]+(?:\s*(?:&|dan|and|et\s+al\.?)\s*[A-Z][a-z]+)?),?\s*(\d{4})\)', 'paren'),
            # Author (Year)
            (r'\b([A-Z][a-z]+(?:\s+et\s+al\.?)?)\s*\((\d{4})\)', 'inline'),
            # Author and Author (Year)
            (r'\b([A-Z][a-z]+)\s+(?:dan|and|&)\s+([A-Z][a-z]+)\s*\((\d{4})\)', 'dual'),
        ]

        for pattern, citation_type in author_year_patterns:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                if citation_type == 'dual':
                    author = f"{groups[0]}_{groups[1]}"
                    year = groups[2]
                else:
                    author = groups[0]
                    year = groups[1]

                # Clean author name
                author = re.sub(r'\s+et\s+al\.?', '', author).strip()

                key = f"{author.lower()}_{year}"

                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                citations.append({
                    'id': key,
                    'type': 'author_year',
                    'author': author,
                    'year': year,
                    'match': match.group(0),
                    'position': match.start(),
                    'context': context,
                    'claim': self._extract_claim(text, match.start())
                })

        # Numbered citations [1], [2,3,4], [1-5]
        numbered_patterns = [
            (r'\[(\d+(?:\s*[-,]\s*\d+)*)\]', 'numbered'),
        ]

        for pattern, citation_type in numbered_patterns:
            for match in re.finditer(pattern, text):
                numbers = match.group(1)

                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                citations.append({
                    'id': numbers,
                    'type': 'numbered',
                    'match': match.group(0),
                    'position': match.start(),
                    'context': context,
                    'claim': self._extract_claim(text, match.start())
                })

        # Remove duplicates based on position
        seen_positions = set()
        unique_citations = []
        for cit in sorted(citations, key=lambda x: x['position']):
            if cit['position'] not in seen_positions:
                unique_citations.append(cit)
                seen_positions.add(cit['position'])

        return unique_citations

    def _extract_claim(self, text: str, citation_pos: int) -> str:
        """Extract the claim/sentence containing the citation."""
        # Find sentence boundaries
        before = text[:citation_pos]
        after = text[citation_pos:]

        # Find start of sentence
        sentence_start = max(
            before.rfind('. ') + 2,
            before.rfind('.\n') + 2,
            0
        )

        # Find end of sentence
        end_match = re.search(r'[.!?]\s', after[50:] if len(after) > 50 else after)
        if end_match:
            sentence_end = citation_pos + 50 + end_match.end()
        else:
            sentence_end = min(citation_pos + 200, len(text))

        return text[sentence_start:sentence_end].strip()

    def get_source_data(self, citation: Dict) -> Optional[Dict]:
        """
        Retrieve source data for a citation.

        Args:
            citation: Citation dictionary from detect_citations

        Returns:
            Source paper data or None
        """
        citation_id = citation['id']
        citation_type = citation['type']

        # Try vector database first
        if self.vector_db:
            try:
                if citation_type == 'doi':
                    results = self.vector_db.get(where={"doi": citation_id})
                elif citation_type == 'author_year':
                    # Query by metadata
                    results = self.vector_db.get(
                        where={
                            "$and": [
                                {"year": citation.get('year', '')},
                            ]
                        }
                    )
                else:
                    results = None

                if results and results.get('documents'):
                    return {
                        'content': results['documents'][0],
                        'metadata': results.get('metadatas', [{}])[0]
                    }
            except Exception as e:
                logger.warning(f"Vector DB query failed: {e}")

        # Fallback to papers index
        if citation_type == 'doi':
            doi_lower = citation_id.lower()
            if doi_lower in self.papers_index:
                return self.papers_index[doi_lower]

        elif citation_type == 'author_year':
            key = citation_id.lower()
            if key in self.papers_index:
                return self.papers_index[key]

            # Try partial match on author
            author = citation.get('author', '').lower()
            year = citation.get('year', '')

            for idx_key, paper in self.papers_index.items():
                if year and str(paper.get('year', '')) == year:
                    paper_authors = paper.get('authors', [])
                    if isinstance(paper_authors, str):
                        paper_authors = [paper_authors]

                    for pa in paper_authors:
                        if author in pa.lower() or pa.lower().startswith(author):
                            return paper

        return None

    def verify_claim(
        self,
        claim: str,
        source_data: Dict
    ) -> Tuple[VerificationStatus, float, str]:
        """
        Verify if claim is supported by source data.

        Args:
            claim: The claim text from narrative
            source_data: Source paper data

        Returns:
            Tuple of (status, similarity_score, notes)
        """
        if not source_data:
            return VerificationStatus.SOURCE_NOT_FOUND, 0.0, "Source not found in database"

        # Get source content
        source_content = ""
        if isinstance(source_data, dict):
            source_content = (
                source_data.get('abstract', '') + " " +
                source_data.get('content', '') + " " +
                source_data.get('findings', '') + " " +
                source_data.get('tldr', '')
            )

        if not source_content.strip():
            return VerificationStatus.NEEDS_REVIEW, 0.5, "Source content is empty"

        # Simple keyword overlap check
        claim_words = set(re.findall(r'\b\w{4,}\b', claim.lower()))
        claim_words -= {'yang', 'dalam', 'untuk', 'dengan', 'dari', 'pada', 'adalah', 'atau', 'this', 'that', 'with', 'from'}

        source_words = set(re.findall(r'\b\w{4,}\b', source_content.lower()))

        if not claim_words:
            return VerificationStatus.NEEDS_REVIEW, 0.5, "Claim too short to verify"

        overlap = len(claim_words & source_words) / len(claim_words)

        # LLM verification for deeper analysis
        if self.use_llm and self.llm_client and overlap > 0.2:
            try:
                llm_result = self._llm_verify_claim(claim, source_content[:2000])
                return llm_result
            except Exception as e:
                logger.warning(f"LLM verification failed: {e}")

        # Rule-based classification
        if overlap >= 0.7:
            return VerificationStatus.VERIFIED, overlap, "High keyword overlap with source"
        elif overlap >= 0.4:
            return VerificationStatus.PARTIALLY_VERIFIED, overlap, "Moderate keyword overlap"
        elif overlap >= 0.2:
            return VerificationStatus.NEEDS_REVIEW, overlap, "Low overlap - manual review recommended"
        else:
            return VerificationStatus.UNVERIFIED, overlap, "Claim not supported by source content"

    def _llm_verify_claim(
        self,
        claim: str,
        source_content: str
    ) -> Tuple[VerificationStatus, float, str]:
        """Use LLM to verify claim against source."""
        prompt = f"""Sebagai auditor akademik, verifikasi apakah KLAIM berikut didukung oleh SUMBER.

KLAIM:
"{claim}"

SUMBER:
"{source_content[:1500]}"

Analisis dan berikan:
1. STATUS: VERIFIED (klaim didukung penuh), PARTIAL (sebagian didukung), UNVERIFIED (tidak didukung)
2. CONFIDENCE: 0.0-1.0
3. NOTES: Penjelasan singkat (1 kalimat)

Format output:
STATUS: [status]
CONFIDENCE: [score]
NOTES: [penjelasan]"""

        response = self.llm_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Parse response
        status_match = re.search(r'STATUS:\s*(VERIFIED|PARTIAL|UNVERIFIED)', response_text, re.IGNORECASE)
        conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response_text)
        notes_match = re.search(r'NOTES:\s*(.+?)(?:\n|$)', response_text)

        if status_match:
            status_str = status_match.group(1).upper()
            status_map = {
                'VERIFIED': VerificationStatus.VERIFIED,
                'PARTIAL': VerificationStatus.PARTIALLY_VERIFIED,
                'UNVERIFIED': VerificationStatus.UNVERIFIED
            }
            status = status_map.get(status_str, VerificationStatus.NEEDS_REVIEW)
        else:
            status = VerificationStatus.NEEDS_REVIEW

        confidence = float(conf_match.group(1)) if conf_match else 0.5
        notes = notes_match.group(1).strip() if notes_match else "LLM verification complete"

        return status, confidence, f"[LLM] {notes}"

    def verify_narrative(
        self,
        chapter_text: str,
        chapter_id: str = "chapter"
    ) -> AuditResult:
        """
        Verify all citations in a chapter/narrative text.

        Args:
            chapter_text: The narrative text to audit
            chapter_id: Identifier for the chapter

        Returns:
            AuditResult with all verification details
        """
        # Detect all citations
        citations = self.detect_citations(chapter_text)

        evidences: List[CitationEvidence] = []

        for citation in citations:
            # Get source data
            source_data = self.get_source_data(citation)

            # Verify claim
            claim = citation.get('claim', '')
            status, similarity, notes = self.verify_claim(claim, source_data)

            # Build evidence record
            source_title = ""
            source_authors = []
            source_year = ""
            source_snippet = ""

            if source_data:
                source_title = source_data.get('title', '')
                source_authors = source_data.get('authors', [])
                if isinstance(source_authors, str):
                    source_authors = [source_authors]
                source_year = str(source_data.get('year', ''))

                # Get snippet
                content = source_data.get('abstract', source_data.get('content', ''))
                source_snippet = content[:300] + "..." if len(content) > 300 else content

            evidence = CitationEvidence(
                citation_id=citation['id'],
                citation_type=citation['type'],
                original_claim=claim[:200],
                source_snippet=source_snippet,
                source_title=source_title,
                source_authors=source_authors,
                source_year=source_year,
                similarity_score=similarity,
                status=status,
                notes=notes
            )
            evidences.append(evidence)

        # Calculate statistics
        total = len(evidences)
        verified = sum(1 for e in evidences if e.status == VerificationStatus.VERIFIED)
        partial = sum(1 for e in evidences if e.status == VerificationStatus.PARTIALLY_VERIFIED)
        unverified = sum(1 for e in evidences if e.status == VerificationStatus.UNVERIFIED)
        not_found = sum(1 for e in evidences if e.status == VerificationStatus.SOURCE_NOT_FOUND)

        verification_rate = (verified + partial * 0.5) / total * 100 if total > 0 else 0

        # Generate summary
        summary = self._generate_summary(total, verified, partial, unverified, not_found, verification_rate)

        return AuditResult(
            document_id=chapter_id,
            total_citations=total,
            verified_count=verified,
            partial_count=partial,
            unverified_count=unverified,
            not_found_count=not_found,
            verification_rate=verification_rate,
            evidences=evidences,
            summary=summary
        )

    def _generate_summary(
        self,
        total: int,
        verified: int,
        partial: int,
        unverified: int,
        not_found: int,
        rate: float
    ) -> str:
        """Generate audit summary."""
        if total == 0:
            return "Tidak ada sitasi yang terdeteksi dalam dokumen."

        lines = [
            f"Audit Forensik Sitasi - Ringkasan",
            f"=" * 40,
            f"Total sitasi terdeteksi: {total}",
            f"",
            f"Status Verifikasi:",
            f"  ✅ Terverifikasi penuh: {verified} ({verified/total*100:.0f}%)",
            f"  🔶 Sebagian terverifikasi: {partial} ({partial/total*100:.0f}%)",
            f"  ❌ Tidak terverifikasi: {unverified} ({unverified/total*100:.0f}%)",
            f"  ❓ Sumber tidak ditemukan: {not_found} ({not_found/total*100:.0f}%)",
            f"",
            f"Tingkat Verifikasi: {rate:.1f}%",
            f"",
        ]

        if rate >= 80:
            lines.append("📊 Status: EXCELLENT - Sitasi sangat well-documented")
        elif rate >= 60:
            lines.append("📊 Status: GOOD - Sebagian besar sitasi terverifikasi")
        elif rate >= 40:
            lines.append("📊 Status: FAIR - Perlu review beberapa sitasi")
        else:
            lines.append("📊 Status: NEEDS ATTENTION - Banyak sitasi perlu verifikasi")

        return "\n".join(lines)

    def format_audit_report(self, result: AuditResult) -> str:
        """Format audit result as detailed report."""
        lines = [
            "=" * 70,
            "LAPORAN AUDIT FORENSIK SITASI",
            "=" * 70,
            "",
            result.summary,
            "",
            "-" * 70,
            "DETAIL VERIFIKASI:",
            "-" * 70,
        ]

        for i, evidence in enumerate(result.evidences, 1):
            status_icon = {
                VerificationStatus.VERIFIED: "✅",
                VerificationStatus.PARTIALLY_VERIFIED: "🔶",
                VerificationStatus.UNVERIFIED: "❌",
                VerificationStatus.SOURCE_NOT_FOUND: "❓",
                VerificationStatus.NEEDS_REVIEW: "🔍"
            }

            lines.extend([
                f"",
                f"[{i}] {status_icon[evidence.status]} {evidence.status.value.upper()}",
                f"    Sitasi: {evidence.citation_id}",
                f"    Tipe: {evidence.citation_type}",
                f"    Similarity: {evidence.similarity_score:.0%}",
                f"    ",
                f"    Klaim: \"{evidence.original_claim[:100]}...\"",
            ])

            if evidence.source_title:
                lines.append(f"    Sumber: {evidence.source_title[:60]}...")

            if evidence.notes:
                lines.append(f"    Notes: {evidence.notes}")

        lines.extend([
            "",
            "=" * 70,
            f"Diaudit pada: {result.audited_at}",
            "=" * 70
        ])

        return "\n".join(lines)

    def audit_full_report(
        self,
        chapters: Dict[str, str]
    ) -> Dict[str, AuditResult]:
        """
        Audit all chapters in a report.

        Args:
            chapters: Dictionary of chapter_id -> chapter_content

        Returns:
            Dictionary of chapter_id -> AuditResult
        """
        results = {}

        for chapter_id, content in chapters.items():
            logger.info(f"Auditing chapter: {chapter_id}")
            result = self.verify_narrative(content, chapter_id)
            results[chapter_id] = result

        return results


def audit_narrative(
    text: str,
    papers: List[Dict] = None,
    api_key: str = None
) -> AuditResult:
    """
    Convenience function to audit narrative text.

    Args:
        text: Narrative text to audit
        papers: List of source papers
        api_key: Anthropic API key for LLM verification

    Returns:
        AuditResult
    """
    agent = ForensicAuditAgent(
        papers_data=papers or [],
        anthropic_api_key=api_key
    )
    return agent.verify_narrative(text)
