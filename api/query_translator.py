"""
Muezza AI - Query Translator
============================
Auto-translate Indonesian research queries to English for Scopus search.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class QueryTranslator:
    """
    Translates Indonesian research queries to English.

    Features:
    - Language detection (ID/EN)
    - Academic term mapping
    - Keyword extraction and translation
    - Query preservation for mixed language
    """

    # Indonesian stopwords
    ID_STOPWORDS = {
        'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'dengan', 'pada', 'adalah',
        'ini', 'itu', 'atau', 'dalam', 'akan', 'oleh', 'sebuah', 'sebagai',
        'dapat', 'telah', 'sudah', 'juga', 'serta', 'bahwa', 'seperti', 'antara',
        'tentang', 'terhadap', 'melalui', 'secara', 'bagaimana', 'apakah', 'apa',
        'mengapa', 'kapan', 'dimana', 'siapa', 'berapa', 'adakah', 'bisakah',
        'ketika', 'saat', 'bila', 'jika', 'maka', 'karena', 'sehingga', 'agar',
        'supaya', 'namun', 'tetapi', 'melainkan', 'sedangkan', 'padahal',
        'tersebut', 'setiap', 'semua', 'beberapa', 'banyak', 'sedikit',
        'sangat', 'lebih', 'paling', 'cukup', 'hampir', 'hanya', 'masih',
        'sudah', 'belum', 'tidak', 'bukan', 'tanpa', 'selain', 'kecuali',
    }

    # Comprehensive Indonesian to English academic term mappings
    TERM_MAPPINGS = {
        # Research methodology
        'penelitian': 'research',
        'studi': 'study',
        'analisis': 'analysis',
        'evaluasi': 'evaluation',
        'pengembangan': 'development',
        'implementasi': 'implementation',
        'metode': 'method',
        'metodologi': 'methodology',
        'pendekatan': 'approach',
        'strategi': 'strategy',
        'teknik': 'technique',
        'prosedur': 'procedure',
        'eksperimen': 'experiment',
        'survei': 'survey',
        'observasi': 'observation',
        'wawancara': 'interview',
        'kuesioner': 'questionnaire',
        'sampel': 'sample',
        'populasi': 'population',
        'data': 'data',
        'hasil': 'result',
        'temuan': 'finding',
        'kesimpulan': 'conclusion',
        'rekomendasi': 'recommendation',
        'hipotesis': 'hypothesis',
        'variabel': 'variable',
        'parameter': 'parameter',
        'indikator': 'indicator',
        'validitas': 'validity',
        'reliabilitas': 'reliability',
        'signifikan': 'significant',
        'korelasi': 'correlation',
        'regresi': 'regression',
        'statistik': 'statistics',
        'kuantitatif': 'quantitative',
        'kualitatif': 'qualitative',

        # AI & Machine Learning
        'pembelajaran mesin': 'machine learning',
        'kecerdasan buatan': 'artificial intelligence',
        'pembelajaran mendalam': 'deep learning',
        'jaringan saraf': 'neural network',
        'jaringan saraf tiruan': 'artificial neural network',
        'pengenalan pola': 'pattern recognition',
        'pemrosesan bahasa alami': 'natural language processing',
        'visi komputer': 'computer vision',
        'pengolahan citra': 'image processing',
        'penambangan data': 'data mining',
        'analisis data': 'data analysis',
        'ilmu data': 'data science',
        'algoritma': 'algorithm',
        'model': 'model',
        'prediksi': 'prediction',
        'klasifikasi': 'classification',
        'klasterisasi': 'clustering',
        'segmentasi': 'segmentation',
        'deteksi': 'detection',
        'pengenalan': 'recognition',
        'ekstraksi': 'extraction',
        'optimasi': 'optimization',
        'pelatihan': 'training',
        'pengujian': 'testing',
        'validasi': 'validation',
        'akurasi': 'accuracy',
        'presisi': 'precision',
        'sensitivitas': 'sensitivity',
        'spesifisitas': 'specificity',

        # Medical & Health
        'kesehatan': 'health',
        'medis': 'medical',
        'kedokteran': 'medicine',
        'klinis': 'clinical',
        'diagnosis': 'diagnosis',
        'diagnostik': 'diagnostic',
        'pengobatan': 'treatment',
        'terapi': 'therapy',
        'pencegahan': 'prevention',
        'penyakit': 'disease',
        'kanker': 'cancer',
        'tumor': 'tumor',
        'diabetes': 'diabetes',
        'jantung': 'heart',
        'kardiovaskular': 'cardiovascular',
        'stroke': 'stroke',
        'hipertensi': 'hypertension',
        'infeksi': 'infection',
        'virus': 'virus',
        'bakteri': 'bacteria',
        'pasien': 'patient',
        'rumah sakit': 'hospital',
        'dokter': 'doctor',
        'perawat': 'nurse',
        'obat': 'drug',
        'farmasi': 'pharmacy',
        'radiologi': 'radiology',
        'patologi': 'pathology',
        'epidemiologi': 'epidemiology',
        'gejala': 'symptom',
        'sindrom': 'syndrome',
        'prognosis': 'prognosis',
        'mortalitas': 'mortality',
        'morbiditas': 'morbidity',

        # Medical Imaging
        'pencitraan medis': 'medical imaging',
        'citra medis': 'medical image',
        'rontgen': 'x-ray',
        'sinar-x': 'x-ray',
        'ct scan': 'ct scan',
        'mri': 'mri',
        'usg': 'ultrasound',
        'ultrasonografi': 'ultrasound',
        'mammografi': 'mammography',
        'histopatologi': 'histopathology',

        # Education
        'pendidikan': 'education',
        'pembelajaran': 'learning',
        'pengajaran': 'teaching',
        'kurikulum': 'curriculum',
        'siswa': 'student',
        'mahasiswa': 'student',
        'guru': 'teacher',
        'dosen': 'lecturer',
        'sekolah': 'school',
        'universitas': 'university',
        'perguruan tinggi': 'higher education',
        'prestasi': 'achievement',
        'kompetensi': 'competency',
        'literasi': 'literacy',
        'numerasi': 'numeracy',
        'e-learning': 'e-learning',
        'daring': 'online',
        'luring': 'offline',

        # Technology
        'teknologi': 'technology',
        'sistem': 'system',
        'aplikasi': 'application',
        'perangkat lunak': 'software',
        'perangkat keras': 'hardware',
        'komputer': 'computer',
        'internet': 'internet',
        'jaringan': 'network',
        'basis data': 'database',
        'cloud': 'cloud',
        'keamanan': 'security',
        'siber': 'cyber',
        'digital': 'digital',
        'otomasi': 'automation',
        'robotik': 'robotics',
        'sensor': 'sensor',
        'iot': 'internet of things',

        # Business & Economics
        'bisnis': 'business',
        'ekonomi': 'economics',
        'manajemen': 'management',
        'pemasaran': 'marketing',
        'keuangan': 'finance',
        'investasi': 'investment',
        'produktivitas': 'productivity',
        'efisiensi': 'efficiency',
        'efektivitas': 'effectiveness',
        'kinerja': 'performance',
        'kualitas': 'quality',
        'inovasi': 'innovation',
        'wirausaha': 'entrepreneurship',
        'umkm': 'sme',
        'industri': 'industry',
        'manufaktur': 'manufacturing',

        # Environment
        'lingkungan': 'environment',
        'ekologi': 'ecology',
        'keberlanjutan': 'sustainability',
        'berkelanjutan': 'sustainable',
        'perubahan iklim': 'climate change',
        'pemanasan global': 'global warming',
        'polusi': 'pollution',
        'pencemaran': 'pollution',
        'limbah': 'waste',
        'daur ulang': 'recycling',
        'energi terbarukan': 'renewable energy',
        'konservasi': 'conservation',
        'biodiversitas': 'biodiversity',

        # Social Sciences
        'sosial': 'social',
        'masyarakat': 'society',
        'komunitas': 'community',
        'budaya': 'culture',
        'perilaku': 'behavior',
        'psikologi': 'psychology',
        'sosiologi': 'sociology',
        'antropologi': 'anthropology',
        'demografi': 'demography',
        'gender': 'gender',
        'kemiskinan': 'poverty',
        'kesejahteraan': 'welfare',
        'kebijakan': 'policy',
        'pemerintah': 'government',
        'publik': 'public',

        # Agriculture
        'pertanian': 'agriculture',
        'tanaman': 'plant',
        'panen': 'harvest',
        'pupuk': 'fertilizer',
        'pestisida': 'pesticide',
        'irigasi': 'irrigation',
        'peternakan': 'livestock',
        'perikanan': 'fisheries',
        'pangan': 'food',
        'ketahanan pangan': 'food security',

        # Common adjectives/descriptors
        'efektif': 'effective',
        'efisien': 'efficient',
        'optimal': 'optimal',
        'akurat': 'accurate',
        'cepat': 'fast',
        'lambat': 'slow',
        'tinggi': 'high',
        'rendah': 'low',
        'besar': 'large',
        'kecil': 'small',
        'baru': 'new',
        'lama': 'old',
        'modern': 'modern',
        'tradisional': 'traditional',
        'otomatis': 'automatic',
        'manual': 'manual',

        # Question words often in research questions
        'pengaruh': 'effect',
        'dampak': 'impact',
        'hubungan': 'relationship',
        'perbandingan': 'comparison',
        'perbedaan': 'difference',
        'persamaan': 'similarity',
        'peningkatan': 'improvement',
        'penurunan': 'decrease',
        'faktor': 'factor',
        'penyebab': 'cause',
        'akibat': 'effect',
        'solusi': 'solution',
        'tantangan': 'challenge',
        'hambatan': 'barrier',
        'peluang': 'opportunity',
    }

    # Indonesian language indicators
    ID_INDICATORS = [
        'bagaimana', 'apakah', 'mengapa', 'apa', 'seberapa',
        'dengan', 'untuk', 'dalam', 'pada', 'terhadap',
        'yang', 'dan', 'atau', 'dari', 'ke',
        'adalah', 'merupakan', 'yaitu', 'yakni',
    ]

    def __init__(self):
        """Initialize translator."""
        # Create reverse mapping for multi-word terms (longer first)
        self._sorted_mappings = sorted(
            self.TERM_MAPPINGS.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

    def detect_language(self, text: str) -> str:
        """
        Detect if text is Indonesian or English.

        Args:
            text: Input text

        Returns:
            'id' for Indonesian, 'en' for English
        """
        if not text:
            return 'en'

        text_lower = text.lower()
        words = set(re.findall(r'\b[a-zA-Z]+\b', text_lower))

        # Count Indonesian indicators
        id_score = sum(1 for ind in self.ID_INDICATORS if ind in text_lower)

        # Count Indonesian terms
        id_terms = sum(1 for term in self.TERM_MAPPINGS.keys() if term in text_lower)

        # Count Indonesian stopwords
        id_stopwords = len(words & self.ID_STOPWORDS)

        total_id = id_score + id_terms + id_stopwords

        # If significant Indonesian detected
        if total_id >= 2:
            return 'id'

        return 'en'

    def translate_query(self, query: str) -> Tuple[str, bool]:
        """
        Translate Indonesian query to English.

        Args:
            query: Input query (Indonesian or English)

        Returns:
            Tuple of (translated_query, was_translated)
        """
        if not query:
            return query, False

        language = self.detect_language(query)

        if language == 'en':
            logger.info(f"Query detected as English, no translation needed")
            return query, False

        logger.info(f"Query detected as Indonesian, translating...")

        translated = query.lower()

        # Apply term mappings (longer terms first to avoid partial matches)
        for id_term, en_term in self._sorted_mappings:
            if id_term in translated:
                translated = translated.replace(id_term, en_term)
                logger.debug(f"Translated: '{id_term}' -> '{en_term}'")

        # Remove Indonesian stopwords that weren't translated
        words = translated.split()
        filtered_words = [w for w in words if w.lower() not in self.ID_STOPWORDS or w in self.TERM_MAPPINGS.values()]
        translated = ' '.join(filtered_words)

        # Clean up
        translated = re.sub(r'\s+', ' ', translated).strip()

        logger.info(f"Translation: '{query}' -> '{translated}'")
        return translated, True

    def translate_keywords(self, keywords: List[str]) -> List[str]:
        """
        Translate list of keywords.

        Args:
            keywords: List of Indonesian keywords

        Returns:
            List of English keywords
        """
        translated = []
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if kw_lower in self.TERM_MAPPINGS:
                translated.append(self.TERM_MAPPINGS[kw_lower])
            elif kw_lower not in self.ID_STOPWORDS:
                # Keep unknown terms (might be proper nouns or already English)
                translated.append(kw)
        return translated

    def get_term_translation(self, term: str) -> Optional[str]:
        """Get translation for a single term."""
        return self.TERM_MAPPINGS.get(term.lower().strip())


# Global instance
_translator = QueryTranslator()


def get_translator() -> QueryTranslator:
    """Get global translator instance."""
    return _translator


def translate_research_query(query: str) -> Tuple[str, bool]:
    """
    Convenience function to translate research query.

    Args:
        query: Research question in Indonesian or English

    Returns:
        Tuple of (translated_query, was_translated)
    """
    return _translator.translate_query(query)


def detect_query_language(query: str) -> str:
    """
    Detect language of query.

    Returns:
        'id' for Indonesian, 'en' for English
    """
    return _translator.detect_language(query)
