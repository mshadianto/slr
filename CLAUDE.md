# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Muezza AI is a Streamlit-based systematic literature review (SLR) automation system for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) with RAG to automate search, screening, full-text acquisition, quality assessment, and **automated academic writing in formal Indonesian**.

**Key Innovation**: BiblioHunter - intelligent paper retrieval with waterfall PDF acquisition and Virtual Full-Text synthesis for paywalled papers.

## Running the Application

```bash
pip install -r requirements.txt
cp .env.example .env  # Configure API keys
streamlit run app.py --server.port 8502
```

## Railway Deployment

Live URL: https://muezza-ai.up.railway.app/

**Deployment files:**
- `Procfile` - Start command for Railway
- `railway.toml` - Nixpacks builder configuration
- `packages.txt` - System dependencies for Streamlit Cloud (also works with Nixpacks)

**Deploy to Railway:**
1. Connect GitHub repo to Railway
2. Railway auto-detects `Procfile` and uses Nixpacks builder
3. Set environment variables in Railway dashboard (Settings → Variables)
4. Generate domain in Settings → Networking

**Start command** (in `Procfile`):
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**Required Railway Variables:**
- `ANTHROPIC_API_KEY`
- `SCOPUS_API_KEY`
- `SEMANTIC_SCHOLAR_API_KEY` (optional)
- `UNPAYWALL_EMAIL` (optional)

## Required Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...          # Required for screening/quality/narrative
SCOPUS_API_KEY=your_scopus_key        # Required for Scopus search
SEMANTIC_SCHOLAR_API_KEY=your_s2_key  # Recommended (higher rate limits)
UNPAYWALL_EMAIL=your@email.com        # Recommended for PDF waterfall
CORE_API_KEY=your_core_key            # Optional
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

The workflow is a linear state machine defined in `agents/orchestrator.py`:

```
search_node → screening_node → acquisition_node → quality_node → END
                                                        ↓
                    narrative_generator → narrative_orchestrator → docx_export
```

**State Management**: All agents share `SLRState` (TypedDict in `agents/state.py`) which tracks papers through each phase, PRISMA statistics, and agent status.

**Core SLR Agents** (`agents/`):
- `SearchAgent` - PICO parsing, Boolean query generation, Scopus search, RapidFuzz deduplication
- `ScreeningAgent` - 4-phase screening (rule-based → semantic → Claude reasoning → human-in-loop)
- `ScroungerAgent` - BiblioHunter integration for full-text acquisition
- `QualityAgent` - JBI Critical Appraisal framework assessment

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

**Waterfall Order**: Semantic Scholar OA → Unpaywall → CORE → ArXiv → Virtual Full-Text

**Virtual Full-Text** (when no PDF available): Synthesizes content from TL;DR, abstract, citation contexts (up to 15 snippets), related papers, and key references.

### External API Clients (`api/`)

Each client handles its own rate limiting and error recovery:
- `scopus.py` - Elsevier Scopus Search API (5000 req/week, 9/sec)
- `semantic_scholar.py` - Paper metadata and citations (100 req/5min without key)
- `unpaywall.py` - Open access PDF discovery (100K req/day)
- `core_api.py` - CORE aggregator (10 req/sec)
- `arxiv_api.py` - Preprint server (1 req/3sec)

### RAG Component (`rag/chromadb_store.py`)

ChromaDB vector store using `all-MiniLM-L6-v2` embeddings for semantic search during screening and deduplication.

## Testing Individual Components

```bash
# Test BiblioHunter
python -c "from api.biblio_hunter import hunt_paper; print(hunt_paper('10.1038/nature12373'))"

# Test SLR workflow
python -c "
import asyncio
from agents.scrounger_agent import acquire_papers
papers = [{'doi': '10.1038/nature12373'}]
results = asyncio.run(acquire_papers(papers))
print(results)
"

# Test narrative generation
python -c "
from agents import NarrativeOrchestrator
orch = NarrativeOrchestrator(api_key='sk-ant-...')
# orch.generate_full_report(research_question='...', ...)
"
```

## Key Patterns

**Async-first design**: All agents use async/await. Use `asyncio.run()` when testing from CLI.

**Progress callbacks**: Long operations accept `progress_callback` for UI updates:
```python
async def acquire_papers(papers, progress_callback=None):
    if progress_callback:
        progress_callback(f"Processing {len(papers)} papers...")
```

**Pydantic settings**: Configuration in `config.py` uses `BaseSettings` with automatic `.env` loading.

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

## Theme Colors

- Primary: #1E3A5F (dark blue)
- Secondary: #2E8B57 (forest green)
- Accent: #E67E22 (orange)
