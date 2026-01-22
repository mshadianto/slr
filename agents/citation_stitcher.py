"""
Citation Auto-Stitcher
======================
Automatically matches author names in narrative text with bibliography
entries from Scopus export files. Eliminates manual citation matching.

Supports:
- BibTeX (.bib)
- RIS (.ris)
- CSV from Scopus
- JSON bibliography

Citation Styles:
- APA 7th Edition
- Vancouver (Numbered)
- Harvard
- IEEE
"""

import re
import csv
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class CitationStyle(str, Enum):
    """Supported citation styles."""
    APA7 = "apa7"
    VANCOUVER = "vancouver"
    HARVARD = "harvard"
    IEEE = "ieee"


@dataclass
class BibEntry:
    """Bibliography entry."""
    key: str
    authors: List[str]
    year: str
    title: str
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    entry_type: str = "article"
    raw_data: Dict = field(default_factory=dict)

    @property
    def first_author_surname(self) -> str:
        """Get first author's surname."""
        if self.authors:
            author = self.authors[0]
            # Handle "Surname, FirstName" format
            if "," in author:
                return author.split(",")[0].strip()
            # Handle "FirstName Surname" format
            parts = author.split()
            return parts[-1] if parts else ""
        return ""

    @property
    def author_surnames(self) -> List[str]:
        """Get all author surnames."""
        surnames = []
        for author in self.authors:
            if "," in author:
                surnames.append(author.split(",")[0].strip())
            else:
                parts = author.split()
                if parts:
                    surnames.append(parts[-1])
        return surnames


@dataclass
class CitationMatch:
    """A matched citation in text."""
    original_text: str
    start_pos: int
    end_pos: int
    matched_entry: BibEntry
    confidence: float
    suggested_citation: str


@dataclass
class StitchedResult:
    """Result of citation stitching."""
    original_text: str
    stitched_text: str
    citations_added: int
    matches: List[CitationMatch]
    bibliography: str
    warnings: List[str]


class CitationAutoStitcher:
    """
    Automatically stitches citations into narrative text.

    Matches author mentions with bibliography entries and inserts
    properly formatted in-text citations.
    """

    def __init__(
        self,
        citation_style: CitationStyle = CitationStyle.APA7,
        bibliography: List[BibEntry] = None
    ):
        """
        Initialize the stitcher.

        Args:
            citation_style: Citation format style
            bibliography: Pre-loaded bibliography entries
        """
        self.citation_style = citation_style
        self.bibliography: List[BibEntry] = bibliography or []
        self.author_index: Dict[str, List[BibEntry]] = {}
        self.citation_counter = 0  # For Vancouver style

        if self.bibliography:
            self._build_author_index()

    def _build_author_index(self):
        """Build index of author surnames to entries."""
        self.author_index = {}
        for entry in self.bibliography:
            for surname in entry.author_surnames:
                surname_lower = surname.lower()
                if surname_lower not in self.author_index:
                    self.author_index[surname_lower] = []
                self.author_index[surname_lower].append(entry)

        logger.info(f"Built author index with {len(self.author_index)} unique surnames")

    def load_bibtex(self, filepath: str) -> int:
        """
        Load bibliography from BibTeX file.

        Args:
            filepath: Path to .bib file

        Returns:
            Number of entries loaded
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple BibTeX parser
            entries = self._parse_bibtex(content)
            self.bibliography.extend(entries)
            self._build_author_index()

            logger.info(f"Loaded {len(entries)} entries from BibTeX")
            return len(entries)

        except Exception as e:
            logger.error(f"Error loading BibTeX: {e}")
            return 0

    def _parse_bibtex(self, content: str) -> List[BibEntry]:
        """Parse BibTeX content."""
        entries = []

        # Match @type{key, ... }
        pattern = r'@(\w+)\s*\{\s*([^,]+)\s*,([^@]+)\}'
        matches = re.findall(pattern, content, re.DOTALL)

        for entry_type, key, fields_str in matches:
            fields = {}

            # Parse fields
            field_pattern = r'(\w+)\s*=\s*[{"]([^}"]+)[}"]'
            for field_name, field_value in re.findall(field_pattern, fields_str):
                fields[field_name.lower()] = field_value.strip()

            # Parse authors
            authors = []
            if 'author' in fields:
                author_str = fields['author']
                # Split by " and "
                authors = [a.strip() for a in re.split(r'\s+and\s+', author_str)]

            entry = BibEntry(
                key=key.strip(),
                authors=authors,
                year=fields.get('year', ''),
                title=fields.get('title', ''),
                journal=fields.get('journal', fields.get('booktitle', '')),
                volume=fields.get('volume', ''),
                issue=fields.get('number', ''),
                pages=fields.get('pages', ''),
                doi=fields.get('doi', ''),
                url=fields.get('url', ''),
                entry_type=entry_type.lower(),
                raw_data=fields
            )
            entries.append(entry)

        return entries

    def load_ris(self, filepath: str) -> int:
        """
        Load bibliography from RIS file.

        Args:
            filepath: Path to .ris file

        Returns:
            Number of entries loaded
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            entries = self._parse_ris(content)
            self.bibliography.extend(entries)
            self._build_author_index()

            logger.info(f"Loaded {len(entries)} entries from RIS")
            return len(entries)

        except Exception as e:
            logger.error(f"Error loading RIS: {e}")
            return 0

    def _parse_ris(self, content: str) -> List[BibEntry]:
        """Parse RIS content."""
        entries = []
        current_entry = {}
        current_authors = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('ER  -'):
                # End of record
                if current_entry:
                    entry = BibEntry(
                        key=current_entry.get('id', f"entry_{len(entries)}"),
                        authors=current_authors,
                        year=current_entry.get('py', current_entry.get('y1', ''))[:4],
                        title=current_entry.get('ti', current_entry.get('t1', '')),
                        journal=current_entry.get('jf', current_entry.get('jo', '')),
                        volume=current_entry.get('vl', ''),
                        issue=current_entry.get('is', ''),
                        pages=current_entry.get('sp', ''),
                        doi=current_entry.get('do', ''),
                        url=current_entry.get('ur', ''),
                        entry_type=current_entry.get('ty', 'article').lower(),
                        raw_data=current_entry.copy()
                    )
                    entries.append(entry)

                current_entry = {}
                current_authors = []
                continue

            # Parse tag-value
            if '  - ' in line:
                tag, value = line.split('  - ', 1)
                tag = tag.strip().lower()
                value = value.strip()

                if tag in ('au', 'a1', 'a2'):
                    current_authors.append(value)
                else:
                    current_entry[tag] = value

        return entries

    def load_scopus_csv(self, filepath: str) -> int:
        """
        Load bibliography from Scopus CSV export.

        Args:
            filepath: Path to CSV file

        Returns:
            Number of entries loaded
        """
        try:
            entries = []

            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Scopus CSV column names
                    authors_str = row.get('Authors', row.get('Author full names', ''))
                    authors = [a.strip() for a in authors_str.split(';') if a.strip()]

                    entry = BibEntry(
                        key=row.get('EID', row.get('DOI', f"scopus_{len(entries)}")),
                        authors=authors,
                        year=row.get('Year', '')[:4] if row.get('Year') else '',
                        title=row.get('Title', ''),
                        journal=row.get('Source title', ''),
                        volume=row.get('Volume', ''),
                        issue=row.get('Issue', ''),
                        pages=row.get('Page start', ''),
                        doi=row.get('DOI', ''),
                        url=row.get('Link', ''),
                        entry_type='article',
                        raw_data=dict(row)
                    )
                    entries.append(entry)

            self.bibliography.extend(entries)
            self._build_author_index()

            logger.info(f"Loaded {len(entries)} entries from Scopus CSV")
            return len(entries)

        except Exception as e:
            logger.error(f"Error loading Scopus CSV: {e}")
            return 0

    def load_json(self, filepath: str) -> int:
        """Load bibliography from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            entries = []
            items = data if isinstance(data, list) else data.get('entries', [])

            for item in items:
                authors = item.get('authors', [])
                if isinstance(authors, str):
                    authors = [a.strip() for a in authors.split(';')]

                entry = BibEntry(
                    key=item.get('key', item.get('doi', f"json_{len(entries)}")),
                    authors=authors,
                    year=str(item.get('year', ''))[:4],
                    title=item.get('title', ''),
                    journal=item.get('journal', item.get('source', '')),
                    volume=str(item.get('volume', '')),
                    issue=str(item.get('issue', '')),
                    pages=str(item.get('pages', '')),
                    doi=item.get('doi', ''),
                    url=item.get('url', ''),
                    entry_type=item.get('type', 'article'),
                    raw_data=item
                )
                entries.append(entry)

            self.bibliography.extend(entries)
            self._build_author_index()

            logger.info(f"Loaded {len(entries)} entries from JSON")
            return len(entries)

        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            return 0

    def load_from_papers(self, papers: List[Dict]) -> int:
        """
        Load bibliography from paper list (from SLR results).

        Args:
            papers: List of paper dictionaries from SLR

        Returns:
            Number of entries loaded
        """
        entries = []

        for paper in papers:
            authors = paper.get('authors', [])
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(';')]

            entry = BibEntry(
                key=paper.get('doi', paper.get('id', f"paper_{len(entries)}")),
                authors=authors,
                year=str(paper.get('year', ''))[:4],
                title=paper.get('title', ''),
                journal=paper.get('journal', paper.get('source', '')),
                volume=str(paper.get('volume', '')),
                issue=str(paper.get('issue', '')),
                pages=str(paper.get('pages', '')),
                doi=paper.get('doi', ''),
                url=paper.get('url', ''),
                entry_type='article',
                raw_data=paper
            )
            entries.append(entry)

        self.bibliography.extend(entries)
        self._build_author_index()

        logger.info(f"Loaded {len(entries)} entries from paper list")
        return len(entries)

    def find_author_mentions(self, text: str) -> List[Tuple[str, int, int, float]]:
        """
        Find potential author mentions in text.

        Returns list of (surname, start_pos, end_pos, confidence)
        """
        mentions = []

        # Pattern for author mentions: "Smith (2020)", "Smith et al.", "Smith and Jones"
        patterns = [
            # "Author (Year)" - highest confidence
            (r'\b([A-Z][a-z]+(?:\s+(?:et\s+al\.?|dan|and|&)\s*(?:[A-Z][a-z]+)?)?)\s*\((\d{4})\)', 0.95),
            # "Author et al. (Year)"
            (r'\b([A-Z][a-z]+)\s+et\s+al\.?\s*\((\d{4})\)', 0.9),
            # "Author and Author (Year)"
            (r'\b([A-Z][a-z]+)\s+(?:dan|and|&)\s+([A-Z][a-z]+)\s*\((\d{4})\)', 0.9),
            # Standalone surname with context clues
            (r'(?:menurut|according to|berdasarkan|dalam studi)\s+([A-Z][a-z]+)', 0.7),
            # "Studi oleh Author"
            (r'(?:studi|penelitian|riset)\s+(?:oleh|by)\s+([A-Z][a-z]+)', 0.75),
        ]

        for pattern, confidence in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract surname from match
                groups = match.groups()
                surname = groups[0]

                # Clean up surname
                surname = re.sub(r'\s+et\s+al\.?', '', surname).strip()
                surname = re.sub(r'\s+(?:dan|and|&).*', '', surname).strip()

                mentions.append((
                    surname,
                    match.start(),
                    match.end(),
                    confidence
                ))

        return mentions

    def match_citation(
        self,
        surname: str,
        year: str = None,
        context: str = ""
    ) -> Optional[Tuple[BibEntry, float]]:
        """
        Match a surname (and optional year) to a bibliography entry.

        Returns (entry, confidence) or None if no match.
        """
        surname_lower = surname.lower()

        if surname_lower not in self.author_index:
            # Try fuzzy matching
            for idx_surname in self.author_index:
                if self._fuzzy_match(surname_lower, idx_surname):
                    surname_lower = idx_surname
                    break
            else:
                return None

        candidates = self.author_index[surname_lower]

        if not candidates:
            return None

        # If year provided, filter by year
        if year:
            year_matches = [e for e in candidates if e.year == year]
            if year_matches:
                return (year_matches[0], 0.95)

        # If only one candidate, return it
        if len(candidates) == 1:
            return (candidates[0], 0.8)

        # Multiple candidates - try to disambiguate using context
        if context:
            for entry in candidates:
                # Check if title words appear in context
                title_words = set(entry.title.lower().split())
                context_words = set(context.lower().split())
                overlap = len(title_words & context_words)
                if overlap > 3:
                    return (entry, 0.7)

        # Return first candidate with lower confidence
        return (candidates[0], 0.5)

    def _fuzzy_match(self, s1: str, s2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy string matching."""
        if s1 == s2:
            return True

        # Check if one is prefix of other
        if s1.startswith(s2) or s2.startswith(s1):
            return True

        # Simple Levenshtein-like ratio
        longer = max(len(s1), len(s2))
        if longer == 0:
            return True

        # Count matching characters
        matches = sum(1 for a, b in zip(s1, s2) if a == b)
        ratio = matches / longer

        return ratio >= threshold

    def format_citation(self, entry: BibEntry, position: int = None) -> str:
        """
        Format citation according to selected style.

        Args:
            entry: Bibliography entry
            position: Position number (for Vancouver style)

        Returns:
            Formatted in-text citation
        """
        if self.citation_style == CitationStyle.APA7:
            return self._format_apa7(entry)
        elif self.citation_style == CitationStyle.VANCOUVER:
            return self._format_vancouver(entry, position)
        elif self.citation_style == CitationStyle.HARVARD:
            return self._format_harvard(entry)
        elif self.citation_style == CitationStyle.IEEE:
            return self._format_ieee(entry, position)
        else:
            return self._format_apa7(entry)

    def _format_apa7(self, entry: BibEntry) -> str:
        """Format APA 7th edition citation."""
        num_authors = len(entry.authors)

        if num_authors == 0:
            author_str = "Unknown"
        elif num_authors == 1:
            author_str = entry.first_author_surname
        elif num_authors == 2:
            surnames = entry.author_surnames[:2]
            author_str = f"{surnames[0]} & {surnames[1]}"
        else:
            author_str = f"{entry.first_author_surname} et al."

        return f"({author_str}, {entry.year})"

    def _format_vancouver(self, entry: BibEntry, position: int = None) -> str:
        """Format Vancouver (numbered) citation."""
        if position is None:
            self.citation_counter += 1
            position = self.citation_counter
        return f"[{position}]"

    def _format_harvard(self, entry: BibEntry) -> str:
        """Format Harvard citation."""
        num_authors = len(entry.authors)

        if num_authors == 0:
            author_str = "Unknown"
        elif num_authors == 1:
            author_str = entry.first_author_surname
        elif num_authors == 2:
            surnames = entry.author_surnames[:2]
            author_str = f"{surnames[0]} and {surnames[1]}"
        elif num_authors <= 3:
            surnames = entry.author_surnames[:3]
            author_str = ", ".join(surnames[:-1]) + f" and {surnames[-1]}"
        else:
            author_str = f"{entry.first_author_surname} et al."

        return f"({author_str} {entry.year})"

    def _format_ieee(self, entry: BibEntry, position: int = None) -> str:
        """Format IEEE citation."""
        if position is None:
            self.citation_counter += 1
            position = self.citation_counter
        return f"[{position}]"

    def stitch_citations(
        self,
        text: str,
        auto_detect: bool = True
    ) -> StitchedResult:
        """
        Stitch citations into narrative text.

        Args:
            text: Narrative text to process
            auto_detect: Whether to auto-detect author mentions

        Returns:
            StitchedResult with stitched text and metadata
        """
        matches: List[CitationMatch] = []
        warnings: List[str] = []
        self.citation_counter = 0  # Reset for Vancouver style

        if auto_detect:
            mentions = self.find_author_mentions(text)

            for surname, start, end, mention_confidence in mentions:
                # Extract year if present in the mention
                mention_text = text[start:end]
                year_match = re.search(r'\((\d{4})\)', mention_text)
                year = year_match.group(1) if year_match else None

                # Get context around mention
                context_start = max(0, start - 100)
                context_end = min(len(text), end + 100)
                context = text[context_start:context_end]

                # Try to match
                result = self.match_citation(surname, year, context)

                if result:
                    entry, match_confidence = result
                    overall_confidence = mention_confidence * match_confidence

                    # Format citation
                    citation = self.format_citation(entry)

                    matches.append(CitationMatch(
                        original_text=mention_text,
                        start_pos=start,
                        end_pos=end,
                        matched_entry=entry,
                        confidence=overall_confidence,
                        suggested_citation=citation
                    ))
                else:
                    warnings.append(f"No match found for: '{surname}' at position {start}")

        # Apply stitching (high confidence only)
        stitched_text = text
        offset = 0

        # Sort matches by position
        matches.sort(key=lambda m: m.start_pos)

        for match in matches:
            if match.confidence >= 0.7:
                # Check if citation already exists
                orig = match.original_text
                if not re.search(r'\([^)]*\d{4}[^)]*\)$', orig):
                    # Add citation after the author mention
                    insert_pos = match.end_pos + offset

                    # Don't add if citation already follows
                    following_text = stitched_text[insert_pos:insert_pos+20]
                    if not re.match(r'\s*\([^)]+\)', following_text):
                        citation = f" {match.suggested_citation}"
                        stitched_text = (
                            stitched_text[:insert_pos] +
                            citation +
                            stitched_text[insert_pos:]
                        )
                        offset += len(citation)

        # Generate bibliography
        bibliography = self.format_bibliography()

        return StitchedResult(
            original_text=text,
            stitched_text=stitched_text,
            citations_added=len([m for m in matches if m.confidence >= 0.7]),
            matches=matches,
            bibliography=bibliography,
            warnings=warnings
        )

    def format_bibliography(self) -> str:
        """Format complete bibliography."""
        lines = ["## Daftar Pustaka\n"]

        # Sort by first author surname
        sorted_entries = sorted(
            self.bibliography,
            key=lambda e: e.first_author_surname.lower()
        )

        for i, entry in enumerate(sorted_entries, 1):
            if self.citation_style == CitationStyle.APA7:
                ref = self._format_ref_apa7(entry)
            elif self.citation_style == CitationStyle.VANCOUVER:
                ref = f"[{i}] {self._format_ref_vancouver(entry)}"
            elif self.citation_style == CitationStyle.IEEE:
                ref = f"[{i}] {self._format_ref_ieee(entry)}"
            else:
                ref = self._format_ref_apa7(entry)

            lines.append(ref)
            lines.append("")

        return "\n".join(lines)

    def _format_ref_apa7(self, entry: BibEntry) -> str:
        """Format APA 7 reference."""
        # Authors
        if len(entry.authors) == 0:
            authors = "Unknown"
        elif len(entry.authors) == 1:
            authors = entry.authors[0]
        elif len(entry.authors) <= 20:
            authors = ", ".join(entry.authors[:-1]) + f", & {entry.authors[-1]}"
        else:
            authors = ", ".join(entry.authors[:19]) + f", ... {entry.authors[-1]}"

        # Basic format
        ref = f"{authors} ({entry.year}). {entry.title}."

        if entry.journal:
            ref += f" *{entry.journal}*"
            if entry.volume:
                ref += f", *{entry.volume}*"
                if entry.issue:
                    ref += f"({entry.issue})"
            if entry.pages:
                ref += f", {entry.pages}"
            ref += "."

        if entry.doi:
            ref += f" https://doi.org/{entry.doi}"

        return ref

    def _format_ref_vancouver(self, entry: BibEntry) -> str:
        """Format Vancouver reference."""
        # Authors (max 6, then et al.)
        if len(entry.authors) <= 6:
            authors = ", ".join(entry.authors)
        else:
            authors = ", ".join(entry.authors[:6]) + ", et al"

        ref = f"{authors}. {entry.title}. {entry.journal}. {entry.year}"

        if entry.volume:
            ref += f";{entry.volume}"
            if entry.issue:
                ref += f"({entry.issue})"
        if entry.pages:
            ref += f":{entry.pages}"
        ref += "."

        return ref

    def _format_ref_ieee(self, entry: BibEntry) -> str:
        """Format IEEE reference."""
        # Authors with initials first
        authors = " and ".join(entry.authors[:3])
        if len(entry.authors) > 3:
            authors += " et al."

        ref = f'{authors}, "{entry.title}," '

        if entry.journal:
            ref += f"*{entry.journal}*, "

        if entry.volume:
            ref += f"vol. {entry.volume}, "
        if entry.issue:
            ref += f"no. {entry.issue}, "
        if entry.pages:
            ref += f"pp. {entry.pages}, "

        ref += f"{entry.year}."

        return ref

    def get_used_references(self) -> List[str]:
        """
        Get list of formatted references for all loaded bibliography entries.

        Returns:
            List of formatted reference strings
        """
        references = []

        sorted_entries = sorted(
            self.bibliography,
            key=lambda e: e.first_author_surname.lower()
        )

        for entry in sorted_entries:
            if self.citation_style == CitationStyle.APA7:
                ref = self._format_ref_apa7(entry)
            elif self.citation_style == CitationStyle.VANCOUVER:
                ref = self._format_ref_vancouver(entry)
            elif self.citation_style == CitationStyle.IEEE:
                ref = self._format_ref_ieee(entry)
            else:
                ref = self._format_ref_apa7(entry)

            references.append(ref)

        return references

    def get_all_entries(self) -> List[BibEntry]:
        """Get all bibliography entries."""
        return self.bibliography


def auto_stitch_citations(
    text: str,
    bibliography_file: str = None,
    papers: List[Dict] = None,
    style: CitationStyle = CitationStyle.APA7
) -> StitchedResult:
    """
    Convenience function to auto-stitch citations.

    Args:
        text: Narrative text
        bibliography_file: Path to bibliography file
        papers: List of papers from SLR
        style: Citation style

    Returns:
        StitchedResult
    """
    stitcher = CitationAutoStitcher(citation_style=style)

    if bibliography_file:
        path = Path(bibliography_file)
        if path.suffix.lower() == '.bib':
            stitcher.load_bibtex(bibliography_file)
        elif path.suffix.lower() == '.ris':
            stitcher.load_ris(bibliography_file)
        elif path.suffix.lower() == '.csv':
            stitcher.load_scopus_csv(bibliography_file)
        elif path.suffix.lower() == '.json':
            stitcher.load_json(bibliography_file)

    if papers:
        stitcher.load_from_papers(papers)

    return stitcher.stitch_citations(text)
