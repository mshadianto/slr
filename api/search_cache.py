"""
Muezza AI - Search Cache System
================================
High-performance caching for search results with TTL, LRU eviction,
and query normalization for maximum cache hits.

Enhanced Features:
- Adaptive TTL based on cache hit rate
- Optional compression for large results
- Hybrid LRU/LFU eviction
- Memory-efficient storage
"""

import asyncio
import gzip
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import wraps
import threading

logger = logging.getLogger(__name__)

# Compression threshold (compress if larger than 10KB)
COMPRESSION_THRESHOLD = 10 * 1024


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    data: Any
    created_at: float
    ttl: int  # seconds
    hits: int = 0
    size_bytes: int = 0
    compressed: bool = False
    last_accessed: float = field(default_factory=time.time)
    frequency: int = 1  # For LFU scoring

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """Update hit count and access time."""
        self.hits += 1
        self.frequency += 1
        self.last_accessed = time.time()

    def get_eviction_score(self) -> float:
        """
        Calculate eviction score (lower = more likely to evict).
        Hybrid LRU/LFU: considers both recency and frequency.
        """
        age = time.time() - self.last_accessed
        # Score = frequency / log(age + 2), so frequently used recent items score higher
        import math
        return self.frequency / math.log(age + 2)

    def get_data(self) -> Any:
        """Get data, decompressing if needed."""
        if self.compressed and isinstance(self.data, bytes):
            try:
                return json.loads(gzip.decompress(self.data).decode('utf-8'))
            except Exception:
                return self.data
        return self.data


class SearchCache:
    """
    High-performance in-memory cache for search results.

    Features:
    - Hybrid LRU/LFU eviction policy
    - Adaptive TTL based on hit rate
    - Query normalization for better cache hits
    - Thread-safe operations
    - Memory limit enforcement (500MB default)
    - Optional compression for large entries
    - Cache statistics and monitoring
    """

    # Adaptive TTL settings
    MIN_TTL = 900       # 15 minutes minimum
    MAX_TTL = 21600     # 6 hours maximum
    TARGET_HIT_RATE = 0.7  # 70% target hit rate

    def __init__(
        self,
        max_entries: int = 2000,
        max_memory_mb: int = 500,  # Increased from 100MB
        default_ttl: int = 3600,  # 1 hour
        cleanup_interval: int = 300,  # 5 minutes
        enable_compression: bool = True,
        adaptive_ttl: bool = True
    ):
        """
        Initialize cache.

        Args:
            max_entries: Maximum number of cache entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds
            cleanup_interval: Interval for cleanup task
            enable_compression: Compress large entries
            adaptive_ttl: Automatically adjust TTL based on hit rate
        """
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.enable_compression = enable_compression
        self.adaptive_ttl = adaptive_ttl

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'compressions': 0,
            'bytes_saved': 0
        }

        # Adaptive TTL tracking
        self._recent_hits = 0
        self._recent_requests = 0
        self._current_adaptive_ttl = default_ttl

        # Start cleanup task
        self._cleanup_task = None
        self._running = True

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for consistent cache keys.

        - Lowercase
        - Remove extra whitespace
        - Sort boolean operators
        - Normalize field names
        """
        if not query:
            return ""

        # Lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Normalize common variations
        replacements = [
            ('title-abs-key', 'tak'),
            ('title-abs', 'ta'),
            ('pubyear', 'py'),
            ('language', 'lang'),
            ('  ', ' '),
        ]

        for old, new in replacements:
            normalized = normalized.replace(old, new)

        return normalized

    def _generate_key(self, query: str, source: str = "", params: Dict = None) -> str:
        """Generate cache key from query and parameters."""
        normalized = self._normalize_query(query)
        key_parts = [normalized, source]

        if params:
            # Sort params for consistency
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))

        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _estimate_size(self, data: Any) -> int:
        """Estimate memory size of data in bytes."""
        try:
            return len(json.dumps(data, default=str).encode())
        except:
            return 1000  # Default estimate

    def _get_adaptive_ttl(self) -> int:
        """Calculate adaptive TTL based on recent hit rate."""
        if not self.adaptive_ttl or self._recent_requests < 10:
            return self.default_ttl

        hit_rate = self._recent_hits / self._recent_requests

        if hit_rate >= self.TARGET_HIT_RATE:
            # High hit rate - can use longer TTL
            ttl_adjustment = (hit_rate - self.TARGET_HIT_RATE) / (1 - self.TARGET_HIT_RATE)
            self._current_adaptive_ttl = int(
                self.default_ttl + (self.MAX_TTL - self.default_ttl) * ttl_adjustment
            )
        else:
            # Low hit rate - use shorter TTL to refresh data more often
            ttl_adjustment = (self.TARGET_HIT_RATE - hit_rate) / self.TARGET_HIT_RATE
            self._current_adaptive_ttl = int(
                self.default_ttl - (self.default_ttl - self.MIN_TTL) * ttl_adjustment
            )

        # Clamp to bounds
        self._current_adaptive_ttl = max(
            self.MIN_TTL,
            min(self.MAX_TTL, self._current_adaptive_ttl)
        )

        # Reset recent counters periodically
        if self._recent_requests >= 100:
            self._recent_hits = int(self._recent_hits * 0.5)
            self._recent_requests = int(self._recent_requests * 0.5)

        return self._current_adaptive_ttl

    def _compress_data(self, data: Any) -> Tuple[Any, int, bool]:
        """
        Compress data if beneficial.

        Returns:
            Tuple of (data, size_bytes, is_compressed)
        """
        try:
            json_data = json.dumps(data, default=str).encode('utf-8')
            original_size = len(json_data)

            if not self.enable_compression or original_size < COMPRESSION_THRESHOLD:
                return data, original_size, False

            compressed = gzip.compress(json_data, compresslevel=6)
            compressed_size = len(compressed)

            # Only use compression if it saves at least 20%
            if compressed_size < original_size * 0.8:
                self._stats['compressions'] += 1
                self._stats['bytes_saved'] += original_size - compressed_size
                return compressed, compressed_size, True

            return data, original_size, False
        except Exception:
            return data, 1000, False

    def _evict_if_needed(self):
        """Evict entries using hybrid LRU/LFU strategy."""
        # Evict by entry count
        while len(self._cache) >= self.max_entries:
            # Find entry with lowest eviction score
            if len(self._cache) > 10:
                # For larger caches, use score-based eviction
                worst_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].get_eviction_score()
                )
                del self._cache[worst_key]
            else:
                # For small caches, just use FIFO
                self._cache.popitem(last=False)
            self._stats['evictions'] += 1

        # Evict by memory
        total_size = sum(e.size_bytes for e in self._cache.values())
        while total_size > self.max_memory_bytes and self._cache:
            # Use score-based eviction for memory pressure
            worst_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].get_eviction_score()
            )
            entry = self._cache.pop(worst_key)
            total_size -= entry.size_bytes
            self._stats['evictions'] += 1

    def get(self, query: str, source: str = "", params: Dict = None) -> Optional[Any]:
        """
        Get cached result.

        Args:
            query: Search query
            source: Source identifier (e.g., 'scopus', 'doaj')
            params: Additional parameters

        Returns:
            Cached data if found and not expired, None otherwise
        """
        key = self._generate_key(query, source, params)

        with self._lock:
            # Track for adaptive TTL
            self._recent_requests += 1

            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats['hits'] += 1
            self._recent_hits += 1

            logger.debug(f"Cache HIT for query: {query[:50]}...")
            return entry.get_data()

    def set(
        self,
        query: str,
        data: Any,
        source: str = "",
        params: Dict = None,
        ttl: int = None
    ):
        """
        Store result in cache.

        Args:
            query: Search query
            data: Data to cache
            source: Source identifier
            params: Additional parameters
            ttl: Time-to-live in seconds (uses adaptive TTL if not specified)
        """
        if data is None:
            return

        key = self._generate_key(query, source, params)

        # Use adaptive TTL if not explicitly specified
        if ttl is None:
            ttl = self._get_adaptive_ttl()

        # Compress data if beneficial
        stored_data, size, compressed = self._compress_data(data)

        with self._lock:
            self._evict_if_needed()

            self._cache[key] = CacheEntry(
                data=stored_data,
                created_at=time.time(),
                ttl=ttl,
                size_bytes=size,
                compressed=compressed
            )

            # Move to end
            self._cache.move_to_end(key)

        compression_note = " (compressed)" if compressed else ""
        logger.debug(f"Cache SET for query: {query[:50]}... (TTL: {ttl}s{compression_note})")

    def invalidate(self, query: str = None, source: str = None):
        """
        Invalidate cache entries.

        Args:
            query: Specific query to invalidate (None = all)
            source: Specific source to invalidate (None = all)
        """
        with self._lock:
            if query is None and source is None:
                self._cache.clear()
                logger.info("Cache cleared completely")
                return

            if query:
                key = self._generate_key(query, source or "")
                if key in self._cache:
                    del self._cache[key]

    def cleanup(self):
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

    def get_stats(self) -> Dict:
        """Get cache statistics including compression and adaptive TTL info."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            total_size = sum(e.size_bytes for e in self._cache.values())
            compressed_entries = sum(1 for e in self._cache.values() if e.compressed)

            return {
                'entries': len(self._cache),
                'max_entries': self.max_entries,
                'memory_used_mb': round(total_size / (1024 * 1024), 2),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                # Compression stats
                'compressed_entries': compressed_entries,
                'total_compressions': self._stats['compressions'],
                'bytes_saved_mb': round(self._stats['bytes_saved'] / (1024 * 1024), 2),
                # Adaptive TTL stats
                'adaptive_ttl_enabled': self.adaptive_ttl,
                'current_adaptive_ttl': self._current_adaptive_ttl,
                'compression_enabled': self.enable_compression
            }


# Global cache instance
_search_cache = SearchCache()


def get_search_cache() -> SearchCache:
    """Get global search cache instance."""
    return _search_cache


def cached_search(source: str = "", ttl: int = None):
    """
    Decorator for caching async search functions.

    Usage:
        @cached_search(source="scopus", ttl=3600)
        async def search_scopus(query: str, **kwargs):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(query: str, *args, **kwargs):
            cache = get_search_cache()

            # Try cache first
            cached = cache.get(query, source, kwargs)
            if cached is not None:
                logger.info(f"[CACHE HIT] {source}: {query[:50]}...")
                return cached

            # Execute search
            logger.info(f"[CACHE MISS] {source}: {query[:50]}...")
            result = await func(query, *args, **kwargs)

            # Cache result
            if result:
                cache.set(query, result, source, kwargs, ttl)

            return result

        return wrapper
    return decorator


class ParallelSearcher:
    """
    Execute searches across multiple sources in parallel.

    Features:
    - Concurrent execution
    - Result merging and deduplication
    - Timeout handling
    - Source prioritization
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_concurrent: int = 5
    ):
        """
        Initialize parallel searcher.

        Args:
            timeout: Timeout per source in seconds
            max_concurrent: Maximum concurrent searches
        """
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _search_with_timeout(
        self,
        search_func: Callable,
        query: str,
        source_name: str,
        **kwargs
    ) -> Dict:
        """Execute single search with timeout."""
        async with self.semaphore:
            try:
                result = await asyncio.wait_for(
                    search_func(query, **kwargs),
                    timeout=self.timeout
                )
                return {
                    'source': source_name,
                    'results': result if isinstance(result, list) else result.get('results', []),
                    'success': True,
                    'error': None
                }
            except asyncio.TimeoutError:
                logger.warning(f"Search timeout for {source_name}")
                return {
                    'source': source_name,
                    'results': [],
                    'success': False,
                    'error': 'timeout'
                }
            except Exception as e:
                logger.error(f"Search error for {source_name}: {e}")
                return {
                    'source': source_name,
                    'results': [],
                    'success': False,
                    'error': str(e)
                }

    async def search_all(
        self,
        query: str,
        sources: List[Dict],
        merge_results: bool = True
    ) -> Dict:
        """
        Search all sources in parallel.

        Args:
            query: Search query
            sources: List of {'name': str, 'func': Callable, 'kwargs': Dict}
            merge_results: Whether to merge and deduplicate results

        Returns:
            Dict with results per source and merged results
        """
        tasks = [
            self._search_with_timeout(
                src['func'],
                query,
                src['name'],
                **src.get('kwargs', {})
            )
            for src in sources
        ]

        results = await asyncio.gather(*tasks)

        output = {
            'by_source': {r['source']: r for r in results},
            'successful_sources': [r['source'] for r in results if r['success']],
            'failed_sources': [r['source'] for r in results if not r['success']],
        }

        if merge_results:
            all_papers = []
            seen_titles = set()
            seen_dois = set()

            for r in results:
                for paper in r['results']:
                    # Deduplicate by DOI
                    doi = paper.get('doi', '').lower().strip()
                    if doi and doi in seen_dois:
                        continue

                    # Deduplicate by title similarity
                    title = paper.get('title', '').lower().strip()
                    if title in seen_titles:
                        continue

                    if doi:
                        seen_dois.add(doi)
                    seen_titles.add(title)

                    # Add source info
                    paper['_source'] = r['source']
                    all_papers.append(paper)

            output['merged'] = all_papers
            output['total_unique'] = len(all_papers)

        return output


class SearchOptimizer:
    """
    Optimizes search queries for better performance and results.

    Features:
    - Query expansion with synonyms
    - Query simplification for broad searches
    - Adaptive query refinement
    """

    # Common synonyms for query expansion
    SYNONYMS = {
        'machine learning': ['ML', 'artificial intelligence', 'AI', 'deep learning'],
        'deep learning': ['neural network', 'CNN', 'RNN', 'transformer'],
        'cancer': ['tumor', 'carcinoma', 'malignancy', 'oncology'],
        'diagnosis': ['detection', 'screening', 'identification'],
        'treatment': ['therapy', 'intervention', 'management'],
        'effectiveness': ['efficacy', 'performance', 'accuracy'],
        'medical imaging': ['radiology', 'CT scan', 'MRI', 'X-ray'],
    }

    @classmethod
    def expand_query(cls, query: str, max_expansions: int = 2) -> List[str]:
        """
        Expand query with synonyms.

        Args:
            query: Original query
            max_expansions: Maximum synonym expansions per term

        Returns:
            List of expanded queries
        """
        queries = [query]
        query_lower = query.lower()

        for term, synonyms in cls.SYNONYMS.items():
            if term in query_lower:
                for syn in synonyms[:max_expansions]:
                    expanded = query_lower.replace(term, syn)
                    if expanded not in queries:
                        queries.append(expanded)

        return queries[:5]  # Limit total queries

    @classmethod
    def simplify_query(cls, query: str) -> str:
        """
        Simplify complex query for broader search.

        Removes restrictive filters when results are too few.
        """
        simplified = query

        # Remove language filter
        simplified = simplified.replace("AND LANGUAGE(english)", "")
        simplified = simplified.replace("AND LANGUAGE(English)", "")

        # Remove document type filter
        import re
        simplified = re.sub(r'\s*AND\s*DOCTYPE\([^)]+\)', '', simplified)

        # Remove date filter (make broader)
        simplified = re.sub(r'\s*AND\s*PUBYEAR\s*[<>]\s*\d+', '', simplified)

        return simplified.strip()

    @classmethod
    def create_fallback_queries(cls, original_query: str) -> List[str]:
        """
        Create fallback queries if original returns no results.

        Returns queries from most specific to least specific.
        """
        queries = [original_query]

        # Remove filters progressively
        q1 = cls.simplify_query(original_query)
        if q1 != original_query:
            queries.append(q1)

        # Extract just keywords
        import re
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', original_query.lower())
        stop_words = {'title', 'abstract', 'language', 'english', 'pubyear', 'doctype'}
        keywords = [k for k in keywords if k not in stop_words][:4]

        if keywords:
            simple_query = ' AND '.join(keywords)
            queries.append(f"TITLE-ABS-KEY({simple_query})")

        return queries


# Convenience function for optimized search
async def optimized_search(
    query: str,
    search_func: Callable,
    source: str = "default",
    use_cache: bool = True,
    use_fallback: bool = True,
    cache_ttl: int = 3600
) -> List[Dict]:
    """
    Perform optimized search with caching and fallbacks.

    Args:
        query: Search query
        search_func: Async search function
        source: Source identifier for caching
        use_cache: Whether to use cache
        use_fallback: Whether to try fallback queries
        cache_ttl: Cache TTL in seconds

    Returns:
        List of search results
    """
    cache = get_search_cache()

    # Try cache first
    if use_cache:
        cached = cache.get(query, source)
        if cached:
            logger.info(f"[OPTIMIZED] Cache hit for {source}")
            return cached

    # Try original query
    results = await search_func(query)

    # If no results and fallback enabled, try simplified queries
    if not results and use_fallback:
        fallback_queries = SearchOptimizer.create_fallback_queries(query)

        for fb_query in fallback_queries[1:]:  # Skip original
            logger.info(f"[OPTIMIZED] Trying fallback: {fb_query[:50]}...")
            results = await search_func(fb_query)
            if results:
                break

    # Cache results
    if use_cache and results:
        cache.set(query, results, source, ttl=cache_ttl)

    return results or []
