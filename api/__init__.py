"""
BiblioAgent AI - API Module
===========================
API clients for external services used in SLR automation.
"""

from .scopus import ScopusClient
from .unpaywall import UnpaywallClient
from .core_api import COREClient
from .arxiv_api import ArxivClient
from .semantic_scholar import SemanticScholarClient
from .biblio_hunter import BiblioHunter, PaperResult, hunt_paper, batch_hunt_papers

__all__ = [
    "ScopusClient",
    "UnpaywallClient",
    "COREClient",
    "ArxivClient",
    "SemanticScholarClient",
    "BiblioHunter",
    "PaperResult",
    "hunt_paper",
    "batch_hunt_papers",
]
