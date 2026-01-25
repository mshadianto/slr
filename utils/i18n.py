"""
Muezza AI - Internationalization (i18n) Module
===============================================
Bilingual text support for Indonesian and English.
"""

from typing import Optional, Dict, Any

# Supported languages
SUPPORTED_LANGUAGES = {
    "id": "Bahasa Indonesia",
    "en": "English"
}

# Default language
_current_language = "id"

# ============================================================================
# BILINGUAL TEXT DICTIONARY
# ============================================================================

TEXTS: Dict[str, Dict[str, str]] = {
    # -------------------------------------------------------------------------
    # General UI
    # -------------------------------------------------------------------------
    "app_title": {
        "id": "Muezza AI",
        "en": "Muezza AI"
    },
    "app_tagline": {
        "id": "Pendamping Penelitian Setia",
        "en": "Faithful Research Companion"
    },
    "language_label": {
        "id": "Bahasa / Language",
        "en": "Language / Bahasa"
    },
    "loading": {
        "id": "Memuat...",
        "en": "Loading..."
    },
    "processing": {
        "id": "Memproses...",
        "en": "Processing..."
    },
    "computing": {
        "id": "Menghitung...",
        "en": "Computing..."
    },
    "success": {
        "id": "Berhasil",
        "en": "Success"
    },
    "error": {
        "id": "Kesalahan",
        "en": "Error"
    },
    "warning": {
        "id": "Peringatan",
        "en": "Warning"
    },
    "info": {
        "id": "Informasi",
        "en": "Information"
    },
    "confirm": {
        "id": "Konfirmasi",
        "en": "Confirm"
    },
    "cancel": {
        "id": "Batal",
        "en": "Cancel"
    },
    "save": {
        "id": "Simpan",
        "en": "Save"
    },
    "reset": {
        "id": "Reset",
        "en": "Reset"
    },
    "export": {
        "id": "Ekspor",
        "en": "Export"
    },
    "include": {
        "id": "Masukkan",
        "en": "Include"
    },
    "exclude": {
        "id": "Keluarkan",
        "en": "Exclude"
    },
    "other": {
        "id": "Lainnya",
        "en": "Other"
    },

    # -------------------------------------------------------------------------
    # AI Priority Screening Section
    # -------------------------------------------------------------------------
    "ai_priority_title": {
        "id": "Prioritas Skrining AI",
        "en": "AI Screening Priority"
    },
    "ai_priority_subtitle": {
        "id": "Sistem rating berbasis active learning untuk memprioritaskan paper",
        "en": "Active learning-based rating system to prioritize papers"
    },
    "compute_ratings": {
        "id": "Hitung Rating",
        "en": "Compute Ratings"
    },
    "recompute_ratings": {
        "id": "Hitung Ulang Rating",
        "en": "Recompute Ratings"
    },
    "need_more_decisions": {
        "id": "Butuh lebih banyak keputusan skrining",
        "en": "Need more screening decisions"
    },
    "decisions_made": {
        "id": "keputusan dibuat",
        "en": "decisions made"
    },
    "minimum_required": {
        "id": "minimum diperlukan",
        "en": "minimum required"
    },
    "ratings_computed": {
        "id": "Rating telah dihitung",
        "en": "Ratings computed"
    },
    "ratings_updated": {
        "id": "Rating diperbarui",
        "en": "Ratings updated"
    },
    "priority_queue": {
        "id": "Antrian Prioritas",
        "en": "Priority Queue"
    },
    "high_priority": {
        "id": "Prioritas Tinggi",
        "en": "High Priority"
    },
    "medium_priority": {
        "id": "Prioritas Sedang",
        "en": "Medium Priority"
    },
    "low_priority": {
        "id": "Prioritas Rendah",
        "en": "Low Priority"
    },
    "ai_confidence": {
        "id": "Kepercayaan AI",
        "en": "AI Confidence"
    },
    "predicted_relevance": {
        "id": "Prediksi Relevansi",
        "en": "Predicted Relevance"
    },
    "stars": {
        "id": "bintang",
        "en": "stars"
    },
    "sort_by_priority": {
        "id": "Urutkan berdasarkan Prioritas",
        "en": "Sort by Priority"
    },
    "show_all_papers": {
        "id": "Tampilkan Semua Paper",
        "en": "Show All Papers"
    },
    "pending_screening": {
        "id": "Menunggu Skrining",
        "en": "Pending Screening"
    },

    # -------------------------------------------------------------------------
    # Exclusion Reasons Section
    # -------------------------------------------------------------------------
    "exclusion_reasons_title": {
        "id": "Alasan Eksklusi",
        "en": "Exclusion Reasons"
    },
    "select_exclusion_reason": {
        "id": "Pilih Alasan Eksklusi",
        "en": "Select Exclusion Reason"
    },
    "exclusion_category": {
        "id": "Kategori Eksklusi",
        "en": "Exclusion Category"
    },
    "exclusion_reason": {
        "id": "Alasan",
        "en": "Reason"
    },
    "custom_reason": {
        "id": "Alasan Kustom",
        "en": "Custom Reason"
    },
    "enter_custom_reason": {
        "id": "Masukkan alasan kustom...",
        "en": "Enter custom reason..."
    },
    "confirm_exclusion": {
        "id": "Konfirmasi Eksklusi",
        "en": "Confirm Exclusion"
    },
    "exclusion_statistics": {
        "id": "Statistik Eksklusi",
        "en": "Exclusion Statistics"
    },
    "exclusion_by_category": {
        "id": "Eksklusi per Kategori",
        "en": "Exclusion by Category"
    },
    "total_excluded": {
        "id": "Total Dieksklusi",
        "en": "Total Excluded"
    },
    "no_exclusions_yet": {
        "id": "Belum ada eksklusi",
        "en": "No exclusions yet"
    },
    "papers_excluded": {
        "id": "paper dieksklusi",
        "en": "papers excluded"
    },

    # -------------------------------------------------------------------------
    # Exclusion Categories (PRISMA 2020)
    # -------------------------------------------------------------------------
    "cat_population": {
        "id": "Populasi tidak sesuai",
        "en": "Wrong population"
    },
    "cat_intervention": {
        "id": "Intervensi tidak sesuai",
        "en": "Wrong intervention"
    },
    "cat_comparator": {
        "id": "Pembanding tidak sesuai",
        "en": "Wrong comparator"
    },
    "cat_outcome": {
        "id": "Outcome tidak sesuai",
        "en": "Wrong outcome"
    },
    "cat_study_design": {
        "id": "Desain studi tidak sesuai",
        "en": "Wrong study design"
    },
    "cat_publication_type": {
        "id": "Tipe publikasi tidak sesuai",
        "en": "Wrong publication type"
    },
    "cat_language": {
        "id": "Bahasa tidak sesuai",
        "en": "Wrong language"
    },
    "cat_duplicate": {
        "id": "Duplikat",
        "en": "Duplicate"
    },
    "cat_full_text_unavailable": {
        "id": "Teks lengkap tidak tersedia",
        "en": "Full text unavailable"
    },
    "cat_other": {
        "id": "Lainnya",
        "en": "Other"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Population
    # -------------------------------------------------------------------------
    "reason_not_human": {
        "id": "Bukan subjek manusia",
        "en": "Not human subjects"
    },
    "reason_wrong_age": {
        "id": "Kelompok usia tidak sesuai",
        "en": "Wrong age group"
    },
    "reason_wrong_disease": {
        "id": "Penyakit/kondisi tidak sesuai",
        "en": "Wrong disease/condition"
    },
    "reason_wrong_setting": {
        "id": "Setting tidak sesuai",
        "en": "Wrong setting"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Intervention
    # -------------------------------------------------------------------------
    "reason_wrong_intervention": {
        "id": "Intervensi berbeda dari kriteria",
        "en": "Different intervention from criteria"
    },
    "reason_no_intervention": {
        "id": "Tidak ada intervensi",
        "en": "No intervention"
    },
    "reason_combined_intervention": {
        "id": "Intervensi kombinasi tidak dapat dipisahkan",
        "en": "Combined intervention cannot be separated"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Comparator
    # -------------------------------------------------------------------------
    "reason_no_comparator": {
        "id": "Tidak ada kelompok pembanding",
        "en": "No comparator group"
    },
    "reason_wrong_comparator": {
        "id": "Pembanding tidak relevan",
        "en": "Irrelevant comparator"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Outcome
    # -------------------------------------------------------------------------
    "reason_wrong_outcome": {
        "id": "Outcome tidak sesuai kriteria",
        "en": "Outcome not matching criteria"
    },
    "reason_no_outcome_data": {
        "id": "Data outcome tidak tersedia",
        "en": "Outcome data not available"
    },
    "reason_composite_outcome": {
        "id": "Outcome komposit tidak dapat dipisahkan",
        "en": "Composite outcome cannot be separated"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Study Design
    # -------------------------------------------------------------------------
    "reason_not_empirical": {
        "id": "Bukan studi empiris",
        "en": "Not an empirical study"
    },
    "reason_review_only": {
        "id": "Review/meta-analisis (bukan studi primer)",
        "en": "Review/meta-analysis (not primary study)"
    },
    "reason_case_report": {
        "id": "Hanya laporan kasus",
        "en": "Case report only"
    },
    "reason_editorial": {
        "id": "Editorial/opini/komentar",
        "en": "Editorial/opinion/commentary"
    },
    "reason_protocol": {
        "id": "Protokol studi (bukan hasil)",
        "en": "Study protocol (no results)"
    },
    "reason_conference_abstract": {
        "id": "Abstrak konferensi saja",
        "en": "Conference abstract only"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Publication Type
    # -------------------------------------------------------------------------
    "reason_letter": {
        "id": "Surat ke editor",
        "en": "Letter to editor"
    },
    "reason_erratum": {
        "id": "Erratum/koreksi",
        "en": "Erratum/correction"
    },
    "reason_retracted": {
        "id": "Artikel ditarik",
        "en": "Retracted article"
    },
    "reason_book_chapter": {
        "id": "Bab buku",
        "en": "Book chapter"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Language
    # -------------------------------------------------------------------------
    "reason_not_english": {
        "id": "Bukan bahasa Inggris",
        "en": "Not in English"
    },
    "reason_no_translation": {
        "id": "Tidak ada terjemahan tersedia",
        "en": "No translation available"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Duplicate
    # -------------------------------------------------------------------------
    "reason_exact_duplicate": {
        "id": "Duplikat persis",
        "en": "Exact duplicate"
    },
    "reason_same_study": {
        "id": "Studi yang sama (publikasi berbeda)",
        "en": "Same study (different publication)"
    },
    "reason_subset_data": {
        "id": "Subset dari studi lain",
        "en": "Subset of another study"
    },

    # -------------------------------------------------------------------------
    # Predefined Exclusion Reasons - Full Text
    # -------------------------------------------------------------------------
    "reason_full_text_not_found": {
        "id": "Teks lengkap tidak ditemukan",
        "en": "Full text not found"
    },
    "reason_paywall": {
        "id": "Di balik paywall",
        "en": "Behind paywall"
    },
    "reason_abstract_only": {
        "id": "Hanya abstrak tersedia",
        "en": "Abstract only available"
    },

    # -------------------------------------------------------------------------
    # Screening Status
    # -------------------------------------------------------------------------
    "status_pending": {
        "id": "Menunggu",
        "en": "Pending"
    },
    "status_included": {
        "id": "Termasuk",
        "en": "Included"
    },
    "status_excluded": {
        "id": "Dieksklusi",
        "en": "Excluded"
    },
    "status_uncertain": {
        "id": "Tidak Pasti",
        "en": "Uncertain"
    },

    # -------------------------------------------------------------------------
    # PRISMA Section
    # -------------------------------------------------------------------------
    "prisma_flow": {
        "id": "Diagram Alur PRISMA 2020",
        "en": "PRISMA 2020 Flow Diagram"
    },
    "identification": {
        "id": "Identifikasi",
        "en": "Identification"
    },
    "screening": {
        "id": "Skrining",
        "en": "Screening"
    },
    "eligibility": {
        "id": "Kelayakan",
        "en": "Eligibility"
    },
    "included": {
        "id": "Termasuk",
        "en": "Included"
    },
    "records_identified": {
        "id": "Rekaman teridentifikasi",
        "en": "Records identified"
    },
    "duplicates_removed": {
        "id": "Duplikat dihapus",
        "en": "Duplicates removed"
    },
    "records_screened": {
        "id": "Rekaman diskrining",
        "en": "Records screened"
    },
    "records_excluded": {
        "id": "Rekaman dieksklusi",
        "en": "Records excluded"
    },
    "full_text_sought": {
        "id": "Teks lengkap dicari",
        "en": "Full-text sought"
    },
    "full_text_not_retrieved": {
        "id": "Teks lengkap tidak diperoleh",
        "en": "Full-text not retrieved"
    },
    "full_text_assessed": {
        "id": "Teks lengkap dinilai",
        "en": "Full-text assessed"
    },
    "studies_included": {
        "id": "Studi termasuk dalam sintesis",
        "en": "Studies included in synthesis"
    },

    # -------------------------------------------------------------------------
    # Agent Status
    # -------------------------------------------------------------------------
    "agent_search": {
        "id": "Pencarian",
        "en": "Search"
    },
    "agent_screening": {
        "id": "Skrining",
        "en": "Screening"
    },
    "agent_acquisition": {
        "id": "Akuisisi",
        "en": "Acquisition"
    },
    "agent_quality": {
        "id": "Kualitas",
        "en": "Quality"
    },
    "agent_citation_network": {
        "id": "Jaringan Sitasi",
        "en": "Citation Network"
    },

    # -------------------------------------------------------------------------
    # Quality Assessment
    # -------------------------------------------------------------------------
    "quality_high": {
        "id": "Tinggi",
        "en": "High"
    },
    "quality_moderate": {
        "id": "Sedang",
        "en": "Moderate"
    },
    "quality_low": {
        "id": "Rendah",
        "en": "Low"
    },
    "quality_critical": {
        "id": "Kritis",
        "en": "Critical"
    },

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------
    "msg_no_papers": {
        "id": "Tidak ada paper untuk ditampilkan",
        "en": "No papers to display"
    },
    "msg_run_search_first": {
        "id": "Jalankan pencarian terlebih dahulu",
        "en": "Run search first"
    },
    "msg_ratings_ready": {
        "id": "Rating siap dihitung! Klik tombol di bawah.",
        "en": "Ratings ready to compute! Click button below."
    },
    "msg_exclusion_recorded": {
        "id": "Eksklusi berhasil dicatat",
        "en": "Exclusion recorded successfully"
    },
    "msg_inclusion_recorded": {
        "id": "Inklusi berhasil dicatat",
        "en": "Inclusion recorded successfully"
    },
}


def set_language(lang: str) -> None:
    """
    Set the current language.

    Args:
        lang: Language code ('id' or 'en')
    """
    global _current_language
    if lang in SUPPORTED_LANGUAGES:
        _current_language = lang


def get_current_language() -> str:
    """
    Get the current language code.

    Returns:
        Current language code ('id' or 'en')
    """
    return _current_language


def get_text(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    Get localized text for a given key.

    Args:
        key: Text key from TEXTS dictionary
        lang: Language code (optional, uses current language if not provided)
        **kwargs: Format arguments for string interpolation

    Returns:
        Localized text string, or the key itself if not found
    """
    language = lang or _current_language

    text_entry = TEXTS.get(key, {})
    text = text_entry.get(language, text_entry.get("en", key))

    # Apply format arguments if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return text


def get_all_texts(lang: Optional[str] = None) -> Dict[str, str]:
    """
    Get all texts for a given language.

    Args:
        lang: Language code (optional, uses current language if not provided)

    Returns:
        Dictionary of all texts for the language
    """
    language = lang or _current_language
    return {key: get_text(key, language) for key in TEXTS.keys()}
