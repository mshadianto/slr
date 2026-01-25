"""
Muezza AI - Shared Connection Pool Manager
==========================================
Centralized aiohttp connection pool for all API clients.

Benefits:
- TCP connection reuse across requests
- DNS caching
- Connection limits per host
- Automatic cleanup

Usage:
    from api.connection_pool import get_session, close_pool

    async def my_api_call():
        session = await get_session()
        async with session.get(url) as response:
            return await response.json()
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import aiohttp

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    Singleton connection pool manager for all HTTP clients.

    Features:
    - Shared TCPConnector across all API clients
    - Configurable limits per host
    - DNS caching for faster lookups
    - Automatic session cleanup
    """

    _instance: Optional["ConnectionPoolManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    # Connection pool settings
    DEFAULT_POOL_SIZE = 100          # Total connections
    DEFAULT_PER_HOST_LIMIT = 10      # Connections per host
    DEFAULT_DNS_TTL = 300            # DNS cache 5 minutes
    DEFAULT_TIMEOUT = 30             # Request timeout seconds
    DEFAULT_KEEPALIVE = 30           # Keep-alive timeout

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._is_closed = False

        # Metrics
        self._request_count = 0
        self._error_count = 0

    @classmethod
    async def get_instance(cls) -> "ConnectionPoolManager":
        """Get or create the singleton instance."""
        async with cls._lock:
            if cls._instance is None or cls._instance._is_closed:
                cls._instance = cls()
                await cls._instance._initialize()
            return cls._instance

    async def _initialize(self) -> None:
        """Initialize the connection pool."""
        if self._session is not None:
            return

        # Create optimized TCP connector
        self._connector = aiohttp.TCPConnector(
            limit=self.DEFAULT_POOL_SIZE,
            limit_per_host=self.DEFAULT_PER_HOST_LIMIT,
            ttl_dns_cache=self.DEFAULT_DNS_TTL,
            use_dns_cache=True,
            keepalive_timeout=self.DEFAULT_KEEPALIVE,
            enable_cleanup_closed=True,
            force_close=False,  # Allow connection reuse
        )

        # Create session with timeout settings
        timeout = aiohttp.ClientTimeout(
            total=self.DEFAULT_TIMEOUT,
            connect=10,
            sock_read=self.DEFAULT_TIMEOUT,
        )

        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={
                "User-Agent": "MuezzaAI/2.2.0 (Systematic Literature Review; mailto:research@muezza.ai)",
            },
        )

        self._is_closed = False
        logger.info(
            f"Connection pool initialized: "
            f"pool_size={self.DEFAULT_POOL_SIZE}, "
            f"per_host={self.DEFAULT_PER_HOST_LIMIT}"
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the shared session."""
        if self._session is None or self._is_closed:
            raise RuntimeError("Connection pool not initialized. Use get_session() instead.")
        return self._session

    async def close(self) -> None:
        """Close the connection pool."""
        if self._session and not self._is_closed:
            await self._session.close()
            self._is_closed = True
            logger.info(
                f"Connection pool closed. "
                f"Total requests: {self._request_count}, "
                f"Errors: {self._error_count}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "is_active": not self._is_closed,
            "request_count": self._request_count,
            "error_count": self._error_count,
        }

        if self._connector:
            stats.update({
                "pool_size": self.DEFAULT_POOL_SIZE,
                "per_host_limit": self.DEFAULT_PER_HOST_LIMIT,
            })

        return stats

    def increment_request(self) -> None:
        """Track request count."""
        self._request_count += 1

    def increment_error(self) -> None:
        """Track error count."""
        self._error_count += 1


# Global convenience functions

async def get_session() -> aiohttp.ClientSession:
    """
    Get the shared aiohttp session.

    Usage:
        session = await get_session()
        async with session.get(url) as resp:
            data = await resp.json()
    """
    manager = await ConnectionPoolManager.get_instance()
    return manager.session


async def close_pool() -> None:
    """Close the connection pool (call on app shutdown)."""
    if ConnectionPoolManager._instance:
        await ConnectionPoolManager._instance.close()


def get_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics."""
    if ConnectionPoolManager._instance:
        return ConnectionPoolManager._instance.get_stats()
    return {"is_active": False}


@asynccontextmanager
async def managed_session():
    """
    Context manager for managed session access.

    Usage:
        async with managed_session() as session:
            async with session.get(url) as resp:
                data = await resp.json()
    """
    session = await get_session()
    try:
        yield session
    finally:
        # Session is shared, don't close it
        pass


class RateLimitedSession:
    """
    Rate-limited wrapper around the shared session.

    Usage:
        rate_limiter = RateLimitedSession(requests_per_second=10)
        async with rate_limiter.get(url) as response:
            data = await response.json()
    """

    def __init__(
        self,
        requests_per_second: float = 10,
        burst_size: int = 5
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self._semaphore = asyncio.Semaphore(burst_size)
        self._last_request_time = 0.0
        self._min_interval = 1.0 / requests_per_second

    async def _wait_for_slot(self) -> None:
        """Wait for rate limit slot."""
        async with self._semaphore:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time

            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

            self._last_request_time = asyncio.get_event_loop().time()

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make a rate-limited request."""
        await self._wait_for_slot()
        session = await get_session()
        return await session.request(method, url, **kwargs)

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Rate-limited GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Rate-limited POST request."""
        return await self.request("POST", url, **kwargs)


# Pre-configured rate limiters for common APIs
class APIRateLimiters:
    """Pre-configured rate limiters for known APIs."""

    # Scopus: 9 requests/second
    SCOPUS = RateLimitedSession(requests_per_second=9, burst_size=3)

    # Semantic Scholar: 100 requests/5 minutes = 0.33/sec
    SEMANTIC_SCHOLAR = RateLimitedSession(requests_per_second=0.33, burst_size=10)

    # Unpaywall: 100K/day = ~1.15/sec
    UNPAYWALL = RateLimitedSession(requests_per_second=1.0, burst_size=5)

    # OpenAlex: 100K/day = ~1.15/sec
    OPENALEX = RateLimitedSession(requests_per_second=1.0, burst_size=10)

    # Crossref: 50/sec polite
    CROSSREF = RateLimitedSession(requests_per_second=50, burst_size=10)

    # PubMed: 3/sec without key, 10/sec with key
    PUBMED = RateLimitedSession(requests_per_second=3, burst_size=3)

    # CORE: 10/sec
    CORE = RateLimitedSession(requests_per_second=10, burst_size=5)


# Parallel request helper
async def parallel_requests(
    urls: list,
    method: str = "GET",
    max_concurrent: int = 10,
    **kwargs
) -> list:
    """
    Make parallel HTTP requests with concurrency limit.

    Args:
        urls: List of URLs to request
        method: HTTP method
        max_concurrent: Maximum concurrent requests
        **kwargs: Additional request arguments

    Returns:
        List of responses (or None for failed requests)
    """
    session = await get_session()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str):
        async with semaphore:
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Request failed: {url} -> {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Request error: {url} -> {e}")
                return None

    return await asyncio.gather(*[fetch_one(url) for url in urls])


async def first_successful_request(
    urls: list,
    method: str = "GET",
    **kwargs
) -> tuple:
    """
    Make parallel requests and return the first successful response.

    Args:
        urls: List of URLs to try
        method: HTTP method
        **kwargs: Additional request arguments

    Returns:
        Tuple of (url, response_data) or (None, None) if all failed
    """
    session = await get_session()

    async def fetch_one(url: str):
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    return (url, data)
        except Exception:
            pass
        return None

    # Create tasks for all URLs
    tasks = [asyncio.create_task(fetch_one(url)) for url in urls]

    # Wait for first successful result
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Get result from completed task
    result = None
    for task in done:
        result = task.result()
        if result is not None:
            break

    # Cancel remaining tasks
    for task in pending:
        task.cancel()

    return result if result else (None, None)
