# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BiblioAgent AI is a Streamlit-based systematic literature review (SLR) automation system designed for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) combined with RAG (Retrieval-Augmented Generation) to automate search, screening, full-text acquisition, and quality assessment of academic papers.

**Key Innovation**: BiblioHunter - intelligent paper retrieval with waterfall PDF acquisition and Virtual Full-Text synthesis for paywalled papers.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure API keys
cp .env.example .env

# Run the integrated dashboard
streamlit run app.py

# Or specify a different port if 8501 is in use
streamlit run app.py --server.port 8502
```

## Project Structure

```
C:\SLR/
├── app.py                              # Main integrated Streamlit dashboard
├── config.py                           # Pydantic settings management
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment template
├── README.md                           # Project documentation
├── CLAUDE.md                           # This file
│
├── agents/                             # Multi-agent system (LangGraph)
│   ├── __init__.py
│   ├── state.py                        # LangGraph state definitions (SLRState, Paper, PRISMAStats)
│   ├── orchestrator.py                 # LangGraph workflow orchestration
│   ├── search_agent.py                 # PICO parsing, Boolean query generation, Scopus search
│   ├── screening_agent.py              # 4-phase screening with Claude API
│   ├── scrounger_agent.py              # Full-text acquisition with BiblioHunter integration
│   └── quality_agent.py                # JBI quality assessment
│
├── api/                                # External API clients
│   ├── __init__.py
│   ├── biblio_hunter.py                # Enhanced paper retrieval (NEW - main retrieval engine)
│   ├── scopus.py                       # Scopus Search API
│   ├── unpaywall.py                    # Unpaywall OA lookup
│   ├── core_api.py                     # CORE aggregator
│   ├── arxiv_api.py                    # ArXiv preprint search
│   └── semantic_scholar.py             # Semantic Scholar API
│
├── rag/                                # RAG components
│   ├── __init__.py
│   └── chromadb_store.py               # ChromaDB vector store
│
├── docs/                               # Documentation
│   └── BIBLIOGRAPHY_STRATEGY.md        # Bibliography acquisition strategy
│
├── BiblioAgent_Streamlit_Dashboard.py  # Original mock dashboard (legacy)
├── BiblioAgent_Workflow.mermaid        # Workflow diagram
└── BiblioAgent_AI_Technical_Blueprint.docx  # Technical specification
```

## Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
# Required
ANTHROPIC_API_KEY=your_claude_api_key      # Required for screening/quality

# Required for Search
SCOPUS_API_KEY=your_scopus_api_key         # Required for Scopus search

# Recommended for BiblioHunter
SEMANTIC_SCHOLAR_API_KEY=your_s2_key       # Higher rate limits (100 req/5min → 1 req/sec)
UNPAYWALL_EMAIL=your_email@domain.com      # Required for Unpaywall waterfall

# Optional
CORE_API_KEY=your_core_key                 # Optional CORE access
CHROMA_PERSIST_DIR=./data/chroma_db        # Vector store location
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

```
Workflow: search_node → screening_node → acquisition_node → quality_node → END
```

1. **Search Agent** (`agents/search_agent.py`)
   - Parses PICO/SPIDER framework from research question
   - Generates Boolean queries with MeSH term expansion
   - Executes Scopus API search with auto-refinement
   - Deduplicates using RapidFuzz title similarity

2. **Screening Agent** (`agents/screening_agent.py`)
   - Phase 1: Rule-based exclusion (doc type, language, patterns)
   - Phase 2: Semantic similarity via sentence-transformers
   - Phase 3: Claude API reasoning for borderline cases
   - Phase 4: Human-in-the-loop flagging for uncertain papers

3. **Scrounger Agent** (`agents/scrounger_agent.py`) - **BiblioHunter Integrated**
   - Uses BiblioHunter for intelligent paper acquisition
   - Waterfall PDF retrieval: S2 → Unpaywall → CORE → ArXiv
   - Virtual Full-Text synthesis for paywalled papers
   - Parallel batch processing with caching
   - Quality scoring per paper

4. **Quality Agent** (`agents/quality_agent.py`)
   - JBI Critical Appraisal framework
   - Weighted criteria extraction
   - Categories: HIGH (≥80), MODERATE (60-79), LOW (40-59), CRITICAL (<40)

## BiblioHunter (`api/biblio_hunter.py`)

BiblioHunter is the core paper retrieval engine with these features:

### Multi-Identifier Support
```python
hunter.hunt("10.1038/nature12373")      # DOI
hunter.hunt("2303.08774")                # ArXiv ID
hunter.hunt("PMID:12345678")             # PubMed ID
hunter.hunt("attention is all you need") # Title search
```

### Waterfall PDF Retrieval
```
1. Semantic Scholar Open Access → PDF found? Return
2. Unpaywall (Green/Gold OA)    → PDF found? Return
3. CORE (200M+ papers)          → PDF found? Return
4. ArXiv (title search)         → PDF found? Return
5. Virtual Full-Text            → Generate synthesis
```

### Virtual Full-Text Generation
When no PDF is available, generates content from:
- **TL;DR** - One-sentence summary from Semantic Scholar
- **Abstract** - Full paper abstract
- **Citation Contexts** - Up to 15 snippets from citing papers
- **Related Papers** - Semantically similar papers
- **Key References** - Influential references from the paper

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `BiblioHunter` | `api/biblio_hunter.py` | Main paper retrieval engine |
| `PaperResult` | `api/biblio_hunter.py` | Structured retrieval result (dataclass) |
| `BiblioHunterCache` | `api/biblio_hunter.py` | In-memory cache with TTL |
| `ScroungerAgent` | `agents/scrounger_agent.py` | Acquisition phase using BiblioHunter |
| `SLRState` | `agents/state.py` | LangGraph state TypedDict |
| `SLROrchestrator` | `agents/orchestrator.py` | Workflow runner |

### BiblioHunter Usage

```python
from api.biblio_hunter import BiblioHunter, hunt_paper, batch_hunt_papers

# Quick single paper
paper = hunt_paper("10.1038/nature12373")

# Full-featured usage
hunter = BiblioHunter(
    s2_api_key="your_key",
    unpaywall_email="your@email.com",
    enable_cache=True,
    download_dir="./pdfs"
)

# Single paper
result = hunter.hunt("10.1038/nature12373")
print(result.title)
print(result.tldr)
print(result.full_text_source)  # semantic_scholar_oa / virtual_fulltext
print(result.quality_score)     # 0-1 score

# Batch processing with progress
results = hunter.batch_hunt(
    ["10.1038/nature12373", "2303.08774"],
    max_workers=3,
    progress_callback=lambda cur, tot, msg: print(f"[{cur}/{tot}] {msg}")
)

# Download PDF
pdf_path = hunter.download_pdf(result)

# Get stats
print(hunter.get_stats())
# {'total_requests': 5, 'cache_hits': 2, 'pdf_found': 3, 'virtual_fulltext_generated': 2}
```

### Paper Result Fields

After retrieval, each paper has these fields:

| Field | Type | Description |
|-------|------|-------------|
| `full_text` | str | PDF text or Virtual Full-Text content |
| `full_text_source` | str | semantic_scholar_oa / unpaywall / core / arxiv / virtual_fulltext |
| `pdf_url` | str | Direct PDF URL if available |
| `tldr` | str | One-sentence summary |
| `retrieval_confidence` | float | 0-1 confidence score |
| `retrieval_quality_score` | float | 0-1 quality score |
| `citation_contexts_count` | int | Number of citation contexts (VFT) |
| `related_papers` | list | Related paper suggestions |

## API Rate Limits

| Service | Limit | Client |
|---------|-------|--------|
| Scopus | 5000 req/week, 9/sec | `api/scopus.py` |
| Semantic Scholar | 100 req/5min (no key) / 1 req/sec (with key) | `api/biblio_hunter.py` |
| Unpaywall | 100K req/day | `api/biblio_hunter.py` |
| CORE | 10 req/sec | `api/biblio_hunter.py` |
| ArXiv | 1 req/3sec | `api/biblio_hunter.py` |

## Quality Assessment (JBI Framework)

| Criterion | Weight | Extraction Method |
|-----------|--------|-------------------|
| Study Design | 25% | Regex patterns + hierarchy scoring |
| Sample Size | 20% | Numeric extraction with thresholds |
| Control Group | 15% | Pattern matching |
| Randomization | 15% | Keyword detection |
| Blinding | 10% | Context analysis |
| Statistical Methods | 10% | Method extraction |
| Confidence Intervals | 5% | Numeric detection |

## Common Commands

```bash
# Run the app
streamlit run app.py --server.port 8502

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
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8501 in use | Use `--server.port 8502` |
| Scopus 401 error | Check API key, use STANDARD view |
| Rate limiting (429) | Add API keys, BiblioHunter handles backoff |
| numpy serialization | Use `enable_checkpointing=False` in orchestrator |
| Module not found | Run `pip install -r requirements.txt` |

## Theme Colors

- Primary: #1E3A5F (dark blue)
- Secondary: #2E8B57 (forest green)
- Accent: #E67E22 (orange)
- Success: #10B981, Warning: #F59E0B, Danger: #EF4444

## Reference Files

- `README.md`: Full project documentation
- `BiblioAgent_Workflow.mermaid`: Visual workflow diagram
- `BiblioAgent_AI_Technical_Blueprint.docx`: Original technical specification
- `docs/BIBLIOGRAPHY_STRATEGY.md`: Bibliography acquisition strategy
