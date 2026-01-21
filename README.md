# BiblioAgent AI

**Intelligent Multi-Agent System for Automated Systematic Literature Reviews**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)

BiblioAgent AI automates the systematic literature review (SLR) process using a multi-agent architecture powered by LangGraph. It implements PRISMA 2020 guidelines with intelligent paper retrieval, screening, quality assessment, and **automated academic writing in formal Indonesian**.

---

## Features

### Multi-Agent Architecture
- **Search Agent** - PICO/SPIDER framework parsing, Boolean query generation for Scopus
- **Screening Agent** - 4-phase LLM-powered title/abstract screening with confidence scoring
- **Scrounger Agent** - Waterfall PDF retrieval with Virtual Full-Text synthesis
- **Quality Agent** - JBI Critical Appraisal framework assessment
- **Narrative Generator** - Auto-generate Results chapter (BAB IV) in formal Indonesian
- **Narrative Orchestrator** - Full 5-chapter research report generation

### Expert Features (NEW)
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

### PRISMA 2020 Compliance
- Automatic PRISMA flow diagram generation
- Statistics tracking at each phase
- Transparent exclusion reasons
- Audit trail for reproducibility

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       BiblioAgent AI Dashboard                           │
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
│  Search Agent   │─────▶│ Screening Agent │─────▶│ Scrounger Agent │
│  (Scopus API)   │      │  (Claude LLM)   │      │  (BiblioHunter) │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  Quality Agent  │
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

## Narrative Generation

### Narrative Generator (BAB IV)

Generates formal Indonesian "Hasil dan Pembahasan" chapter with 6 sub-sections:

```python
from agents import NarrativeGenerator

generator = NarrativeGenerator(anthropic_client=client)
narratives = await generator.generate_full_chapter(slr_results)

# Generated sections:
# 4.1 Proses Seleksi Studi (PRISMA Flow)
# 4.2 Karakteristik Studi yang Diinklusi
# 4.3 Penilaian Kualitas Studi
# 4.4 Sintesis Tematik
# 4.5 Diskusi
# 4.6 Keterbatasan Studi

# Export
generator.export_to_markdown()
generator.export_to_word("bab_iv.docx")
```

### Narrative Orchestrator (Full Report)

Generates complete 5-chapter research report:

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
# BAB I   - Pendahuluan (Background, urgency, research gap)
# BAB II  - Tinjauan Pustaka (Literature synthesis by themes)
# BAB III - Metodologi (SLR, PRISMA, Waterfall Retrieval)
# BAB IV  - Hasil dan Pembahasan (Data analysis)
# BAB V   - Kesimpulan dan Saran (Conclusions, recommendations)

# Export
orchestrator.export_to_markdown()
orchestrator.export_to_word("laporan_lengkap.docx")
```

---

## Expert Features

### 1. Citation Auto-Stitcher

Automatically matches author names in narrative with bibliography entries:

```python
from agents import CitationAutoStitcher, CitationStyle

stitcher = CitationAutoStitcher(citation_style=CitationStyle.APA7)

# Load bibliography from various formats
stitcher.load_bibtex("references.bib")
stitcher.load_ris("scopus_export.ris")
stitcher.load_scopus_csv("scopus.csv")
stitcher.load_from_papers(slr_papers)

# Auto-stitch citations
result = stitcher.stitch_citations(narrative_text)

print(result.stitched_text)      # Text with citations inserted
print(result.citations_added)     # Number of citations added
print(result.bibliography)        # Formatted bibliography

# Supported styles: APA7, Vancouver, Harvard, IEEE
```

**Detects patterns:**
- `Menurut Smith (2023)` → `Menurut Smith (2023) (Smith, 2023)`
- `Studi oleh Wang` → auto-matches to bibliography
- `Garcia et al.` → finds multi-author entries

### 2. Logic Continuity Agent

Ensures logical flow ("benang merah") across all chapters:

```python
from agents import LogicContinuityAgent

agent = LogicContinuityAgent(anthropic_api_key="sk-ant-...")
report = agent.analyze_report(chapters_dict, research_question)

print(f"Overall Score: {report.overall_score}/100")
print(f"Is Coherent: {report.is_coherent}")

# Detailed scores
print(f"RQ Alignment: {report.research_question_alignment}%")
print(f"Method-Results Match: {report.methodology_results_match}%")
print(f"Conclusion Support: {report.conclusion_support_score}%")
print(f"Terminology: {report.terminology_consistency}%")
print(f"Transitions: {report.transition_quality}%")

# Issues found
for issue in report.issues:
    print(f"[{issue.level}] {issue.chapter}: {issue.description}")
    print(f"  Suggestion: {issue.suggestion}")
```

**Checks:**
- Research question alignment across all chapters
- Methodology-results consistency
- Conclusions supported by findings
- Terminology consistency (AI vs Kecerdasan Buatan)
- Smooth transitions between chapters

### 3. Forensic Audit Agent

Verifies every citation against source database:

```python
from agents import ForensicAuditAgent

auditor = ForensicAuditAgent(
    papers_data=slr_papers,
    anthropic_api_key="sk-ant-..."  # Optional for LLM verification
)

result = auditor.verify_narrative(chapter_text)

print(f"Verification Rate: {result.verification_rate}%")
print(f"Verified: {result.verified_count}")
print(f"Unverified: {result.unverified_count}")
print(f"Not Found: {result.not_found_count}")

# Evidence details
for evidence in result.evidences:
    print(f"[{evidence.status}] {evidence.citation_id}")
    print(f"  Claim: {evidence.original_claim}")
    print(f"  Source: {evidence.source_title}")
    print(f"  Similarity: {evidence.similarity_score:.0%}")
```

**Detects citation formats:**
- DOI: `[DOI: 10.1038/xxx]`, `(DOI: ...)`, `https://doi.org/...`
- Author-Year: `(Smith, 2023)`, `Smith et al. (2023)`
- Numbered: `[1]`, `[2-5]`, `[1,3,5]`

**Verification Statuses:**
- ✅ VERIFIED - Claim fully supported by source
- 🔶 PARTIAL - Some support found
- ❌ UNVERIFIED - No support in source content
- ❓ NOT_FOUND - Citation not in database
- 🔍 NEEDS_REVIEW - Manual review recommended

---

## Installation

### Prerequisites
- Python 3.10+
- pip or conda

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/biblioagent-ai.git
cd biblioagent-ai

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

### API Keys

| Service | Required | Free Tier | Get Key |
|---------|----------|-----------|---------|
| Anthropic | Yes | No | [console.anthropic.com](https://console.anthropic.com) |
| Scopus | Yes* | Yes (limited) | [dev.elsevier.com](https://dev.elsevier.com) |
| Semantic Scholar | No | Yes (100 req/5min) | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) |
| Unpaywall | No | Yes | Email only |
| CORE | No | Yes (limited) | [core.ac.uk/services/api](https://core.ac.uk/services/api) |

*Scopus required for comprehensive literature search

---

## Usage

### Web Interface

```bash
# Start the Streamlit dashboard
streamlit run app.py

# Or specify port
streamlit run app.py --server.port 8502
```

Open http://localhost:8501 in your browser.

### Dashboard Sections

```
┌────────────────────────────────────────────────────────────────────────┐
│  📊 PRISMA Metrics & Flowchart                                         │
├────────────────────────────────────────────────────────────────────────┤
│  📑 Synthesis Table (CSV/JSON export)                                  │
├────────────────────────────────────────────────────────────────────────┤
│  📝 Generate Results Chapter (BAB IV)                                  │
│     └── NarrativeGenerator - 6 sub-sections                            │
├────────────────────────────────────────────────────────────────────────┤
│  📚 Generate Full Research Report (5 Chapters)                         │
│     └── NarrativeOrchestrator - BAB I-V                               │
├────────────────────────────────────────────────────────────────────────┤
│  🎓 Expert Features                                                    │
│     ├── 📚 Citation Auto-Stitcher                                      │
│     ├── 🔗 Logic Continuity Check                                      │
│     └── 🔬 Forensic Audit                                              │
└────────────────────────────────────────────────────────────────────────┘
```

### Programmatic Usage

#### Full SLR Pipeline

```python
import asyncio
from agents.orchestrator import SLROrchestrator

async def run_slr():
    orchestrator = SLROrchestrator(
        progress_callback=lambda phase, pct, msg: print(f"[{phase}] {pct}%: {msg}")
    )

    result = await orchestrator.run(
        research_question="What is the impact of AI on healthcare outcomes?",
        inclusion_criteria=[
            "Studies using AI/ML in clinical settings",
            "Peer-reviewed publications",
            "Published 2018-2024"
        ],
        exclusion_criteria=[
            "Non-English publications",
            "Conference abstracts only"
        ],
        date_range=(2018, 2024)
    )

    print(f"Identified: {result['prisma_stats']['identified']}")
    print(f"Included: {result['prisma_stats']['included_synthesis']}")

    return result

asyncio.run(run_slr())
```

#### BiblioHunter Standalone

```python
from api.biblio_hunter import BiblioHunter, hunt_paper

# Quick single paper lookup
paper = hunt_paper("10.1038/nature12373")
print(paper['title'])
print(paper['tldr'])

# Full-featured usage
hunter = BiblioHunter(
    s2_api_key="your_key",
    unpaywall_email="your@email.com",
    enable_cache=True,
    download_dir="./pdfs"
)

# Hunt by DOI
result = hunter.hunt("10.1038/nature12373")

# Hunt by ArXiv ID
result = hunter.hunt("2303.08774")

# Hunt by title
result = hunter.hunt("Attention is All You Need")

# Batch processing with progress
results = hunter.batch_hunt(
    ["10.1038/s41586-020-2649-2", "2303.08774"],
    max_workers=3,
    progress_callback=lambda c, t, m: print(f"[{c}/{t}] {m}")
)

# Download PDF
pdf_path = hunter.download_pdf(result)
```

---

## Project Structure

```
BiblioAgent-AI/
├── app.py                        # Streamlit dashboard
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
│   └── forensic_audit_agent.py   # Citation verification
│
├── api/                          # External API clients
│   ├── __init__.py
│   ├── biblio_hunter.py          # Enhanced paper retrieval
│   ├── scopus.py                 # Scopus API client
│   ├── unpaywall.py              # Unpaywall API client
│   ├── core_api.py               # CORE API client
│   ├── arxiv_api.py              # ArXiv API client
│   └── semantic_scholar.py       # Semantic Scholar client
│
├── rag/                          # RAG components
│   └── chromadb_store.py         # Vector store for semantic search
│
└── docs/                         # Documentation
    └── BIBLIOGRAPHY_STRATEGY.md
```

---

## Virtual Full-Text

When PDFs are not accessible (paywalled), BiblioHunter generates **Virtual Full-Text** by synthesizing:

1. **TL;DR** - One-sentence summary from Semantic Scholar
2. **Abstract** - Full paper abstract
3. **Citation Contexts** - How other papers describe this work (up to 15 contexts)
4. **Related Papers** - Semantically similar papers
5. **Key References** - Most influential references from the paper

### Example Output

```markdown
## TL;DR
GPT-4, a large-scale, multimodal model which can accept image and text inputs...

## ABSTRACT
We report the development of GPT-4, a large-scale, multimodal model...

## CITATION CONTEXTS (How others describe this work)

### Context 1
From: "Large Language Models in Healthcare" (2024)
"GPT-4 demonstrated remarkable capabilities in medical reasoning tasks..."

### Context 2
From: "Multimodal AI Systems" (2024)
"Following the success of GPT-4's vision capabilities..."

## RELATED PAPERS
- PaLM 2 Technical Report (2023)
- LLaMA: Open Foundation Models (2023)
- Claude 3 Technical Report (2024)
```

---

## PRISMA Statistics

The system tracks PRISMA 2020 flow statistics:

| Phase | Metric |
|-------|--------|
| Identification | Records identified from databases |
| Screening | Records screened / excluded |
| Retrieval | Reports sought / not retrieved |
| Eligibility | Reports assessed / excluded |
| Inclusion | Studies included in synthesis |

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

## Troubleshooting

### Common Issues

**Port already in use**
```bash
streamlit run app.py --server.port 8502
```

**Scopus API 401 Error**
- Check API key validity
- Ensure institutional access if required
- Use STANDARD view (not COMPLETE)

**Rate limiting (429)**
- Add API keys for higher limits
- BiblioHunter handles automatic backoff

**numpy serialization error**
- Checkpointing is disabled by default
- Use `enable_checkpointing=False` in orchestrator

**python-docx not installed**
```bash
pip install python-docx
```

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

If you use BiblioAgent AI in your research, please cite:

```bibtex
@software{biblioagent2024,
  title = {BiblioAgent AI: Intelligent Multi-Agent System for Automated Systematic Literature Reviews},
  year = {2024},
  url = {https://github.com/yourusername/biblioagent-ai}
}
```
