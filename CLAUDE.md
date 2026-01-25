# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Muezza AI is a Streamlit-based systematic literature review (SLR) automation system for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) with RAG to automate search, screening, full-text acquisition, quality assessment, and automated academic writing in formal Indonesian.

**Key Innovation**: BiblioHunter - intelligent paper retrieval with waterfall PDF acquisition and Virtual Full-Text synthesis for paywalled papers.

## Running the Application

**Requirements**: Python 3.10+

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

Create `.env` file (see `.env.example`):
```env
ANTHROPIC_API_KEY=sk-ant-...          # Required for screening/quality/narrative
SCOPUS_API_KEY=your_scopus_key        # Required for Scopus search + ScienceDirect
ELSEVIER_INST_TOKEN=your_inst_token   # Optional (off-campus ScienceDirect)
SEMANTIC_SCHOLAR_API_KEY=your_s2_key  # Recommended (higher rate limits)
UNPAYWALL_EMAIL=your@email.com        # Recommended for PDF waterfall
CORE_API_KEY=your_core_key            # Optional
OPENALEX_EMAIL=your@email.com         # Optional (polite pool)
NCBI_API_KEY=your_ncbi_key            # Optional (10 req/sec vs 3 req/sec)
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

Linear state machine defined in `agents/orchestrator.py`:

```
search_node → screening_node → acquisition_node → quality_node → END
                                                        ↓
                    narrative_generator → narrative_orchestrator → docx_export
```

**State Management**: All agents share `SLRState` (TypedDict in `agents/state.py`) which tracks papers through each phase, PRISMA statistics, and agent status via `AgentStatus` enum (PENDING/ACTIVE/COMPLETED/ERROR/PAUSED).

### Core Components

**SLR Agents** (`agents/`):
- `SearchAgent` - PICO parsing, Boolean query generation, Scopus search, RapidFuzz deduplication
- `ScreeningAgent` - 4-phase screening (rule-based → semantic → Claude reasoning → human-in-loop), includes AI Priority Screening (Rayyan-style 1-5 star ratings)
- `ScroungerAgent` - BiblioHunter integration for full-text acquisition
- `QualityAgent` - JBI Critical Appraisal framework assessment
- `CitationNetworkAgent` - Network visualization, PageRank centrality, cluster detection
- `CitationContextAnalyzer` - Scite-style citation classification (Supporting/Contrasting/Mentioning)

**Report Generation** (`agents/`):
- `NarrativeGenerator` - BAB IV (Results chapter) in formal Indonesian
- `NarrativeOrchestrator` - Full 5-chapter report (BAB I-V)
- `CitationAutoStitcher` - Auto-match author names with bibliography (APA7/Vancouver)
- `LogicContinuityAgent` - Ensure "benang merah" coherence across chapters
- `ForensicAuditAgent` - Verify every citation against source database
- `DocxGenerator` - Professional Word export with title page

### BiblioHunter (`api/biblio_hunter.py`)

Core paper retrieval engine with waterfall PDF strategy:

```python
from api.biblio_hunter import BiblioHunter, hunt_paper
paper = hunt_paper("10.1038/nature12373")  # DOI, ArXiv ID, PMID, or title
```

**Waterfall Order** (11 sources + fallback):
ScienceDirect → Semantic Scholar OA → Unpaywall → OpenAlex → Crossref → DOAJ → PubMed Central → CORE → ArXiv → Google Scholar → Virtual Full-Text

**Virtual Full-Text**: Synthesizes content from TL;DR, abstract, citation contexts (up to 15 snippets), related papers for paywalled papers.

### External API Clients (`api/`)

Each client handles its own rate limiting and error recovery:
- `scopus.py` - Elsevier Scopus (5000 req/week, 9/sec)
- `sciencedirect.py` - Elsevier ScienceDirect full-text (requires institutional access)
- `semantic_scholar.py` - Paper metadata/citations (100 req/5min without key)
- `unpaywall.py` - Open access PDF discovery (100K req/day)
- `openalex.py` - OpenAlex (250M+ works, 100K req/day, free)
- `crossref.py` - Crossref (140M+ works, 50 req/sec)
- `pubmed.py` - PubMed/NCBI E-utilities (35M+ biomedical, 3-10 req/sec)
- `core_api.py`, `arxiv_api.py`, `doaj.py`, `google_scholar.py` - Additional sources
- `query_translator.py` - Indonesian → English query translation with academic term mappings
- `search_cache.py` - LRU cache with TTL, query normalization, thread-safe

### RAG Component (`rag/chromadb_store.py`)

ChromaDB vector store using `all-MiniLM-L6-v2` embeddings for semantic search during screening and deduplication.

## Testing Individual Components

No formal test suite exists. Use these CLI patterns to verify components:

```bash
# Test BiblioHunter
python -c "from api.biblio_hunter import hunt_paper; print(hunt_paper('10.1038/nature12373'))"

# Test API clients
python -c "from api.openalex import OpenAlexClient; print(OpenAlexClient().search('machine learning'))"
python -c "from api.crossref import CrossrefClient; print(CrossrefClient().get_work_by_doi('10.1038/nature12373'))"
python -c "from api.pubmed import PubMedClient; print(PubMedClient().search('COVID-19 treatment', limit=5))"

# Test async acquisition
python -c "import asyncio; from agents.scrounger_agent import acquire_papers; print(asyncio.run(acquire_papers([{'doi': '10.1038/nature12373'}])))"

# Test orchestrator
python -c "
import asyncio
from agents.orchestrator import SLROrchestrator
from agents.state import create_initial_state

async def test():
    orch = SLROrchestrator(enable_checkpointing=False)
    state = create_initial_state('test question', ['criteria'], [])
    return await orch.run(state)

asyncio.run(test())
"
```

## Key Patterns

**Async-first**: All agents use async/await. Use `asyncio.run()` for CLI testing.

**Progress callbacks**: Long operations accept `progress_callback` for UI updates:
```python
async def acquire_papers(papers, progress_callback=None):
    if progress_callback:
        progress_callback(f"Processing {len(papers)} papers...")
```

**Pydantic settings**: Configuration in `config.py` uses `BaseSettings` with automatic `.env` loading. Access via `from config import settings`.

**Caching**: BiblioHunter uses 24-hour TTL in-memory cache. SearchCache provides LRU eviction with configurable TTL (default 1 hour).

**Data classes**: `Paper` dataclass in `agents/state.py` carries all paper metadata through the pipeline (including `ai_priority_rating`, `exclusion_category` for PRISMA 2020 tracking). `PaperResult` in `api/biblio_hunter.py` for retrieval results.

**Orchestrator usage**:
```python
from agents.orchestrator import SLROrchestrator
from agents.state import create_initial_state

orchestrator = SLROrchestrator(
    progress_callback=lambda phase, percent, msg: print(f"{phase}: {percent}% - {msg}"),
    enable_checkpointing=False  # Disable due to numpy serialization issues
)
initial_state = create_initial_state(
    research_question="...",
    inclusion_criteria=["..."],
    exclusion_criteria=["..."]
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
| uvloop on Windows | Automatically skipped; nest_asyncio used instead |
| Import errors with agents | Ensure all `agents/__init__.py` exports are up to date |

## Quality Assessment (JBI Framework)

Quality scores: HIGH (≥80), MODERATE (60-79), LOW (40-59), CRITICAL (<40)

Weighted criteria: Study Design (25%), Sample Size (20%), Control Group (15%), Randomization (15%), Blinding (10%), Statistical Methods (10%), Confidence Intervals (5%)

## Deployment

**Railway** (Live: https://muezza-ai.up.railway.app/):
- Files: `Procfile`, `railway.toml`, `packages.txt`
- Required: `ANTHROPIC_API_KEY`, `SCOPUS_API_KEY`
- Optional: `SEMANTIC_SCHOLAR_API_KEY`, `UNPAYWALL_EMAIL`

## Windows-Specific Notes

- uvloop is not supported on Windows; the codebase auto-detects and uses `nest_asyncio` instead
- Use `asyncio.run()` for CLI testing of async functions
- File paths use backslashes but the code handles this transparently
