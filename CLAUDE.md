# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Muezza AI is a Streamlit-based systematic literature review (SLR) automation system for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) with RAG to automate search, screening, full-text acquisition, quality assessment, and automated academic writing in formal Indonesian.

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

## Testing

No pytest suite. There is a manual test script and CLI one-liners:

```bash
# Run feature tests (exclusion reasons, AI priority screening, i18n, caching)
python test_new_features.py

# Test BiblioHunter retrieval
python -c "from api.biblio_hunter import hunt_paper; print(hunt_paper('10.1038/nature12373'))"

# Test API clients
python -c "from api.openalex import OpenAlexClient; print(OpenAlexClient().search('machine learning'))"

# Test async agents (all agents are async)
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

## Required Environment Variables

Create `.env` file (see `.env.example`):
```env
ANTHROPIC_API_KEY=sk-ant-...          # Required - screening/quality/narrative
SCOPUS_API_KEY=your_scopus_key        # Required - Scopus search + ScienceDirect
ELSEVIER_INST_TOKEN=your_inst_token   # Optional - off-campus ScienceDirect
SEMANTIC_SCHOLAR_API_KEY=your_s2_key  # Recommended - higher rate limits
UNPAYWALL_EMAIL=your@email.com        # Recommended - PDF waterfall
CORE_API_KEY=your_core_key            # Optional
OPENALEX_EMAIL=your@email.com         # Optional - polite pool
NCBI_API_KEY=your_ncbi_key            # Optional - 10 req/sec vs 3 req/sec
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

Linear state machine defined in `agents/orchestrator.py`. The Streamlit UI in `app.py` (3000+ lines) drives the orchestrator and renders all results.

```
search_node → screening_node → acquisition_node → quality_node → END
                                                        ↓
                    narrative_generator → narrative_orchestrator → docx_export
```

### State Management

All agents share `SLRState` (TypedDict in `agents/state.py`). Key types:
- `SLRState` - shared pipeline state tracking papers through each phase, PRISMA statistics, agent statuses
- `Paper` dataclass - carries all paper metadata through the pipeline (identifiers, screening results, `ai_priority_rating`, `exclusion_category`, quality scores)
- `PRISMAStats` dataclass - PRISMA 2020 flow statistics (identification → screening → eligibility → included)
- `AgentStatus` enum - PENDING/ACTIVE/COMPLETED/ERROR/PAUSED

### Agent Categories

**Pipeline agents** (executed sequentially by orchestrator):
- `SearchAgent` - PICO/SPIDER parsing → Boolean query → Scopus search → RapidFuzz deduplication
- `ScreeningAgent` - 4-phase: rule-based → semantic similarity → Claude LLM reasoning → human-in-loop
- `ScreeningPriorityAgent` - Rayyan-style 1-5 star AI priority ratings using scikit-learn active learning (needs 50+ decisions)
- `ScroungerAgent` - BiblioHunter integration for full-text acquisition
- `QualityAgent` - JBI Critical Appraisal framework (weighted criteria scoring)

**Report generation agents** (post-pipeline, called from app.py):
- `NarrativeGenerator` → `NarrativeOrchestrator` → `DocxGenerator` (BAB I-V in formal Indonesian)
- `CitationAutoStitcher` - APA7/Vancouver citation matching
- `LogicContinuityAgent` - cross-chapter coherence ("benang merah")
- `ForensicAuditAgent` - verify every citation against source database

**Analysis agents** (independent, callable separately):
- `CitationNetworkAgent` - PageRank centrality, cluster detection, visualization
- `CitationContextAnalyzer` - Scite-style classification (Supporting/Contrasting/Mentioning)
- `BibliometricAgent` - publication trends, journal distribution charts

### BiblioHunter (`api/biblio_hunter.py`)

Core paper retrieval engine. Accepts DOI, ArXiv ID, PMID, or title. Tries sources in waterfall order until a full-text is found:

ScienceDirect → Semantic Scholar OA → Unpaywall → OpenAlex → Crossref → DOAJ → PubMed Central → CORE → ArXiv → Google Scholar → Virtual Full-Text (fallback)

**Virtual Full-Text** synthesizes content from TL;DR, abstract, citation contexts (up to 15 snippets), and related papers for paywalled papers. Uses `PaperResult` dataclass for retrieval results.

### API Clients (`api/`)

Each client in `api/` handles its own rate limiting and error recovery. Rate limits are configured in `config.py`. Key infrastructure:
- `connection_pool.py` - HTTP connection pooling with per-API rate limiting and retry logic
- `search_cache.py` - Hybrid LRU/LFU cache with adaptive TTL, compression, thread-safe (500MB default limit)
- `query_translator.py` - Indonesian → English translation with 40+ academic term mappings
- `pdf_processor.py` - PDF text extraction via PyMuPDF and pdfplumber

### RAG Component (`rag/chromadb_store.py`)

ChromaDB vector store using `all-MiniLM-L6-v2` embeddings for semantic search during screening and deduplication.

### Internationalization (`utils/i18n.py`)

Bilingual Indonesian/English support. Use `get_text(key, lang)` for UI strings. All PRISMA categories, exclusion reasons, and agent labels have i18n keys.

## Key Patterns

**Async-first**: All agents use async/await. Use `asyncio.run()` for CLI testing.

**Progress callbacks**: Long operations accept `progress_callback` for Streamlit UI updates:
```python
progress_callback(f"Processing {len(papers)} papers...")
```

**Configuration**: `config.py` uses Pydantic `BaseSettings` with automatic `.env` loading. Access via `from config import settings`. Singleton via `@lru_cache`.

**Caching**: BiblioHunter uses 24-hour TTL in-memory cache. SearchCache provides LRU eviction with configurable TTL (default 1 hour).

**Checkpointing**: Disabled by default (`enable_checkpointing=False`) due to numpy serialization issues.

**PRISMA 2020 tracking**: `ExclusionCategory` enum and `ExclusionReasonManager` in `agents/exclusion_reasons.py` provide structured exclusion tracking with predefined reason keys per category.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8501 in use | Use `--server.port 8502` |
| Scopus 401 error | Check API key, use STANDARD view |
| Rate limiting (429) | Add API keys; BiblioHunter handles backoff automatically |
| numpy serialization | Use `enable_checkpointing=False` in orchestrator |
| uvloop on Windows | Automatically skipped; nest_asyncio used instead |
| Import errors with agents | Ensure `agents/__init__.py` exports are up to date |

## Deployment

**Railway** (Live: https://muezza-ai.up.railway.app/):
- Config files: `Procfile`, `railway.toml`, `packages.txt`
- Dockerfile uses Python 3.11-slim
- Railway health check: `/_stcore/health` (300s timeout)
