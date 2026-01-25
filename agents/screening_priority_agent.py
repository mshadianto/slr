"""
Muezza AI - AI Priority Screening Agent
========================================
Rayyan-style AI priority rating system using active learning.

Features:
- 5-star ratings based on screening decisions
- Active learning with incremental model updates
- Priority queue for efficient screening workflow
- Minimum 50 decisions before computing ratings (like Rayyan)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
except ImportError:
    LogisticRegression = None
    StandardScaler = None

logger = logging.getLogger(__name__)


@dataclass
class ScreeningRating:
    """
    Represents the AI-computed priority rating for a paper.

    Attributes:
        paper_doi: DOI of the rated paper
        rating: 1-5 star rating
        confidence: Model confidence (0-1)
        relevance_score: Raw relevance probability (0-1)
        matched_criteria: List of matched inclusion criteria
        computed_at: Timestamp when rating was computed
    """
    paper_doi: str
    rating: float
    confidence: float
    relevance_score: float
    matched_criteria: List[str] = field(default_factory=list)
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "paper_doi": self.paper_doi,
            "rating": self.rating,
            "confidence": self.confidence,
            "relevance_score": self.relevance_score,
            "matched_criteria": self.matched_criteria,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreeningRating":
        """Create from dictionary."""
        return cls(
            paper_doi=data["paper_doi"],
            rating=data["rating"],
            confidence=data["confidence"],
            relevance_score=data["relevance_score"],
            matched_criteria=data.get("matched_criteria", []),
            computed_at=data.get("computed_at", datetime.now().isoformat()),
        )

    @property
    def star_display(self) -> str:
        """Get star emoji display."""
        full_stars = int(self.rating)
        half_star = (self.rating - full_stars) >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)
        return "★" * full_stars + ("½" if half_star else "") + "☆" * empty_stars


class ScreeningPriorityAgent:
    """
    AI-powered screening priority agent using active learning.

    Implements Rayyan-style priority ratings:
    - Learns from user's include/exclude decisions
    - Predicts relevance for unscreened papers
    - Converts predictions to 1-5 star ratings
    - Requires minimum 50 decisions before computing ratings

    Usage:
        agent = ScreeningPriorityAgent()

        # After user makes 50+ decisions
        if agent.can_compute_ratings(len(included) + len(excluded)):
            ratings = await agent.compute_ratings(pending, included, excluded)
            priority_queue = agent.get_priority_queue(pending)
    """

    # Minimum decisions required before computing ratings (like Rayyan)
    MIN_DECISIONS_FOR_TRAINING = 50

    # Model parameters
    DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        min_decisions: int = MIN_DECISIONS_FOR_TRAINING
    ):
        """
        Initialize the screening priority agent.

        Args:
            embedding_model: Name of the sentence transformer model
            min_decisions: Minimum decisions required before training
        """
        self.embedding_model_name = embedding_model
        self.min_decisions = min_decisions

        # Lazy loading for embedder
        self._embedder: Optional[SentenceTransformer] = None

        # Classifier and scaler
        self._classifier: Optional[LogisticRegression] = None
        self._scaler: Optional[StandardScaler] = None

        # Cache for embeddings
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Computed ratings
        self._ratings: Dict[str, ScreeningRating] = {}

        # Training state
        self._is_trained = False
        self._training_decisions_count = 0
        self._last_trained_at: Optional[str] = None

    @property
    def embedder(self) -> Optional[SentenceTransformer]:
        """Lazy load the sentence transformer model."""
        if self._embedder is None and SentenceTransformer is not None:
            try:
                self._embedder = SentenceTransformer(self.embedding_model_name)
                logger.info(f"Loaded embedding model: {self.embedding_model_name}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
        return self._embedder

    def can_compute_ratings(self, decisions_count: int) -> bool:
        """
        Check if minimum decisions have been reached.

        Args:
            decisions_count: Total number of include + exclude decisions

        Returns:
            True if ratings can be computed
        """
        return decisions_count >= self.min_decisions

    def get_decisions_progress(self, decisions_count: int) -> Dict[str, Any]:
        """
        Get progress towards minimum decisions.

        Args:
            decisions_count: Current number of decisions

        Returns:
            Dict with progress information
        """
        return {
            "current": decisions_count,
            "required": self.min_decisions,
            "percentage": min(100, int(decisions_count / self.min_decisions * 100)),
            "can_compute": self.can_compute_ratings(decisions_count),
            "remaining": max(0, self.min_decisions - decisions_count),
        }

    def _get_paper_text(self, paper: Dict) -> str:
        """Extract text content from paper for embedding."""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        keywords = " ".join(paper.get("keywords", []))
        return f"{title} {abstract} {keywords}".strip()

    def _get_embedding(self, paper: Dict) -> Optional[np.ndarray]:
        """
        Get embedding for a paper (with caching).

        Args:
            paper: Paper dictionary

        Returns:
            Embedding vector or None if failed
        """
        doi = paper.get("doi", "")
        if doi in self._embedding_cache:
            return self._embedding_cache[doi]

        if self.embedder is None:
            return None

        try:
            text = self._get_paper_text(paper)
            if not text:
                return None

            embedding = self.embedder.encode(text, convert_to_numpy=True)
            if doi:
                self._embedding_cache[doi] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Failed to compute embedding for {doi}: {e}")
            return None

    def _prepare_training_data(
        self,
        included: List[Dict],
        excluded: List[Dict]
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Prepare training data from screening decisions.

        Args:
            included: List of included papers
            excluded: List of excluded papers

        Returns:
            Tuple of (X embeddings, y labels) or (None, None) if failed
        """
        X_list = []
        y_list = []

        # Process included papers (label = 1)
        for paper in included:
            embedding = self._get_embedding(paper)
            if embedding is not None:
                X_list.append(embedding)
                y_list.append(1)

        # Process excluded papers (label = 0)
        for paper in excluded:
            embedding = self._get_embedding(paper)
            if embedding is not None:
                X_list.append(embedding)
                y_list.append(0)

        if len(X_list) < 10:  # Need minimum samples
            logger.warning(f"Insufficient training samples: {len(X_list)}")
            return None, None

        return np.array(X_list), np.array(y_list)

    def _train_classifier(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> bool:
        """
        Train the relevance classifier.

        Args:
            X: Feature matrix (embeddings)
            y: Labels (1=include, 0=exclude)

        Returns:
            True if training succeeded
        """
        if LogisticRegression is None or StandardScaler is None:
            logger.error("scikit-learn not available")
            return False

        try:
            # Scale features
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)

            # Train classifier with balanced class weights
            self._classifier = LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
                C=1.0,
            )
            self._classifier.fit(X_scaled, y)

            self._is_trained = True
            self._training_decisions_count = len(y)
            self._last_trained_at = datetime.now().isoformat()

            logger.info(f"Classifier trained on {len(y)} samples")
            return True

        except Exception as e:
            logger.error(f"Classifier training failed: {e}")
            return False

    def _predict_relevance(
        self,
        papers: List[Dict]
    ) -> List[Tuple[str, float, float]]:
        """
        Predict relevance scores for papers.

        Args:
            papers: List of papers to score

        Returns:
            List of (doi, probability, confidence) tuples
        """
        if not self._is_trained or self._classifier is None:
            return []

        results = []
        for paper in papers:
            doi = paper.get("doi", "")
            embedding = self._get_embedding(paper)

            if embedding is None:
                # Default to middle score if embedding fails
                results.append((doi, 0.5, 0.0))
                continue

            try:
                X = self._scaler.transform(embedding.reshape(1, -1))
                prob = self._classifier.predict_proba(X)[0]

                # prob[1] is probability of inclusion
                relevance = float(prob[1])

                # Confidence based on distance from 0.5
                confidence = abs(relevance - 0.5) * 2

                results.append((doi, relevance, confidence))

            except Exception as e:
                logger.error(f"Prediction failed for {doi}: {e}")
                results.append((doi, 0.5, 0.0))

        return results

    @staticmethod
    def _relevance_to_stars(relevance: float) -> float:
        """
        Convert relevance probability to 1-5 star rating.

        Mapping:
        - 0.0-0.2 → 1 star
        - 0.2-0.4 → 2 stars
        - 0.4-0.6 → 3 stars
        - 0.6-0.8 → 4 stars
        - 0.8-1.0 → 5 stars

        Args:
            relevance: Relevance probability (0-1)

        Returns:
            Star rating (1-5)
        """
        # Linear mapping with minimum of 1 star
        return max(1.0, min(5.0, 1.0 + relevance * 4.0))

    async def compute_ratings(
        self,
        pending_papers: List[Dict],
        included_papers: List[Dict],
        excluded_papers: List[Dict],
        inclusion_criteria: Optional[List[str]] = None
    ) -> List[ScreeningRating]:
        """
        Compute AI priority ratings for pending papers.

        Args:
            pending_papers: Papers awaiting screening
            included_papers: Papers already included
            excluded_papers: Papers already excluded
            inclusion_criteria: List of inclusion criteria (optional)

        Returns:
            List of ScreeningRating objects sorted by rating (descending)
        """
        total_decisions = len(included_papers) + len(excluded_papers)

        if not self.can_compute_ratings(total_decisions):
            logger.warning(
                f"Cannot compute ratings: {total_decisions}/{self.min_decisions} decisions"
            )
            return []

        # Prepare training data
        X, y = self._prepare_training_data(included_papers, excluded_papers)
        if X is None or y is None:
            logger.error("Failed to prepare training data")
            return []

        # Train classifier
        if not self._train_classifier(X, y):
            logger.error("Failed to train classifier")
            return []

        # Predict relevance for pending papers
        predictions = self._predict_relevance(pending_papers)

        # Create rating objects
        ratings = []
        paper_map = {p.get("doi", ""): p for p in pending_papers}

        for doi, relevance, confidence in predictions:
            paper = paper_map.get(doi, {})

            # Find matched criteria (simple keyword matching)
            matched = []
            if inclusion_criteria:
                paper_text = self._get_paper_text(paper).lower()
                for criterion in inclusion_criteria:
                    if any(word.lower() in paper_text for word in criterion.split()):
                        matched.append(criterion)

            rating = ScreeningRating(
                paper_doi=doi,
                rating=self._relevance_to_stars(relevance),
                confidence=confidence,
                relevance_score=relevance,
                matched_criteria=matched[:3],  # Top 3 matches
            )

            ratings.append(rating)
            self._ratings[doi] = rating

        # Sort by rating (highest first)
        ratings.sort(key=lambda r: r.rating, reverse=True)

        logger.info(f"Computed ratings for {len(ratings)} papers")
        return ratings

    def get_rating(self, paper_doi: str) -> Optional[ScreeningRating]:
        """
        Get cached rating for a paper.

        Args:
            paper_doi: DOI of the paper

        Returns:
            ScreeningRating or None if not computed
        """
        return self._ratings.get(paper_doi)

    def get_priority_queue(
        self,
        papers: List[Dict],
        min_rating: float = 1.0
    ) -> List[Dict]:
        """
        Get papers sorted by priority (highest rated first).

        Args:
            papers: List of papers to sort
            min_rating: Minimum rating to include (default 1.0)

        Returns:
            Papers sorted by AI rating with rating info attached
        """
        result = []

        for paper in papers:
            doi = paper.get("doi", "")
            rating = self._ratings.get(doi)

            if rating is None:
                # Unrated papers go to end with default score
                paper_copy = paper.copy()
                paper_copy["ai_priority_rating"] = 0.0
                paper_copy["ai_priority_confidence"] = 0.0
                paper_copy["ai_relevance_score"] = 0.0
                paper_copy["ai_star_display"] = "☆☆☆☆☆"
                result.append(paper_copy)
            elif rating.rating >= min_rating:
                paper_copy = paper.copy()
                paper_copy["ai_priority_rating"] = rating.rating
                paper_copy["ai_priority_confidence"] = rating.confidence
                paper_copy["ai_relevance_score"] = rating.relevance_score
                paper_copy["ai_star_display"] = rating.star_display
                paper_copy["ai_matched_criteria"] = rating.matched_criteria
                result.append(paper_copy)

        # Sort by rating (rated first, then unrated)
        result.sort(key=lambda p: p.get("ai_priority_rating", 0), reverse=True)

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dict with training and rating statistics
        """
        ratings_by_star = {i: 0 for i in range(1, 6)}
        for rating in self._ratings.values():
            star = int(rating.rating)
            if 1 <= star <= 5:
                ratings_by_star[star] += 1

        return {
            "is_trained": self._is_trained,
            "training_samples": self._training_decisions_count,
            "last_trained_at": self._last_trained_at,
            "total_ratings": len(self._ratings),
            "ratings_by_star": ratings_by_star,
            "cached_embeddings": len(self._embedding_cache),
        }

    def clear_cache(self) -> None:
        """Clear embedding cache and ratings."""
        self._embedding_cache.clear()
        self._ratings.clear()
        self._is_trained = False
        self._classifier = None
        self._scaler = None
        logger.info("Cache and model cleared")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent state (ratings only, not model)."""
        return {
            "ratings": {
                doi: rating.to_dict()
                for doi, rating in self._ratings.items()
            },
            "statistics": self.get_statistics(),
        }

    def load_ratings(self, data: Dict[str, Dict]) -> None:
        """Load ratings from serialized data."""
        for doi, rating_data in data.items():
            try:
                self._ratings[doi] = ScreeningRating.from_dict(rating_data)
            except (KeyError, ValueError) as e:
                logger.error(f"Failed to load rating for {doi}: {e}")


# Convenience function for quick rating computation
async def compute_paper_ratings(
    pending: List[Dict],
    included: List[Dict],
    excluded: List[Dict],
    progress_callback: Optional[callable] = None
) -> List[ScreeningRating]:
    """
    Convenience function to compute ratings.

    Args:
        pending: Papers pending screening
        included: Papers included
        excluded: Papers excluded
        progress_callback: Optional callback for progress updates

    Returns:
        List of ScreeningRating objects
    """
    agent = ScreeningPriorityAgent()

    total = len(included) + len(excluded)
    if not agent.can_compute_ratings(total):
        if progress_callback:
            progress_callback(
                f"Need {agent.min_decisions - total} more decisions"
            )
        return []

    if progress_callback:
        progress_callback("Computing AI ratings...")

    ratings = await agent.compute_ratings(pending, included, excluded)

    if progress_callback:
        progress_callback(f"Computed {len(ratings)} ratings")

    return ratings
