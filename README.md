# Muezza AI 🐱

**Faithful Research Companion — Intelligent SLR Automation System**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-blueviolet.svg)](https://muezza-ai.up.railway.app/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![Version](https://img.shields.io/badge/version-2.1.0-gold.svg)](https://github.com/mshadianto/slr)

**Muezza AI** automates the systematic literature review (SLR) process using a multi-agent architecture powered by LangGraph. It implements PRISMA 2020 guidelines with intelligent paper retrieval, screening, quality assessment, and **automated academic writing in formal Indonesian**.

> *"Precision in Research, Integrity in Every Citation"*

---

## Developer

**MS Hadianto**
- GitHub: [@mshadianto](https://github.com/mshadianto)
- Repository: [github.com/mshadianto/slr](https://github.com/mshadianto/slr)

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🐱 Muezza AI v2.1.0                                                        │
│  Faithful Research Companion — Intelligent SLR Automation System            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │ 🔍      │ │ 🔬      │ │ 📥      │ │ ⚖️      │  Agent Status Monitor     │
│  │ Search  │ │Screening│ │Waterfall│ │Quality  │                           │
│  │Strategist│ │Specialist│ │Retrieval│ │Evaluator│                          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  📊 PRISMA 2020 Flow          │  📋 Processing Log                         │
│  [Sankey Diagram]             │  [Terminal-style log]                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  🔬 Forensic Audit Results    │  📝 Drafting Preview (Bab I-V)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Multi-Agent Architecture
- **Search Strategist** - PICO/SPIDER framework parsing, Boolean query generation for Scopus
- **Screening Specialist** - 4-phase LLM-powered title/abstract screening with confidence scoring
- **Waterfall Retrieval** - Multi-source PDF retrieval with Virtual Full-Text synthesis
- **Quality Evaluator** - JBI Critical Appraisal framework assessment
- **Narrative Generator** - Auto-generate Results chapter (BAB IV) in formal Indonesian
- **Narrative Orchestrator** - Full 5-chapter research report generation

### Expert Features
- **Citation Auto-Stitcher** - Automatically match author names with bibliography from Scopus
- **Logic Continuity Agent** - Ensure "benang merah" (red thread) across all chapters
- **Forensic Audit Agent** - Verify every citation against source database

### BiblioHunter - Intelligent Paper Retrieval
- **Multi-identifier support** - DOI, ArXiv ID, PMID, Semantic Scholar ID, Title search
- **Waterfall PDF retrieval** - Semantic Scholar → Unpaywall → CORE → ArXiv
- **Virtual Full-Text** - TL;DR + Abstract + Citation Contexts + Related Papers
- **In-memory caching** - 9000x+ speedup on repeated requests
- **Parallel batch processing** - Configurable workers with progress callbacks
- **Quality scoring** - 0-1 score based on confidence and content completeness

### Premium UI/UX
- **Emerald Green, Gold, Dark Slate Gray** color palette
- **Real-time Agent Status Cards** with animations
- **PRISMA 2020 Sankey Diagram** with interactive hover
- **Terminal-style Processing Log**
- **Citation Verification Modal**
- **Tabbed Drafting Preview** (Bab I - Bab V)
- **Professional Word Export** with title page

### PRISMA 2020 Compliance
- Automatic PRISMA flow diagram generation
- Statistics tracking at each phase
- Transparent exclusion reasons
- Audit trail for reproducibility

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Muezza AI Dashboard                               │
│                         (Streamlit app.py)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LangGraph Orchestrator                             │
│                     (agents/orchestrator.py)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Search Strategist│─────▶│Screening        │─────▶│Waterfall        │
│  (Scopus API)   │      │  Specialist     │      │  Retrieval      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │Quality Evaluator│
                                                  │   (JBI CRaT)    │
                                                  └─────────────────┘
                                                           │
                    ┌──────────────────────────────────────┼──────────────────────────────────────┐
                    ▼                                      ▼                                      ▼
         ┌─────────────────┐                   ┌─────────────────┐                   ┌─────────────────┐
         │    Narrative    │                   │    Narrative    │                   │  Expert Tools   │
         │   Generator     │                   │  Orchestrator   │                   │  (Audit/Cite)   │
         │   (BAB IV)      │                   │  (BAB I-V)      │                   │                 │
         └─────────────────┘                   └─────────────────┘                   └─────────────────┘
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/mshadianto/slr.git
cd slr

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your API keys:
```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Recommended
SCOPUS_API_KEY=your_scopus_key
SEMANTIC_SCHOLAR_API_KEY=your_s2_key

# Optional (enhances PDF retrieval)
UNPAYWALL_EMAIL=your@email.com
CORE_API_KEY=your_core_key
```

### Run

```bash
# Start Muezza AI Dashboard
streamlit run app.py --server.port 8502
```

Open http://localhost:8502 in your browser.

---

## Railway Deployment

**Live Demo:** [https://muezza-ai.up.railway.app/](https://muezza-ai.up.railway.app/)

### Deploy Your Own Instance

1. Fork this repository
2. Create a new project on [Railway](https://railway.app/)
3. Connect your GitHub repo
4. Add environment variables in Railway dashboard:
   - `ANTHROPIC_API_KEY` (required)
   - `SCOPUS_API_KEY` (required)
   - `SEMANTIC_SCHOLAR_API_KEY` (optional)
   - `UNPAYWALL_EMAIL` (optional)
5. Railway auto-detects `Procfile` and deploys

### Deployment Files

| File | Purpose |
|------|---------|
| `Procfile` | Start command for Railway |
| `railway.toml` | Nixpacks builder config |
| `packages.txt` | System dependencies |
| `.streamlit/config.toml` | Streamlit settings |

---

## Dashboard Sections

### Command Center (Sidebar)
- 🔌 **API Status Indicators** - Real-time connection status with pulse animation
- 🎯 **Research Question** - Define your systematic review question
- ✅❌ **Inclusion/Exclusion Criteria** - Dynamic criteria builder
- 📅 **Publication Period** - Date range filter

### Agent Status Monitor
Four agent cards showing real-time status:
| Agent | Role | Status |
|-------|------|--------|
| 🔍 Search Strategist | Boolean query & database search | Pending/Running/Completed |
| 🔬 Screening Specialist | Title/Abstract AI screening | Pending/Running/Completed |
| 📥 Waterfall Retrieval | Multi-source full-text fetch | Pending/Running/Completed |
| ⚖️ Quality Evaluator | JBI critical appraisal | Pending/Running/Completed |

### PRISMA 2020 Flow
- Interactive Sankey diagram
- Real-time statistics
- Hover for details

### Forensic Audit Results
- Paper Title, Source, Retrieval Method, Quality Score
- **Verify Citation** button with verbatim text snippet modal
- Export to CSV, JSON, PRISMA report

### Drafting Preview
- Tabbed interface: Bab I → Bab V
- Word count per chapter
- Download options:
  - 📄 Markdown
  - 📝 Word (Simple)
  - 📑 Word (Pro) - Professional formatting with title page

---

## API Reference

### Narrative Orchestrator

```python
from agents import NarrativeOrchestrator

orchestrator = NarrativeOrchestrator(api_key="sk-ant-...")
chapters = orchestrator.generate_full_report(
    research_question="Bagaimana efektivitas AI dalam diagnosis?",
    scopus_metadata=scopus_stats,
    extraction_table=extracted_data,
    prisma_stats=prisma_stats
)

# Generated chapters:
# BAB I   - Pendahuluan
# BAB II  - Tinjauan Pustaka
# BAB III - Metodologi
# BAB IV  - Hasil dan Pembahasan
# BAB V   - Kesimpulan dan Saran

orchestrator.export_to_word("laporan_lengkap.docx")
```

### Citation Auto-Stitcher

```python
from agents import CitationAutoStitcher, CitationStyle

stitcher = CitationAutoStitcher(citation_style=CitationStyle.APA7)
stitcher.load_bibtex("references.bib")

result = stitcher.stitch_citations(narrative_text)
print(result.stitched_text)
print(result.citations_added)
```

### Forensic Audit Agent

```python
from agents import ForensicAuditAgent

auditor = ForensicAuditAgent(papers_data=slr_papers)
result = auditor.verify_narrative(chapter_text)

print(f"Verification Rate: {result.verification_rate}%")
print(f"Verified: {result.verified_count}")
```

### DocxGenerator

```python
from agents import DocxGenerator

generator = DocxGenerator(
    researcher_name="MS Hadianto",
    institution="Universitas Indonesia"
)

generator.generate_report(
    chapters=chapters_dict,
    bibliography=references_list,
    filename="Laporan_SLR.docx",
    title="LAPORAN SYSTEMATIC LITERATURE REVIEW"
)
```

---

## Project Structure

```
Muezza-AI/
├── app.py                        # Streamlit dashboard (Premium UI)
├── config.py                     # Pydantic settings management
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── README.md                     # This file
│
├── agents/                       # Multi-agent system
│   ├── __init__.py
│   ├── state.py                  # LangGraph state definitions
│   ├── orchestrator.py           # Workflow orchestration
│   ├── search_agent.py           # Scopus search & query generation
│   ├── screening_agent.py        # Title/abstract screening
│   ├── scrounger_agent.py        # Full-text acquisition (BiblioHunter)
│   ├── quality_agent.py          # JBI quality assessment
│   ├── narrative_generator.py    # BAB IV generation (Indonesian)
│   ├── narrative_orchestrator.py # Full 5-chapter report
│   ├── citation_stitcher.py      # Auto citation matching
│   ├── logic_continuity_agent.py # Report coherence checker
│   ├── forensic_audit_agent.py   # Citation verification
│   └── docx_generator.py         # Professional Word export
│
├── api/                          # External API clients
│   ├── biblio_hunter.py          # Enhanced paper retrieval
│   ├── scopus.py                 # Scopus API client
│   ├── unpaywall.py              # Unpaywall API client
│   ├── core_api.py               # CORE API client
│   ├── arxiv_api.py              # ArXiv API client
│   └── semantic_scholar.py       # Semantic Scholar client
│
└── rag/                          # RAG components
    └── chromadb_store.py         # Vector store for semantic search
```

---

## API Keys

| Service | Required | Free Tier | Get Key |
|---------|----------|-----------|---------|
| Anthropic | Yes | No | [console.anthropic.com](https://console.anthropic.com) |
| Scopus | Yes* | Yes (limited) | [dev.elsevier.com](https://dev.elsevier.com) |
| Semantic Scholar | No | Yes (100 req/5min) | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) |
| Unpaywall | No | Yes | Email only |
| CORE | No | Yes (limited) | [core.ac.uk/services/api](https://core.ac.uk/services/api) |

*Scopus required for comprehensive literature search

---

## Performance

### BiblioHunter Benchmarks

| Metric | Value |
|--------|-------|
| Cache speedup | 9000x+ |
| Parallel workers | 3 (configurable) |
| API rate limiting | Automatic |
| Success rate (with VFT) | ~95%+ |

### Typical SLR Processing

| Papers | Search | Screening | Acquisition | Quality |
|--------|--------|-----------|-------------|---------|
| 100 | ~30s | ~5min | ~10min | ~5min |
| 500 | ~2min | ~25min | ~45min | ~25min |
| 1000 | ~5min | ~50min | ~90min | ~50min |

*Times vary based on API rate limits and paper availability*

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-01-22 | Add developer info, dynamic versioning |
| 2.0.0 | 2026-01-22 | Complete UI redesign as Muezza AI |
| 1.5.0 | 2026-01-21 | Add DocxGenerator, Expert Features |
| 1.0.0 | 2026-01-20 | Initial release |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Semantic Scholar](https://www.semanticscholar.org/) - Paper metadata and citation data
- [Unpaywall](https://unpaywall.org/) - Open access PDF discovery
- [CORE](https://core.ac.uk/) - Open access aggregator
- [ArXiv](https://arxiv.org/) - Preprint server
- [Anthropic Claude](https://www.anthropic.com/) - LLM for screening, synthesis, and narrative generation
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration

---

## Citation

If you use Muezza AI in your research, please cite:

```bibtex
@software{muezza2026,
  author = {Hadianto, MS},
  title = {Muezza AI: Faithful Research Companion for Automated Systematic Literature Reviews},
  year = {2026},
  url = {https://github.com/mshadianto/slr},
  version = {2.1.0}
}
```

---

<div align="center">

**🐱 Muezza AI**

*Faithful Research Companion*

Developed by **MS Hadianto**

[GitHub](https://github.com/mshadianto/slr) • [Report Bug](https://github.com/mshadianto/slr/issues)

</div>
