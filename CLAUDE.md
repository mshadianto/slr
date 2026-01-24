# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Muezza AI is a Streamlit-based systematic literature review (SLR) automation system for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) with RAG to automate search, screening, full-text acquisition, quality assessment, and **automated academic writing in formal Indonesian**.

**Key Innovation**: BiblioHunter - intelligent paper retrieval with waterfall PDF acquisition and Virtual Full-Text synthesis for paywalled papers.

## Running the Application

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

**Docker**:
```bash
docker build -t muezza-ai .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... muezza-ai
```

## Required Environment Variables

Create `.env` file with:
```env
ANTHROPIC_API_KEY=sk-ant-...          # Required for screening/quality/narrative
SCOPUS_API_KEY=your_scopus_key        # Required for Scopus search
SEMANTIC_SCHOLAR_API_KEY=your_s2_key  # Recommended (higher rate limits)
UNPAYWALL_EMAIL=your@email.com        # Recommended for PDF waterfall
CORE_API_KEY=your_core_key            # Optional
OPENALEX_EMAIL=your@email.com         # Optional (polite pool, higher limits)
NCBI_API_KEY=your_ncbi_key            # Optional (10 req/sec vs 3 req/sec)
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

The workflow is a linear state machine defined in `agents/orchestrator.py`:

```
search_node → screening_node → acquisition_node → quality_node → END
                                                        ↓
                    narrative_generator → narrative_orchestrator → docx_export
```

**State Management**: All agents share `SLRState` (TypedDict in `agents/state.py`) which tracks papers through each phase, PRISMA statistics, and agent status via `AgentStatus` enum (PENDING/ACTIVE/COMPLETED/ERROR/PAUSED).

**Core SLR Agents** (`agents/`):
- `SearchAgent` - PICO parsing, Boolean query generation, Scopus search, RapidFuzz deduplication
- `ScreeningAgent` - 4-phase screening (rule-based → semantic → Claude reasoning → human-in-loop)
- `ScroungerAgent` - BiblioHunter integration for full-text acquisition
- `QualityAgent` - JBI Critical Appraisal framework assessment
- `BibliometricAgent` - Publication trends, journal distribution, citation analysis charts
- `CitationNetworkAgent` - **NEW** Connected Papers-style network visualization, PageRank centrality, cluster detection
- `CitationContextAnalyzer` - **NEW** Scite-style citation classification (Supporting/Contrasting/Mentioning)

**Report Generation Agents** (`agents/`):
- `NarrativeGenerator` - BAB IV (Results chapter) in formal Indonesian
- `NarrativeOrchestrator` - Full 5-chapter report (BAB I-V)
- `CitationAutoStitcher` - Auto-match author names with bibliography (APA7/Vancouver styles)
- `LogicContinuityAgent` - Ensure "benang merah" coherence across chapters
- `ForensicAuditAgent` - Verify every citation against source database
- `DocxGenerator` - Professional Word export with title page

### BiblioHunter (`api/biblio_hunter.py`)

Core paper retrieval engine with waterfall PDF strategy:

```python
from api.biblio_hunter import BiblioHunter, hunt_paper

# Quick usage
paper = hunt_paper("10.1038/nature12373")

# Multi-identifier support: DOI, ArXiv ID, PMID, title search
hunter = BiblioHunter(s2_api_key="...", unpaywall_email="...")
result = hunter.hunt("10.1038/nature12373")
```

**Waterfall Order** (9 sources):
1. Semantic Scholar OA
2. Unpaywall
3. **OpenAlex** (250M+ works, free)
4. **Crossref** (publisher links)
5. DOAJ
6. **PubMed Central** (biomedical full-text)
7. CORE
8. ArXiv
9. Google Scholar
10. Virtual Full-Text (fallback)

**Virtual Full-Text** (when no PDF available): Synthesizes content from TL;DR, abstract, citation contexts (up to 15 snippets), related papers, and key references.

### External API Clients (`api/`)

Each client handles its own rate limiting and error recovery:
- `scopus.py` - Elsevier Scopus Search API (5000 req/week, 9/sec)
- `semantic_scholar.py` - Paper metadata and citations (100 req/5min without key)
- `unpaywall.py` - Open access PDF discovery (100K req/day)
- `openalex.py` - **NEW** OpenAlex API (250M+ works, 100K req/day, free)
- `crossref.py` - **NEW** Crossref API (140M+ works, 50 req/sec)
- `pubmed.py` - **NEW** PubMed/NCBI E-utilities (35M+ biomedical, 3-10 req/sec)
- `core_api.py` - CORE aggregator (10 req/sec)
- `arxiv_api.py` - Preprint server (1 req/3sec)
- `doaj.py` - Directory of Open Access Journals
- `google_scholar.py` - Google Scholar fallback
- `pdf_processor.py` - **NEW** Multi-backend PDF extraction (PyMuPDF, pdfplumber)
- `query_translator.py` - Indonesian → English query translation with academic term mappings
- `search_cache.py` - LRU cache with TTL, query normalization, thread-safe operations

### RAG Component (`rag/chromadb_store.py`)

ChromaDB vector store using `all-MiniLM-L6-v2` embeddings for semantic search during screening and deduplication.

## Testing Individual Components

```bash
# Test BiblioHunter paper retrieval
python -c "from api.biblio_hunter import hunt_paper; print(hunt_paper('10.1038/nature12373'))"

# Test new API clients
python -c "from api.openalex import OpenAlexClient; print(OpenAlexClient().search('machine learning'))"
python -c "from api.crossref import CrossrefClient; print(CrossrefClient().get_work_by_doi('10.1038/nature12373'))"
python -c "from api.pubmed import PubMedClient; print(PubMedClient().search('COVID-19 treatment', limit=5))"

# Test citation network
python -c "
from agents.citation_network_agent import CitationNetworkAgent
agent = CitationNetworkAgent(max_depth=1, max_papers=20)
network = agent.build_network([{'doi': '10.1038/nature12373', 'title': 'Test', 'paper_id': 'test'}])
print(f'Nodes: {len(network.nodes)}, Edges: {len(network.edges)}')
"

# Test citation context analyzer
python -c "
from agents.citation_context_analyzer import CitationContextAnalyzer
analyzer = CitationContextAnalyzer()
result = analyzer.classify_context('Our results support the findings of Smith et al.')
print(result)
"

# Test async SLR acquisition
python -c "
import asyncio
from agents.scrounger_agent import acquire_papers
papers = [{'doi': '10.1038/nature12373'}]
results = asyncio.run(acquire_papers(papers))
print(results)
"
```

**Import patterns for agents**:
```python
# Individual agent imports
from agents.narrative_orchestrator import NarrativeOrchestrator
from agents.citation_stitcher import CitationAutoStitcher
from agents.forensic_audit_agent import ForensicAuditAgent
from agents.docx_generator import DocxGenerator

# NEW: Citation analysis agents
from agents.citation_network_agent import CitationNetworkAgent, build_citation_network
from agents.citation_context_analyzer import CitationContextAnalyzer, analyze_citation_contexts

# NEW: API clients
from api.openalex import OpenAlexClient, search_openalex
from api.crossref import CrossrefClient, search_crossref
from api.pubmed import PubMedClient, search_pubmed
from api.pdf_processor import PDFProcessor, process_pdf

# State and orchestration
from agents.state import SLRState, Paper, PRISMAStats, AgentStatus
from agents.orchestrator import SLROrchestrator
```

## Key Patterns

**Async-first design**: All agents use async/await. Use `asyncio.run()` when testing from CLI.

**Progress callbacks**: Long operations accept `progress_callback` for UI updates:
```python
async def acquire_papers(papers, progress_callback=None):
    if progress_callback:
        progress_callback(f"Processing {len(papers)} papers...")
```

**Pydantic settings**: Configuration in `config.py` uses `BaseSettings` with automatic `.env` loading. Access via `from config import settings`.

**Caching**: BiblioHunter uses 24-hour TTL in-memory cache. SearchCache provides LRU eviction with configurable TTL (default 1 hour).

**Data classes**: `Paper` dataclass in `agents/state.py` carries all paper metadata through the pipeline. `PaperResult` in `api/biblio_hunter.py` for retrieval results.

**Orchestrator usage**:
```python
orchestrator = SLROrchestrator(
    progress_callback=lambda phase, percent, msg: print(f"{phase}: {percent}% - {msg}"),
    enable_checkpointing=False  # Disable due to numpy serialization issues
)
result = await orchestrator.run(initial_state)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8501 in use | Use `--server.port 8502` |
| Scopus 401 error | Check API key, use STANDARD view |
| Rate limiting (429) | Add API keys; BiblioHunter handles backoff automatically |
| numpy serialization | Use `enable_checkpointing=False` in orchestrator |

## Quality Assessment (JBI Framework)

Quality scores categorized as: HIGH (≥80), MODERATE (60-79), LOW (40-59), CRITICAL (<40)

Weighted criteria: Study Design (25%), Sample Size (20%), Control Group (15%), Randomization (15%), Blinding (10%), Statistical Methods (10%), Confidence Intervals (5%)

## Railway Deployment

Live URL: https://muezza-ai.up.railway.app/

**Deployment files:** `Procfile`, `railway.toml`, `packages.txt`

**Required Railway Variables:** `ANTHROPIC_API_KEY`, `SCOPUS_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` (optional), `UNPAYWALL_EMAIL` (optional)

## Related AI Research Tools

Reference: [Awesome AI Research Tools](https://github.com/Harrypatria/Awesome-AI-Research-Tools-)

### Already Integrated
- **Semantic Scholar** (semanticscholar.org) - 227M+ papers, used in BiblioHunter waterfall
- **Unpaywall** (unpaywall.org) - OA PDF discovery, 100K req/day
- **OpenAlex** (openalex.org) - **NEW** 250M+ works, free API, no key required
- **Crossref** (crossref.org) - **NEW** 140M+ works, DOI metadata, 50 req/sec
- **PubMed/NCBI** (pubmed.gov) - **NEW** 35M+ biomedical citations, PMC full-text
- **CORE** (core.ac.uk) - Academic aggregator, 10 req/sec
- **ArXiv** (arxiv.org) - Preprint server, 1 req/3sec
- **Scopus** (scopus.com) - Primary search database
- **DOAJ** (doaj.org) - Directory of Open Access Journals

### Similar SLR Tools (Competitive Landscape)
| Tool | Focus | Key Difference from Muezza AI |
|------|-------|------------------------------|
| **ASReview** (asreview.nl) | Active learning screening | Open-source, no full-text acquisition |
| **Rayyan** (rayyan.ai) | Collaborative screening | No auto-narrative generation |
| **Elicit** (elicit.com) | Literature review automation | 125M papers, no Indonesian output |
| **Covidence** | PRISMA compliance | Premium, no LLM integration |

### Potential Integrations (PDF Processing)
Open-source tools that could enhance BiblioHunter's PDF extraction:
- **MinerU** - Multimodal PDF parsing to Markdown/JSON (1.2B params)
- **Nougat** (Meta AI) - Scientific PDF to Markdown with formula support
- **Marker** - High-accuracy PDF to Markdown/JSON/HTML
- **Docling** (IBM) - Multi-format to structured data

### Autonomous Research Agents (Emerging)
For reference on future AI-driven research systems:
- **The AI Scientist** - Full research cycle: hypothesis → experiment → paper
- **AI-Researcher** (HKUDS) - Pipeline from review to publication
- **Agent Laboratory** - Multi-agent with cumulative discovery
