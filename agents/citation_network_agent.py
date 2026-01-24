"""
Citation Network Agent
======================
Builds citation network graphs for Connected Papers-style visualization.

Features:
- Build network from seed papers
- Calculate centrality metrics (PageRank, betweenness)
- Detect research clusters using community detection
- Generate visualization data for Plotly/Pyvis
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# Check for networkx availability
NETWORKX_AVAILABLE = False
try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
    NETWORKX_AVAILABLE = True
except ImportError:
    logger.warning("networkx not available - citation network features disabled")


@dataclass
class CitationNode:
    """Represents a paper in the citation network."""
    paper_id: str
    title: str = ""
    year: int = 0
    authors: List[str] = field(default_factory=list)
    citations: int = 0
    doi: Optional[str] = None
    is_seed: bool = False
    cluster_id: int = 0
    centrality_score: float = 0.0
    depth: int = 0  # Distance from seed papers

    def to_dict(self) -> Dict[str, Any]:
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'year': self.year,
            'authors': self.authors,
            'citations': self.citations,
            'doi': self.doi,
            'is_seed': self.is_seed,
            'cluster_id': self.cluster_id,
            'centrality_score': self.centrality_score,
            'depth': self.depth,
        }


@dataclass
class CitationEdge:
    """Represents a citation relationship."""
    source_id: str
    target_id: str
    weight: float = 1.0  # Can be based on citation influence
    edge_type: str = "cites"  # cites, cited_by, co_citation

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source_id,
            'target': self.target_id,
            'weight': self.weight,
            'type': self.edge_type,
        }


@dataclass
class NetworkData:
    """Complete network data for visualization."""
    nodes: List[CitationNode] = field(default_factory=list)
    edges: List[CitationEdge] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    clusters: Dict[int, List[str]] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
            'metrics': self.metrics,
            'clusters': self.clusters,
            'generated_at': self.generated_at,
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'cluster_count': len(self.clusters),
        }

    def to_plotly_data(self) -> Dict[str, Any]:
        """Convert to Plotly-compatible format for visualization."""
        # Create node positions using a layout algorithm
        if not NETWORKX_AVAILABLE or not self.nodes:
            return {'nodes': [], 'edges': []}

        # Build networkx graph for layout
        G = nx.DiGraph()
        for node in self.nodes:
            G.add_node(node.paper_id, **node.to_dict())
        for edge in self.edges:
            G.add_edge(edge.source_id, edge.target_id, weight=edge.weight)

        # Calculate layout
        try:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        except Exception:
            pos = nx.random_layout(G)

        # Build Plotly data
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []

        for node in self.nodes:
            if node.paper_id in pos:
                x, y = pos[node.paper_id]
                node_x.append(x)
                node_y.append(y)
                node_text.append(f"{node.title[:50]}...<br>Year: {node.year}<br>Citations: {node.citations}")
                # Size based on citations (log scale)
                size = max(10, min(50, 10 + (node.citations ** 0.5)))
                node_size.append(size)
                node_color.append(node.cluster_id)

        edge_x = []
        edge_y = []

        for edge in self.edges:
            if edge.source_id in pos and edge.target_id in pos:
                x0, y0 = pos[edge.source_id]
                x1, y1 = pos[edge.target_id]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

        return {
            'node_x': node_x,
            'node_y': node_y,
            'node_text': node_text,
            'node_size': node_size,
            'node_color': node_color,
            'edge_x': edge_x,
            'edge_y': edge_y,
        }


class CitationNetworkAgent:
    """
    Agent for building and analyzing citation networks.

    Creates Connected Papers-style network graphs from seed papers,
    expanding through citations and references.
    """

    def __init__(
        self,
        s2_api_key: str = None,
        max_depth: int = 2,
        max_papers: int = 50,
        min_citations: int = 5
    ):
        """
        Initialize the citation network agent.

        Args:
            s2_api_key: Semantic Scholar API key
            max_depth: Maximum depth from seed papers
            max_papers: Maximum papers in network
            min_citations: Minimum citations to include paper
        """
        self.s2_api_key = s2_api_key
        self.max_depth = max_depth
        self.max_papers = max_papers
        self.min_citations = min_citations

        # Internal graph (if networkx available)
        self._graph = nx.DiGraph() if NETWORKX_AVAILABLE else None

        # Paper cache
        self._paper_cache: Dict[str, CitationNode] = {}
        self._edges: List[CitationEdge] = []

    def build_network(
        self,
        seed_papers: List[Dict],
        include_references: bool = True,
        include_citations: bool = True,
        progress_callback: callable = None
    ) -> NetworkData:
        """
        Build citation network from seed papers.

        Args:
            seed_papers: List of paper dicts with 'doi', 'title', etc.
            include_references: Include papers referenced by seeds
            include_citations: Include papers that cite seeds
            progress_callback: Optional callback for progress updates

        Returns:
            NetworkData object with nodes and edges
        """
        if not NETWORKX_AVAILABLE:
            logger.error("networkx required for citation network")
            return NetworkData()

        logger.info(f"Building citation network from {len(seed_papers)} seed papers")

        # Reset internal state
        self._graph = nx.DiGraph()
        self._paper_cache = {}
        self._edges = []

        # Process seed papers
        for paper in seed_papers:
            node = self._create_node_from_paper(paper, is_seed=True, depth=0)
            if node:
                self._add_node(node)

        if progress_callback:
            progress_callback(10, "Processed seed papers")

        # Expand network
        current_depth = 0
        papers_to_expand = list(self._paper_cache.values())

        while current_depth < self.max_depth and len(self._paper_cache) < self.max_papers:
            current_depth += 1
            new_papers = []

            for paper in papers_to_expand:
                if len(self._paper_cache) >= self.max_papers:
                    break

                # Get related papers
                related = self._get_related_papers(paper, include_references, include_citations)

                for rel_paper, edge_type in related:
                    if rel_paper.paper_id not in self._paper_cache:
                        rel_paper.depth = current_depth
                        self._add_node(rel_paper)
                        new_papers.append(rel_paper)

                    # Add edge
                    if edge_type == "references":
                        edge = CitationEdge(paper.paper_id, rel_paper.paper_id, edge_type="cites")
                    else:
                        edge = CitationEdge(rel_paper.paper_id, paper.paper_id, edge_type="cites")
                    self._add_edge(edge)

            papers_to_expand = new_papers

            if progress_callback:
                progress = 10 + int(60 * (current_depth / self.max_depth))
                progress_callback(progress, f"Expanded to depth {current_depth}")

        if progress_callback:
            progress_callback(70, "Calculating metrics")

        # Calculate metrics
        metrics = self.calculate_centrality()

        if progress_callback:
            progress_callback(85, "Detecting clusters")

        # Detect clusters
        clusters = self.detect_clusters()

        if progress_callback:
            progress_callback(100, "Network complete")

        # Build result
        network_data = NetworkData(
            nodes=list(self._paper_cache.values()),
            edges=self._edges,
            metrics=metrics,
            clusters=clusters
        )

        logger.info(f"Built network with {len(network_data.nodes)} nodes, {len(network_data.edges)} edges")

        return network_data

    def _create_node_from_paper(
        self,
        paper: Dict,
        is_seed: bool = False,
        depth: int = 0
    ) -> Optional[CitationNode]:
        """Create CitationNode from paper dictionary."""
        # Extract paper ID (prefer S2 paper ID, then DOI)
        paper_id = paper.get('s2_paper_id') or paper.get('paper_id')
        if not paper_id and paper.get('doi'):
            paper_id = f"doi:{paper['doi']}"
        if not paper_id:
            return None

        return CitationNode(
            paper_id=paper_id,
            title=paper.get('title', ''),
            year=paper.get('year', 0),
            authors=paper.get('authors', [])[:5],  # Limit authors
            citations=paper.get('citation_count', 0) or paper.get('citations', 0),
            doi=paper.get('doi'),
            is_seed=is_seed,
            depth=depth
        )

    def _add_node(self, node: CitationNode):
        """Add node to graph and cache."""
        self._paper_cache[node.paper_id] = node
        if self._graph is not None:
            self._graph.add_node(node.paper_id, **node.to_dict())

    def _add_edge(self, edge: CitationEdge):
        """Add edge to graph."""
        # Avoid duplicate edges
        existing = [(e.source_id, e.target_id) for e in self._edges]
        if (edge.source_id, edge.target_id) not in existing:
            self._edges.append(edge)
            if self._graph is not None:
                self._graph.add_edge(edge.source_id, edge.target_id, weight=edge.weight)

    def _get_related_papers(
        self,
        paper: CitationNode,
        include_references: bool,
        include_citations: bool
    ) -> List[Tuple[CitationNode, str]]:
        """Get related papers (references and citations) for a paper."""
        related = []

        # Try to fetch from Semantic Scholar
        try:
            from api.semantic_scholar import SemanticScholarClient
            client = SemanticScholarClient(api_key=self.s2_api_key)

            paper_id = paper.paper_id
            if paper_id.startswith('doi:'):
                paper_id = f"DOI:{paper_id[4:]}"

            if include_references:
                refs = client.get_paper_references(paper_id, limit=10)
                for ref in refs:
                    if ref.get('citationCount', 0) >= self.min_citations:
                        node = self._create_node_from_paper(ref)
                        if node:
                            related.append((node, "references"))

            if include_citations:
                cites = client.get_paper_citations(paper_id, limit=10)
                for cite in cites:
                    if cite.get('citationCount', 0) >= self.min_citations:
                        node = self._create_node_from_paper(cite)
                        if node:
                            related.append((node, "citations"))

        except Exception as e:
            logger.debug(f"Error fetching related papers: {e}")

        return related

    def calculate_centrality(self) -> Dict[str, float]:
        """
        Calculate centrality metrics for the network.

        Returns:
            Dictionary with paper_id -> centrality scores
        """
        if not NETWORKX_AVAILABLE or not self._graph:
            return {}

        metrics = {
            'pagerank': {},
            'betweenness': {},
            'degree': {},
        }

        try:
            # PageRank - importance based on link structure
            pagerank = nx.pagerank(self._graph, weight='weight')
            metrics['pagerank'] = pagerank

            # Update nodes with centrality scores
            for paper_id, score in pagerank.items():
                if paper_id in self._paper_cache:
                    self._paper_cache[paper_id].centrality_score = score

            # Betweenness centrality - bridge papers
            if len(self._graph) > 2:
                betweenness = nx.betweenness_centrality(self._graph)
                metrics['betweenness'] = betweenness

            # Degree centrality
            degree = nx.degree_centrality(self._graph)
            metrics['degree'] = degree

        except Exception as e:
            logger.error(f"Error calculating centrality: {e}")

        return metrics

    def detect_clusters(self) -> Dict[int, List[str]]:
        """
        Detect research clusters using community detection.

        Returns:
            Dictionary mapping cluster_id -> list of paper_ids
        """
        if not NETWORKX_AVAILABLE or not self._graph:
            return {}

        clusters = {}

        try:
            # Convert to undirected for community detection
            G_undirected = self._graph.to_undirected()

            if len(G_undirected) < 3:
                return {0: list(self._paper_cache.keys())}

            # Use Louvain community detection
            communities = nx_community.louvain_communities(G_undirected, seed=42)

            for cluster_id, community in enumerate(communities):
                clusters[cluster_id] = list(community)

                # Update node cluster assignments
                for paper_id in community:
                    if paper_id in self._paper_cache:
                        self._paper_cache[paper_id].cluster_id = cluster_id

        except Exception as e:
            logger.error(f"Error detecting clusters: {e}")
            # Fallback: all in one cluster
            clusters = {0: list(self._paper_cache.keys())}

        return clusters

    def get_key_papers(self, top_n: int = 10) -> List[CitationNode]:
        """
        Get most important papers based on centrality.

        Args:
            top_n: Number of papers to return

        Returns:
            List of top papers sorted by centrality
        """
        papers = list(self._paper_cache.values())
        papers.sort(key=lambda p: p.centrality_score, reverse=True)
        return papers[:top_n]

    def get_cluster_summary(self) -> Dict[int, Dict[str, Any]]:
        """
        Get summary information for each cluster.

        Returns:
            Dictionary with cluster_id -> summary info
        """
        cluster_summary = {}

        for node in self._paper_cache.values():
            cluster_id = node.cluster_id

            if cluster_id not in cluster_summary:
                cluster_summary[cluster_id] = {
                    'paper_count': 0,
                    'total_citations': 0,
                    'year_range': [9999, 0],
                    'top_papers': [],
                }

            summary = cluster_summary[cluster_id]
            summary['paper_count'] += 1
            summary['total_citations'] += node.citations

            if node.year > 0:
                summary['year_range'][0] = min(summary['year_range'][0], node.year)
                summary['year_range'][1] = max(summary['year_range'][1], node.year)

            # Track top papers
            summary['top_papers'].append((node.citations, node.title[:50]))
            summary['top_papers'].sort(reverse=True)
            summary['top_papers'] = summary['top_papers'][:3]

        return cluster_summary

    def find_bridge_papers(self, min_betweenness: float = 0.1) -> List[CitationNode]:
        """
        Find papers that bridge different clusters/research areas.

        Args:
            min_betweenness: Minimum betweenness centrality threshold

        Returns:
            List of bridge papers
        """
        if not NETWORKX_AVAILABLE or not self._graph:
            return []

        try:
            betweenness = nx.betweenness_centrality(self._graph)
            bridge_ids = [pid for pid, score in betweenness.items() if score >= min_betweenness]
            return [self._paper_cache[pid] for pid in bridge_ids if pid in self._paper_cache]
        except Exception:
            return []

    def get_co_citation_pairs(self, min_co_citations: int = 3) -> List[Tuple[str, str, int]]:
        """
        Find papers frequently co-cited together.

        Args:
            min_co_citations: Minimum co-citation count

        Returns:
            List of (paper1_id, paper2_id, co_citation_count) tuples
        """
        # Track which papers cite each paper
        cited_by: Dict[str, Set[str]] = defaultdict(set)

        for edge in self._edges:
            cited_by[edge.target_id].add(edge.source_id)

        # Find co-citation pairs
        co_citations = []
        paper_ids = list(self._paper_cache.keys())

        for i, paper1 in enumerate(paper_ids):
            for paper2 in paper_ids[i + 1:]:
                # Papers citing both
                common_citers = cited_by[paper1] & cited_by[paper2]
                if len(common_citers) >= min_co_citations:
                    co_citations.append((paper1, paper2, len(common_citers)))

        co_citations.sort(key=lambda x: x[2], reverse=True)
        return co_citations[:20]


# Async wrapper for integration with orchestrator
async def build_citation_network(
    seed_papers: List[Dict],
    s2_api_key: str = None,
    max_depth: int = 2,
    progress_callback: callable = None
) -> Dict[str, Any]:
    """
    Async function to build citation network.

    Args:
        seed_papers: List of paper dictionaries
        s2_api_key: Optional Semantic Scholar API key
        max_depth: Maximum depth from seed papers
        progress_callback: Optional progress callback

    Returns:
        Network data dictionary
    """
    agent = CitationNetworkAgent(s2_api_key=s2_api_key, max_depth=max_depth)

    # Run synchronous build in executor
    loop = asyncio.get_event_loop()
    network = await loop.run_in_executor(
        None,
        lambda: agent.build_network(seed_papers, progress_callback=progress_callback)
    )

    return network.to_dict()


if __name__ == "__main__":
    # Test the agent
    if not NETWORKX_AVAILABLE:
        print("networkx not installed. Run: pip install networkx")
        exit(1)

    # Test with sample papers
    seed_papers = [
        {
            'doi': '10.18653/v1/N19-1423',
            'title': 'BERT: Pre-training of Deep Bidirectional Transformers',
            'year': 2019,
            'citation_count': 50000,
            'paper_id': 'bert_paper'
        },
        {
            'doi': '10.48550/arXiv.1706.03762',
            'title': 'Attention Is All You Need',
            'year': 2017,
            'citation_count': 80000,
            'paper_id': 'transformer_paper'
        }
    ]

    agent = CitationNetworkAgent(max_depth=1, max_papers=20)

    def progress(percent, msg):
        print(f"[{percent}%] {msg}")

    network = agent.build_network(seed_papers, progress_callback=progress)

    print(f"\nNetwork built:")
    print(f"  Nodes: {len(network.nodes)}")
    print(f"  Edges: {len(network.edges)}")
    print(f"  Clusters: {len(network.clusters)}")

    print("\nTop papers by centrality:")
    for paper in agent.get_key_papers(5):
        print(f"  - {paper.title[:50]}... (centrality: {paper.centrality_score:.4f})")

    print("\nCluster summary:")
    for cluster_id, summary in agent.get_cluster_summary().items():
        print(f"  Cluster {cluster_id}: {summary['paper_count']} papers, {summary['total_citations']} total citations")
