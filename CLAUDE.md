# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Muezza AI (formerly BiblioAgent AI) is a Streamlit-based systematic literature review (SLR) automation system for PRISMA 2020 compliance. It uses a multi-agent architecture (LangGraph) with RAG to automate search, screening, full-text acquisition, quality assessment, and **automated academic writing in formal Indonesian**.

**Key Innovation**: BiblioHunter - intelligent paper retrieval with waterfall PDF acquisition and Virtual Full-Text synthesis for paywalled papers.

## Running the Application

```bash
pip install -r requirements.txt
cp .env.example .env  # Configure API keys
streamlit run app.py --server.port 8502
```

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

```
search_node → screening_node → acquisition_node → quality_node → END
                                                        ↓
                    narrative_generator → narrative_orchestrator → docx_export
```

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

**State Management**:
- `SLRState` - LangGraph TypedDict in `agents/state.py`
- `SLROrchestrator` - Workflow runner in `agents/orchestrator.py`

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

### API Rate Limits

| Service | Limit |
|---------|-------|
| Scopus | 5000 req/week, 9/sec |
| Semantic Scholar | 100 req/5min (no key) / 1 req/sec (with key) |
| Unpaywall | 100K req/day |
| CORE | 10 req/sec |
| ArXiv | 1 req/3sec |

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
