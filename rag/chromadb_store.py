"""
BiblioAgent AI - ChromaDB Vector Store
======================================
Vector database for semantic search and paper embeddings using ChromaDB.
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class PaperEmbeddings:
    """Container for paper embedding data."""
    paper_id: str
    title: str
    embedding: List[float]
    metadata: Dict


class ChromaDBStore:
    """
    ChromaDB-based vector store for paper embeddings.

    Uses sentence-transformers for local embedding generation
    to avoid API costs. ChromaDB provides persistent storage
    and efficient similarity search.

    Features:
    - Local embedding generation (no API costs)
    - Persistent storage for resume capability
    - Semantic similarity search for screening
    - Deduplication via embedding similarity
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Fast and efficient
    COLLECTION_NAME = "biblioagent_papers"

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        embedding_model: str = None,
        collection_name: str = None
    ):
        """
        Initialize ChromaDB store.

        Args:
            persist_directory: Directory for persistent storage
            embedding_model: Sentence transformer model name
            collection_name: Name for the ChromaDB collection
        """
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model or self.DEFAULT_MODEL
        self.collection_name = collection_name or self.COLLECTION_NAME

        self._embedding_model = None
        self._client = None
        self._collection = None

        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)

    def _get_embedding_model(self):
        """Lazy load the embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info(f"Loaded embedding model: {self.embedding_model_name}")
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise ImportError(
                    "Please install sentence-transformers: pip install sentence-transformers"
                )
        return self._embedding_model

    def _get_client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    )
                )
                logger.info(f"ChromaDB client initialized at {self.persist_directory}")
            except ImportError:
                logger.error("chromadb not installed")
                raise ImportError("Please install chromadb: pip install chromadb")
        return self._client

    def _get_collection(self):
        """Get or create the papers collection."""
        if self._collection is None:
            client = self._get_client()

            # Custom embedding function using sentence-transformers
            class SentenceTransformerEmbedding:
                def __init__(self, model):
                    self.model = model

                def __call__(self, input: List[str]) -> List[List[float]]:
                    embeddings = self.model.encode(input)
                    return embeddings.tolist()

            embedding_fn = SentenceTransformerEmbedding(self._get_embedding_model())

            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_fn
            )
            logger.info(f"Collection '{self.collection_name}' ready with {self._collection.count()} documents")

        return self._collection

    def _generate_paper_id(self, paper: Dict) -> str:
        """Generate a unique ID for a paper."""
        # Use DOI if available, otherwise hash title
        doi = paper.get("doi", "")
        if doi:
            return f"doi:{doi}"

        title = paper.get("title", "").lower().strip()
        title_hash = hashlib.md5(title.encode()).hexdigest()[:16]
        return f"title:{title_hash}"

    def _paper_to_document(self, paper: Dict) -> Tuple[str, str, Dict]:
        """Convert paper dict to ChromaDB document format."""
        paper_id = self._generate_paper_id(paper)

        # Combine title and abstract for embedding
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        document = f"{title}. {abstract}"

        # Metadata (ChromaDB only supports primitive types)
        metadata = {
            "doi": paper.get("doi", ""),
            "title": title[:500],  # Limit length
            "year": paper.get("year", 0),
            "authors": ", ".join(paper.get("authors", [])[:5]),  # First 5 authors
            "journal": paper.get("journal", "")[:200],
            "source": paper.get("source_database", "unknown"),
        }

        return paper_id, document, metadata

    def add_papers(self, papers: List[Dict]) -> int:
        """
        Add papers to the vector store.

        Args:
            papers: List of paper dictionaries

        Returns:
            Number of papers added
        """
        collection = self._get_collection()

        ids = []
        documents = []
        metadatas = []

        for paper in papers:
            paper_id, document, metadata = self._paper_to_document(paper)

            # Skip if already exists
            try:
                existing = collection.get(ids=[paper_id])
                if existing and existing["ids"]:
                    continue
            except:
                pass

            ids.append(paper_id)
            documents.append(document)
            metadatas.append(metadata)

        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Added {len(ids)} papers to vector store")

        return len(ids)

    def search_similar(
        self,
        query: str,
        n_results: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> List[Dict]:
        """
        Search for papers similar to the query.

        Args:
            query: Search query text
            n_results: Number of results to return
            where: Metadata filter (e.g., {"year": {"$gte": 2020}})
            where_document: Document content filter

        Returns:
            List of matching papers with similarity scores
        """
        collection = self._get_collection()

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )

        papers = []
        if results and results["ids"]:
            for i, paper_id in enumerate(results["ids"][0]):
                paper = {
                    "id": paper_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "similarity": 1 - results["distances"][0][i] if results["distances"] else 1,
                }
                papers.append(paper)

        return papers

    def find_similar_papers(
        self,
        paper: Dict,
        threshold: float = 0.9
    ) -> List[Dict]:
        """
        Find papers similar to the given paper (for deduplication).

        Args:
            paper: Paper to find duplicates of
            threshold: Similarity threshold (0-1)

        Returns:
            List of similar papers above threshold
        """
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        query = f"{title}. {abstract}"

        results = self.search_similar(query, n_results=5)

        # Filter by threshold
        similar = [
            r for r in results
            if r["similarity"] >= threshold
        ]

        return similar

    def search_by_criteria(
        self,
        inclusion_criteria: List[str],
        n_results: int = 100
    ) -> List[Dict]:
        """
        Search for papers matching inclusion criteria.

        Args:
            inclusion_criteria: List of criteria strings
            n_results: Maximum results per criterion

        Returns:
            Combined list of matching papers
        """
        all_results = {}

        for criterion in inclusion_criteria:
            results = self.search_similar(criterion, n_results=n_results)

            for paper in results:
                paper_id = paper["id"]
                if paper_id not in all_results:
                    paper["matched_criteria"] = [criterion]
                    all_results[paper_id] = paper
                else:
                    all_results[paper_id]["matched_criteria"].append(criterion)
                    # Average the similarity scores
                    all_results[paper_id]["similarity"] = (
                        all_results[paper_id]["similarity"] + paper["similarity"]
                    ) / 2

        # Sort by number of matched criteria and similarity
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: (len(x.get("matched_criteria", [])), x["similarity"]),
            reverse=True
        )

        return sorted_results

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Get a paper by ID."""
        collection = self._get_collection()

        try:
            result = collection.get(
                ids=[paper_id],
                include=["documents", "metadatas"]
            )

            if result and result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
        except Exception as e:
            logger.error(f"Error getting paper {paper_id}: {e}")

        return None

    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper by ID."""
        collection = self._get_collection()

        try:
            collection.delete(ids=[paper_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting paper {paper_id}: {e}")
            return False

    def clear(self):
        """Clear all papers from the collection."""
        client = self._get_client()
        try:
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info(f"Cleared collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    def get_stats(self) -> Dict:
        """Get collection statistics."""
        collection = self._get_collection()

        return {
            "name": self.collection_name,
            "count": collection.count(),
            "persist_directory": self.persist_directory,
            "embedding_model": self.embedding_model_name,
        }

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        model = self._get_embedding_model()
        embedding = model.encode(text)
        return embedding.tolist()

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        import numpy as np

        model = self._get_embedding_model()
        emb1 = model.encode(text1)
        emb2 = model.encode(text2)

        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
