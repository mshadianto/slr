# Strategi Mendapatkan Data Bibliography untuk SLR

## Overview

Dokumen ini menjelaskan berbagai metode untuk mendapatkan data bibliography yang dapat digunakan dalam BiblioAgent AI untuk Systematic Literature Review.

---

## 1. Database Akademik Utama

### A. Scopus (Terintegrasi di BiblioAgent)
**URL**: https://www.scopus.com

**Cara Export:**
1. Login ke Scopus
2. Jalankan pencarian dengan query
3. Select All → Export → BibTeX / RIS / CSV
4. Download file

**Free Tier API:**
- Daftar di https://dev.elsevier.com
- 5000 requests/week
- BiblioAgent sudah terintegrasi otomatis

### B. Web of Science
**URL**: https://www.webofscience.com

**Cara Export:**
1. Login via institusi
2. Jalankan pencarian
3. Export → BibTeX / EndNote / Plain Text
4. Max 1000 records per export

### C. PubMed / MEDLINE
**URL**: https://pubmed.ncbi.nlm.nih.gov

**Cara Export:**
1. Jalankan pencarian
2. Save → All results → Format: PubMed
3. Atau gunakan E-utilities API (gratis)

**API Gratis:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=YOUR_QUERY
```

### D. Google Scholar
**URL**: https://scholar.google.com

**Cara Export:**
1. Install ekstensi browser "Google Scholar Button"
2. Atau gunakan tool seperti Publish or Perish
3. Export ke BibTeX

**Catatan:** Tidak ada official API, gunakan scraping dengan hati-hati

---

## 2. Open Access Repositories

### A. CORE (Terintegrasi di BiblioAgent)
**URL**: https://core.ac.uk

- 200M+ open access articles
- API gratis: https://core.ac.uk/services/api
- Sudah terintegrasi di BiblioAgent

### B. arXiv (Terintegrasi di BiblioAgent)
**URL**: https://arxiv.org

**Cara Export:**
1. Cari paper di arXiv
2. Export Citation → BibTeX
3. Atau gunakan API: http://export.arxiv.org/api/query

### C. Semantic Scholar (Terintegrasi di BiblioAgent)
**URL**: https://www.semanticscholar.org

- API gratis dengan rate limit
- Kaya metadata dan citation context
- Sudah terintegrasi di BiblioAgent

### D. OpenAlex
**URL**: https://openalex.org

**API Gratis:**
```
https://api.openalex.org/works?search=YOUR_QUERY
```
- 100M+ works
- Polite pool: 100K requests/day

---

## 3. Reference Managers

### A. Zotero
**URL**: https://www.zotero.org

**Export:**
1. Select items → Right click → Export Items
2. Format: BibTeX / RIS / CSV
3. Atau sync dengan Zotero API

### B. Mendeley
**URL**: https://www.mendeley.com

**Export:**
1. Select references → File → Export
2. Format: BibTeX / RIS

### C. EndNote
**Export:**
1. Select references → File → Export
2. Format: BibTeX / RIS / XML

---

## 4. Automated Search Strategy

### A. Boolean Query Generator (BiblioAgent Built-in)

BiblioAgent otomatis generate Boolean query dari research question:

```
Input: "What is the effectiveness of machine learning in cancer diagnosis?"

Generated Query:
TITLE-ABS-KEY("machine learning" OR "artificial intelligence" OR "deep learning")
AND TITLE-ABS-KEY("cancer" OR "tumor" OR "oncology")
AND TITLE-ABS-KEY("diagnosis" OR "detection" OR "screening")
AND PUBYEAR > 2017 AND PUBYEAR < 2026
AND LANGUAGE(english)
```

### B. PICO Framework Extraction

BiblioAgent menggunakan PICO untuk memparse research question:

| Element | Deskripsi | Keywords |
|---------|-----------|----------|
| **P**opulation | Siapa yang diteliti | patients, adults, children |
| **I**ntervention | Apa yang diuji | treatment, therapy, method |
| **C**omparison | Pembanding | placebo, control, standard |
| **O**utcome | Hasil yang diukur | survival, accuracy, efficacy |

---

## 5. Multi-Database Search Strategy

### Recommended Workflow:

```
┌─────────────────┐
│  Research       │
│  Question       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate PICO   │
│ Boolean Query   │
└────────┬────────┘
         │
    ┌────┴────┬─────────┬─────────┐
    ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Scopus │ │PubMed │ │ WoS   │ │Scholar│
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │
    └────┬────┴─────────┴────┬────┘
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│  Merge & Dedup  │  │ Save as .bib    │
│  (RapidFuzz)    │  │ or .ris file    │
└────────┬────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Upload to       │
│ BiblioAgent     │
└─────────────────┘
```

---

## 6. File Formats Supported

| Format | Extension | Best For |
|--------|-----------|----------|
| BibTeX | .bib | LaTeX users, comprehensive metadata |
| RIS | .ris | Reference managers, universal |
| CSV | .csv | Spreadsheet analysis |
| EndNote XML | .xml | EndNote users |

### Sample BibTeX Entry:
```bibtex
@article{smith2023,
  author = {Smith, John and Doe, Jane},
  title = {Machine Learning in Healthcare},
  journal = {Nature Medicine},
  year = {2023},
  volume = {29},
  pages = {1234-1245},
  doi = {10.1038/s41591-023-1234},
  abstract = {This study investigates...}
}
```

---

## 7. Tips untuk Comprehensive Search

### DO:
- ✅ Gunakan minimal 2-3 database berbeda
- ✅ Include grey literature (theses, preprints)
- ✅ Dokumentasikan search strategy (reproducibility)
- ✅ Export dengan metadata lengkap (abstract, keywords)
- ✅ Simpan date of search

### DON'T:
- ❌ Hanya gunakan satu database
- ❌ Abaikan non-English literature (jika relevan)
- ❌ Skip deduplication
- ❌ Lupa mencatat exclusion reasons

---

## 8. Quick Start untuk BiblioAgent

### Option A: Upload File Bibliography
1. Export dari Scopus/PubMed/WoS sebagai .bib atau .ris
2. Buka BiblioAgent di http://localhost:8501
3. Upload file di sidebar
4. Masukkan research question dan criteria
5. Klik "Run"

### Option B: Direct API Search (Recommended)
1. Buka BiblioAgent di http://localhost:8501
2. Masukkan research question
3. BiblioAgent otomatis search via Scopus API
4. System akan melakukan screening, acquisition, dan quality assessment

---

## 9. Contoh Research Questions

### Medical/Health:
```
What is the effectiveness of telemedicine interventions
on patient outcomes in chronic disease management?
```

### Technology:
```
How does artificial intelligence improve accuracy
in medical image diagnosis compared to traditional methods?
```

### Social Science:
```
What are the impacts of remote work on employee
productivity and well-being during the COVID-19 pandemic?
```

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| Export limit reached | Split search into smaller batches |
| Encoding errors | Save as UTF-8, avoid special characters |
| Missing abstracts | Re-export with "Include abstract" option |
| Duplicate entries | BiblioAgent auto-deduplicates with RapidFuzz |

---

## Resources

- PRISMA Guidelines: https://prisma-statement.org
- Cochrane Handbook: https://training.cochrane.org/handbook
- JBI Manual: https://jbi.global/jbi-manual-for-evidence-synthesis
