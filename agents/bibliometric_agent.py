"""
Muezza AI - Bibliometric Analysis Agent
=======================================
Provides bibliometric analysis and visualization for SLR results.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class BibliometricStats:
    """Container for bibliometric statistics."""
    total_papers: int
    total_citations: int
    avg_citations: float
    max_citations: int
    min_citations: int
    h_index: int
    publication_years: Dict[int, int]
    top_authors: List[Tuple[str, int]]
    top_journals: List[Tuple[str, int]]
    top_keywords: List[Tuple[str, int]]
    top_cited_papers: List[Dict]
    author_collaborations: Dict[str, List[str]]
    papers_with_citations: int
    citation_distribution: Dict[str, int]


class BibliometricAgent:
    """
    Bibliometric Analysis Agent

    Provides comprehensive bibliometric analysis including:
    - Publication trends over time
    - Citation analysis and h-index
    - Author productivity and collaboration
    - Journal distribution
    - Keyword frequency analysis
    """

    def __init__(self, papers: List[Dict] = None):
        """
        Initialize with papers data.

        Args:
            papers: List of paper dictionaries with metadata
        """
        self.papers = papers or []
        self._stats = None

    def set_papers(self, papers: List[Dict]):
        """Update papers data."""
        self.papers = papers
        self._stats = None  # Reset cached stats

    def analyze(self) -> BibliometricStats:
        """
        Perform full bibliometric analysis.

        Returns:
            BibliometricStats with all computed metrics
        """
        if not self.papers:
            return self._empty_stats()

        # Citation metrics
        citations = [self._get_citations(p) for p in self.papers]
        total_citations = sum(citations)
        papers_with_citations = sum(1 for c in citations if c > 0)

        # H-index calculation
        h_index = self._calculate_h_index(citations)

        # Publication years
        publication_years = self._analyze_years()

        # Author analysis
        top_authors, collaborations = self._analyze_authors()

        # Journal analysis
        top_journals = self._analyze_journals()

        # Keyword analysis
        top_keywords = self._analyze_keywords()

        # Top cited papers
        top_cited = self._get_top_cited(limit=10)

        # Citation distribution (ranges)
        citation_dist = self._citation_distribution(citations)

        self._stats = BibliometricStats(
            total_papers=len(self.papers),
            total_citations=total_citations,
            avg_citations=total_citations / len(self.papers) if self.papers else 0,
            max_citations=max(citations) if citations else 0,
            min_citations=min(citations) if citations else 0,
            h_index=h_index,
            publication_years=publication_years,
            top_authors=top_authors,
            top_journals=top_journals,
            top_keywords=top_keywords,
            top_cited_papers=top_cited,
            author_collaborations=collaborations,
            papers_with_citations=papers_with_citations,
            citation_distribution=citation_dist
        )

        return self._stats

    def _empty_stats(self) -> BibliometricStats:
        """Return empty stats when no papers."""
        return BibliometricStats(
            total_papers=0,
            total_citations=0,
            avg_citations=0,
            max_citations=0,
            min_citations=0,
            h_index=0,
            publication_years={},
            top_authors=[],
            top_journals=[],
            top_keywords=[],
            top_cited_papers=[],
            author_collaborations={},
            papers_with_citations=0,
            citation_distribution={}
        )

    def _get_citations(self, paper: Dict) -> int:
        """Extract citation count from paper."""
        # Try different field names
        for field in ['citations_count', 'citation_count', 'citedby_count', 'num_citations']:
            if field in paper:
                try:
                    return int(paper[field]) if paper[field] else 0
                except (ValueError, TypeError):
                    pass
        return 0

    def _calculate_h_index(self, citations: List[int]) -> int:
        """
        Calculate h-index.

        h-index is the maximum value h such that h papers
        have at least h citations each.
        """
        if not citations:
            return 0

        sorted_citations = sorted(citations, reverse=True)
        h = 0
        for i, c in enumerate(sorted_citations):
            if c >= i + 1:
                h = i + 1
            else:
                break
        return h

    def _analyze_years(self) -> Dict[int, int]:
        """Analyze publication years distribution."""
        years = Counter()
        for paper in self.papers:
            year = paper.get('year') or paper.get('pub_year')
            if year:
                try:
                    year = int(year)
                    if 1900 <= year <= 2100:  # Sanity check
                        years[year] += 1
                except (ValueError, TypeError):
                    pass
        return dict(sorted(years.items()))

    def _analyze_authors(self) -> Tuple[List[Tuple[str, int]], Dict[str, List[str]]]:
        """
        Analyze author productivity and collaborations.

        Returns:
            Tuple of (top_authors list, collaboration dict)
        """
        author_counts = Counter()
        collaborations = defaultdict(set)

        for paper in self.papers:
            authors = paper.get('authors', [])
            if isinstance(authors, str):
                # Split string authors
                authors = [a.strip() for a in re.split(r'[,;]|and', authors) if a.strip()]

            # Normalize author names
            normalized = []
            for author in authors:
                if isinstance(author, dict):
                    name = author.get('name', '') or author.get('authname', '')
                else:
                    name = str(author)
                name = name.strip()
                if name and len(name) > 1:
                    normalized.append(name)

            # Count authors
            for author in normalized:
                author_counts[author] += 1

            # Track collaborations
            for i, author in enumerate(normalized):
                for coauthor in normalized[i+1:]:
                    collaborations[author].add(coauthor)
                    collaborations[coauthor].add(author)

        # Convert to list format
        top_authors = author_counts.most_common(20)
        collab_dict = {k: list(v) for k, v in collaborations.items()}

        return top_authors, collab_dict

    def _analyze_journals(self) -> List[Tuple[str, int]]:
        """Analyze journal distribution."""
        journals = Counter()
        for paper in self.papers:
            journal = paper.get('journal') or paper.get('venue') or paper.get('publicationName')
            if journal and isinstance(journal, str):
                journal = journal.strip()
                if journal and len(journal) > 2:
                    journals[journal] += 1
        return journals.most_common(15)

    def _analyze_keywords(self) -> List[Tuple[str, int]]:
        """Analyze keyword frequency."""
        keywords = Counter()

        for paper in self.papers:
            # Get keywords from various fields
            kw_list = paper.get('keywords', [])
            if isinstance(kw_list, str):
                kw_list = [k.strip() for k in kw_list.split(',') if k.strip()]

            # Also extract from subject/topics
            subjects = paper.get('subject', [])
            if isinstance(subjects, str):
                subjects = [s.strip() for s in subjects.split(',') if s.strip()]

            all_keywords = list(kw_list) + list(subjects)

            for kw in all_keywords:
                if isinstance(kw, str) and len(kw) > 2:
                    # Normalize
                    kw_normalized = kw.lower().strip()
                    keywords[kw_normalized] += 1

        return keywords.most_common(30)

    def _get_top_cited(self, limit: int = 10) -> List[Dict]:
        """Get top cited papers."""
        papers_with_cites = []
        for paper in self.papers:
            citations = self._get_citations(paper)
            papers_with_cites.append({
                'title': paper.get('title', 'Untitled'),
                'authors': paper.get('authors', []),
                'year': paper.get('year', ''),
                'journal': paper.get('journal', ''),
                'citations': citations,
                'doi': paper.get('doi', '')
            })

        # Sort by citations descending
        sorted_papers = sorted(papers_with_cites, key=lambda x: x['citations'], reverse=True)
        return sorted_papers[:limit]

    def _citation_distribution(self, citations: List[int]) -> Dict[str, int]:
        """Categorize papers by citation ranges."""
        distribution = {
            '0': 0,
            '1-10': 0,
            '11-50': 0,
            '51-100': 0,
            '101-500': 0,
            '500+': 0
        }

        for c in citations:
            if c == 0:
                distribution['0'] += 1
            elif c <= 10:
                distribution['1-10'] += 1
            elif c <= 50:
                distribution['11-50'] += 1
            elif c <= 100:
                distribution['51-100'] += 1
            elif c <= 500:
                distribution['101-500'] += 1
            else:
                distribution['500+'] += 1

        return distribution

    def get_summary_text(self) -> str:
        """Generate text summary of bibliometric analysis."""
        if not self._stats:
            self.analyze()

        stats = self._stats

        summary = f"""
## Bibliometric Summary

### Overview
- **Total Papers**: {stats.total_papers}
- **Total Citations**: {stats.total_citations:,}
- **Average Citations per Paper**: {stats.avg_citations:.1f}
- **H-Index**: {stats.h_index}
- **Papers with Citations**: {stats.papers_with_citations} ({stats.papers_with_citations/stats.total_papers*100:.1f}% if stats.total_papers else 0)

### Top Authors
{self._format_top_list(stats.top_authors[:5])}

### Top Journals
{self._format_top_list(stats.top_journals[:5])}

### Top Keywords
{self._format_top_list(stats.top_keywords[:10])}

### Publication Trend
{self._format_year_trend(stats.publication_years)}
"""
        return summary

    def _format_top_list(self, items: List[Tuple[str, int]]) -> str:
        """Format a top list for display."""
        if not items:
            return "No data available"
        lines = [f"{i+1}. {name} ({count})" for i, (name, count) in enumerate(items)]
        return "\n".join(lines)

    def _format_year_trend(self, years: Dict[int, int]) -> str:
        """Format year trend for display."""
        if not years:
            return "No data available"
        lines = [f"- {year}: {count} papers" for year, count in sorted(years.items())]
        return "\n".join(lines)


def create_publication_trend_chart(years: Dict[int, int]) -> Dict:
    """
    Create Plotly chart data for publication trends.

    Args:
        years: Dict mapping year to paper count

    Returns:
        Plotly figure dict
    """
    import plotly.graph_objects as go

    if not years:
        return None

    sorted_years = sorted(years.items())
    x_vals = [str(y) for y, _ in sorted_years]
    y_vals = [c for _, c in sorted_years]

    fig = go.Figure()

    # Bar chart
    fig.add_trace(go.Bar(
        x=x_vals,
        y=y_vals,
        marker_color='#2E8B57',
        name='Publications'
    ))

    # Trend line
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode='lines+markers',
        line=dict(color='#E67E22', width=2),
        marker=dict(size=8),
        name='Trend'
    ))

    fig.update_layout(
        title='Publication Trends Over Time',
        xaxis_title='Year',
        yaxis_title='Number of Publications',
        template='plotly_dark',
        paper_bgcolor='rgba(30,58,95,0.8)',
        plot_bgcolor='rgba(30,58,95,0.5)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )

    return fig


def create_journal_distribution_chart(journals: List[Tuple[str, int]]) -> Dict:
    """Create Plotly pie chart for journal distribution."""
    import plotly.graph_objects as go

    if not journals:
        return None

    # Take top 10
    top_journals = journals[:10]
    labels = [j[0][:30] + '...' if len(j[0]) > 30 else j[0] for j in top_journals]
    values = [j[1] for j in top_journals]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=[
            '#2E8B57', '#3CB371', '#90EE90', '#98FB98', '#00FA9A',
            '#00FF7F', '#7CFC00', '#7FFF00', '#ADFF2F', '#32CD32'
        ])
    )])

    fig.update_layout(
        title='Journal Distribution',
        template='plotly_dark',
        paper_bgcolor='rgba(30,58,95,0.8)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            orientation='v',
            yanchor='middle',
            y=0.5,
            xanchor='left',
            x=1.05,
            font=dict(size=10)
        )
    )

    return fig


def create_citation_distribution_chart(distribution: Dict[str, int]) -> Dict:
    """Create Plotly bar chart for citation distribution."""
    import plotly.graph_objects as go

    if not distribution:
        return None

    # Ordered categories
    categories = ['0', '1-10', '11-50', '51-100', '101-500', '500+']
    values = [distribution.get(c, 0) for c in categories]

    fig = go.Figure(data=[go.Bar(
        x=categories,
        y=values,
        marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    )])

    fig.update_layout(
        title='Citation Distribution',
        xaxis_title='Citations Range',
        yaxis_title='Number of Papers',
        template='plotly_dark',
        paper_bgcolor='rgba(30,58,95,0.8)',
        plot_bgcolor='rgba(30,58,95,0.5)',
        font=dict(color='white')
    )

    return fig


def create_author_chart(authors: List[Tuple[str, int]], limit: int = 10) -> Dict:
    """Create horizontal bar chart for top authors."""
    import plotly.graph_objects as go

    if not authors:
        return None

    top_authors = authors[:limit]
    # Reverse for horizontal bar chart (top at top)
    names = [a[0] for a in reversed(top_authors)]
    counts = [a[1] for a in reversed(top_authors)]

    fig = go.Figure(data=[go.Bar(
        x=counts,
        y=names,
        orientation='h',
        marker_color='#E67E22'
    )])

    fig.update_layout(
        title='Top Authors by Publications',
        xaxis_title='Number of Publications',
        yaxis_title='Author',
        template='plotly_dark',
        paper_bgcolor='rgba(30,58,95,0.8)',
        plot_bgcolor='rgba(30,58,95,0.5)',
        font=dict(color='white'),
        height=400
    )

    return fig


def create_keyword_chart(keywords: List[Tuple[str, int]], limit: int = 15) -> Dict:
    """Create horizontal bar chart for keywords."""
    import plotly.graph_objects as go

    if not keywords:
        return None

    top_kw = keywords[:limit]
    names = [k[0] for k in reversed(top_kw)]
    counts = [k[1] for k in reversed(top_kw)]

    fig = go.Figure(data=[go.Bar(
        x=counts,
        y=names,
        orientation='h',
        marker_color='#9B59B6'
    )])

    fig.update_layout(
        title='Top Keywords',
        xaxis_title='Frequency',
        yaxis_title='Keyword',
        template='plotly_dark',
        paper_bgcolor='rgba(30,58,95,0.8)',
        plot_bgcolor='rgba(30,58,95,0.5)',
        font=dict(color='white'),
        height=450
    )

    return fig
