"""
Muezza AI - API Module
======================
API clients for external services used in SLR automation.
"""

from .scopus import ScopusClient
from .unpaywall import UnpaywallClient
from .core_api import COREClient
from .arxiv_api import ArxivClient
from .semantic_scholar import SemanticScholarClient
from .doaj import DOAJClient, search_doaj, get_doaj_pdf
from .google_scholar import GoogleScholarClient, search_google_scholar
from .biblio_hunter import BiblioHunter, PaperResult, hunt_paper, batch_hunt_papers

__all__ = [
    "ScopusClient",
    "UnpaywallClient",
    "COREClient",
    "ArxivClient",
    "SemanticScholarClient",
    "DOAJClient",
    "search_doaj",
    "get_doaj_pdf",
    "GoogleScholarClient",
    "search_google_scholar",
    "BiblioHunter",
    "PaperResult",
    "hunt_paper",
    "batch_hunt_papers",
]
