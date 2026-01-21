"""
Logic Continuity Agent
======================
Analyzes complete research report (Bab 1-5) to ensure logical flow
and consistency - the "red thread" (benang merah) of the research.

Checks:
- Research question alignment across chapters
- Methodology-results consistency
- Conclusions supported by findings
- Terminology consistency
- Smooth transitions between chapters
- Argument coherence
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IssueLevel(str, Enum):
    """Severity level for identified issues."""
    CRITICAL = "critical"      # Major logical breaks
    WARNING = "warning"        # Inconsistencies that need attention
    SUGGESTION = "suggestion"  # Minor improvements
    INFO = "info"              # Informational notes


@dataclass
class ContinuityIssue:
    """A logical continuity issue found in the report."""
    level: IssueLevel
    chapter: str
    location: str
    description: str
    suggestion: str
    related_chapters: List[str] = field(default_factory=list)


@dataclass
class ContinuityReport:
    """Complete continuity analysis report."""
    overall_score: float  # 0-100
    is_coherent: bool
    issues: List[ContinuityIssue]
    chapter_scores: Dict[str, float]
    research_question_alignment: float
    methodology_results_match: float
    conclusion_support_score: float
    terminology_consistency: float
    transition_quality: float
    summary: str
    recommendations: List[str]
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LogicContinuityAgent:
    """
    Agent that ensures logical continuity across research report chapters.

    Uses both rule-based analysis and LLM for comprehensive evaluation.
    """

    def __init__(
        self,
        anthropic_api_key: str = None,
        use_llm: bool = True
    ):
        """
        Initialize the agent.

        Args:
            anthropic_api_key: API key for Claude (optional)
            use_llm: Whether to use LLM for analysis
        """
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_llm = use_llm and bool(self.api_key)
        self.llm_client = None

        if self.use_llm:
            self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM client."""
        try:
            from anthropic import Anthropic
            self.llm_client = Anthropic(api_key=self.api_key)
            logger.info("LLM client initialized for continuity analysis")
        except ImportError:
            logger.warning("Anthropic package not installed, using rule-based analysis only")
            self.use_llm = False

    def analyze_report(
        self,
        chapters: Dict[str, str],
        research_question: str = None
    ) -> ContinuityReport:
        """
        Analyze complete report for logical continuity.

        Args:
            chapters: Dictionary mapping chapter names to content
            research_question: The main research question

        Returns:
            ContinuityReport with analysis results
        """
        issues: List[ContinuityIssue] = []
        chapter_scores: Dict[str, float] = {}

        # Extract research question if not provided
        if not research_question:
            research_question = self._extract_research_question(chapters)

        # 1. Check research question alignment
        rq_alignment, rq_issues = self._check_rq_alignment(chapters, research_question)
        issues.extend(rq_issues)

        # 2. Check methodology-results consistency
        method_results_match, mr_issues = self._check_methodology_results(chapters)
        issues.extend(mr_issues)

        # 3. Check conclusion support
        conclusion_support, cs_issues = self._check_conclusion_support(chapters)
        issues.extend(cs_issues)

        # 4. Check terminology consistency
        terminology_score, term_issues = self._check_terminology(chapters)
        issues.extend(term_issues)

        # 5. Check transitions between chapters
        transition_score, trans_issues = self._check_transitions(chapters)
        issues.extend(trans_issues)

        # 6. Individual chapter analysis
        for chapter_name, content in chapters.items():
            score, chapter_issues = self._analyze_chapter(chapter_name, content, research_question)
            chapter_scores[chapter_name] = score
            issues.extend(chapter_issues)

        # 7. LLM-based deep analysis (if available)
        if self.use_llm:
            llm_issues = self._llm_deep_analysis(chapters, research_question)
            issues.extend(llm_issues)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            rq_alignment,
            method_results_match,
            conclusion_support,
            terminology_score,
            transition_score,
            chapter_scores
        )

        # Determine coherence
        is_coherent = overall_score >= 70 and not any(
            i.level == IssueLevel.CRITICAL for i in issues
        )

        # Generate summary and recommendations
        summary = self._generate_summary(overall_score, issues)
        recommendations = self._generate_recommendations(issues)

        return ContinuityReport(
            overall_score=overall_score,
            is_coherent=is_coherent,
            issues=issues,
            chapter_scores=chapter_scores,
            research_question_alignment=rq_alignment,
            methodology_results_match=method_results_match,
            conclusion_support_score=conclusion_support,
            terminology_consistency=terminology_score,
            transition_quality=transition_score,
            summary=summary,
            recommendations=recommendations
        )

    def _extract_research_question(self, chapters: Dict[str, str]) -> str:
        """Extract research question from Chapter 1."""
        bab1_keys = ['bab_1', 'bab1', 'pendahuluan', 'introduction', 'chapter_1']

        for key in bab1_keys:
            for chapter_key in chapters:
                if key in chapter_key.lower():
                    content = chapters[chapter_key]

                    # Look for research question patterns
                    patterns = [
                        r'(?:rumusan masalah|research question|pertanyaan penelitian)[:\s]*["\']?([^"\'?\n]+\?)',
                        r'(?:penelitian ini bertujuan|this study aims)[:\s]*([^.\n]+)',
                        r'(?:bagaimana|how|what|apa)[^?\n]+\?',
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            return match.group(1) if match.lastindex else match.group(0)

        return ""

    def _check_rq_alignment(
        self,
        chapters: Dict[str, str],
        research_question: str
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Check if all chapters align with research question."""
        issues = []

        if not research_question:
            issues.append(ContinuityIssue(
                level=IssueLevel.WARNING,
                chapter="Bab 1",
                location="Rumusan Masalah",
                description="Pertanyaan penelitian tidak ditemukan secara eksplisit",
                suggestion="Tambahkan rumusan masalah yang jelas dan terukur"
            ))
            return 50.0, issues

        # Extract key concepts from research question
        rq_words = set(re.findall(r'\b\w{4,}\b', research_question.lower()))
        rq_words -= {'yang', 'dalam', 'untuk', 'dengan', 'dari', 'pada', 'adalah', 'atau'}

        alignment_scores = []

        chapter_requirements = {
            'bab_1': ('Pendahuluan', 0.8, 'mengidentifikasi masalah penelitian'),
            'bab_2': ('Tinjauan Pustaka', 0.6, 'mengulas konsep terkait'),
            'bab_3': ('Metodologi', 0.5, 'menjelaskan cara menjawab pertanyaan'),
            'bab_4': ('Hasil', 0.9, 'menyajikan temuan yang menjawab pertanyaan'),
            'bab_5': ('Kesimpulan', 0.95, 'menjawab pertanyaan penelitian secara langsung'),
        }

        for key_pattern, (chapter_name, min_threshold, requirement) in chapter_requirements.items():
            for chapter_key, content in chapters.items():
                if key_pattern in chapter_key.lower():
                    content_words = set(re.findall(r'\b\w{4,}\b', content.lower()))
                    overlap = len(rq_words & content_words) / len(rq_words) if rq_words else 0

                    alignment_scores.append(overlap)

                    if overlap < min_threshold:
                        issues.append(ContinuityIssue(
                            level=IssueLevel.WARNING if overlap < min_threshold * 0.5 else IssueLevel.SUGGESTION,
                            chapter=chapter_name,
                            location="Keseluruhan bab",
                            description=f"Keterkaitan dengan pertanyaan penelitian rendah ({overlap:.0%})",
                            suggestion=f"{chapter_name} harus {requirement}",
                            related_chapters=["Bab 1"]
                        ))

        return (sum(alignment_scores) / len(alignment_scores) * 100) if alignment_scores else 50.0, issues

    def _check_methodology_results(
        self,
        chapters: Dict[str, str]
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Check consistency between methodology and results."""
        issues = []

        method_content = ""
        results_content = ""

        for key, content in chapters.items():
            if 'bab_3' in key.lower() or 'metodologi' in key.lower():
                method_content = content
            elif 'bab_4' in key.lower() or 'hasil' in key.lower():
                results_content = content

        if not method_content or not results_content:
            return 70.0, issues

        # Check for methodology elements mentioned in results
        method_elements = {
            'analisis tematik': r'\b(tema|tematik|thematic)\b',
            'PRISMA': r'\bPRISMA\b',
            'JBI': r'\bJBI\b',
            'penilaian kualitas': r'\b(kualitas|quality)\s+(assessment|penilaian)\b',
            'screening': r'\bscreening\b',
            'kriteria inklusi': r'\b(inklusi|inclusion)\b',
            'kriteria eksklusi': r'\b(eksklusi|exclusion)\b',
        }

        methodology_mentioned = []
        for element, pattern in method_elements.items():
            if re.search(pattern, method_content, re.IGNORECASE):
                methodology_mentioned.append(element)

        results_mentioned = []
        for element, pattern in method_elements.items():
            if re.search(pattern, results_content, re.IGNORECASE):
                results_mentioned.append(element)

        # Check alignment
        method_set = set(methodology_mentioned)
        results_set = set(results_mentioned)

        if method_set and not method_set & results_set:
            issues.append(ContinuityIssue(
                level=IssueLevel.CRITICAL,
                chapter="Bab 4",
                location="Hasil",
                description="Metode yang dijelaskan di Bab 3 tidak tercermin di Bab 4",
                suggestion=f"Pastikan hasil mencerminkan metode: {', '.join(methodology_mentioned)}",
                related_chapters=["Bab 3"]
            ))
            return 40.0, issues

        missing_in_results = method_set - results_set
        if missing_in_results:
            issues.append(ContinuityIssue(
                level=IssueLevel.WARNING,
                chapter="Bab 4",
                location="Hasil",
                description=f"Beberapa elemen metodologi tidak dilaporkan: {', '.join(missing_in_results)}",
                suggestion="Tambahkan hasil dari setiap tahap metodologi yang digunakan",
                related_chapters=["Bab 3"]
            ))

        overlap_ratio = len(method_set & results_set) / len(method_set) if method_set else 1.0
        return overlap_ratio * 100, issues

    def _check_conclusion_support(
        self,
        chapters: Dict[str, str]
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Check if conclusions are supported by findings."""
        issues = []

        results_content = ""
        conclusion_content = ""

        for key, content in chapters.items():
            if 'bab_4' in key.lower() or 'hasil' in key.lower():
                results_content = content
            elif 'bab_5' in key.lower() or 'kesimpulan' in key.lower():
                conclusion_content = content

        if not results_content or not conclusion_content:
            return 70.0, issues

        # Extract key findings from Bab 4
        findings_patterns = [
            r'(?:temuan|finding|hasil)[:\s]*([^.]+\.)',
            r'(?:menunjukkan|shows?|indicates?)[:\s]*([^.]+\.)',
            r'(?:ditemukan|found)[:\s]*([^.]+\.)',
        ]

        findings = []
        for pattern in findings_patterns:
            findings.extend(re.findall(pattern, results_content, re.IGNORECASE))

        # Extract conclusion claims from Bab 5
        conclusion_patterns = [
            r'(?:kesimpulan|conclusion)[:\s]*([^.]+\.)',
            r'(?:dapat disimpulkan|concluded)[:\s]*([^.]+\.)',
            r'(?:penelitian ini menunjukkan|this study shows)[:\s]*([^.]+\.)',
        ]

        conclusions = []
        for pattern in conclusion_patterns:
            conclusions.extend(re.findall(pattern, conclusion_content, re.IGNORECASE))

        if not conclusions:
            issues.append(ContinuityIssue(
                level=IssueLevel.WARNING,
                chapter="Bab 5",
                location="Kesimpulan",
                description="Pernyataan kesimpulan tidak ditemukan secara eksplisit",
                suggestion="Gunakan frasa seperti 'Dapat disimpulkan bahwa...' atau 'Kesimpulan penelitian ini adalah...'"
            ))
            return 60.0, issues

        # Check if conclusion keywords appear in findings
        findings_text = " ".join(findings).lower()
        conclusions_text = " ".join(conclusions).lower()

        # Extract significant words from conclusions
        conclusion_words = set(re.findall(r'\b\w{5,}\b', conclusions_text))
        conclusion_words -= {'bahwa', 'adalah', 'dapat', 'untuk', 'dengan', 'dalam', 'penelitian'}

        findings_words = set(re.findall(r'\b\w{5,}\b', findings_text))

        support_ratio = len(conclusion_words & findings_words) / len(conclusion_words) if conclusion_words else 0.5

        if support_ratio < 0.3:
            issues.append(ContinuityIssue(
                level=IssueLevel.CRITICAL,
                chapter="Bab 5",
                location="Kesimpulan",
                description="Kesimpulan tidak didukung oleh temuan di Bab 4",
                suggestion="Kesimpulan harus merangkum dan merefleksikan temuan utama dari Bab 4",
                related_chapters=["Bab 4"]
            ))
        elif support_ratio < 0.5:
            issues.append(ContinuityIssue(
                level=IssueLevel.WARNING,
                chapter="Bab 5",
                location="Kesimpulan",
                description="Beberapa kesimpulan tidak terhubung dengan temuan",
                suggestion="Tinjau kembali apakah setiap klaim kesimpulan didukung bukti dari Bab 4",
                related_chapters=["Bab 4"]
            ))

        return support_ratio * 100, issues

    def _check_terminology(
        self,
        chapters: Dict[str, str]
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Check terminology consistency across chapters."""
        issues = []

        # Common terminology pairs (should use one consistently)
        terminology_pairs = [
            (r'\bAI\b', r'\bartificial intelligence\b', 'AI/Artificial Intelligence'),
            (r'\bML\b', r'\bmachine learning\b', 'ML/Machine Learning'),
            (r'\bSLR\b', r'\bsystematic literature review\b', 'SLR/Systematic Literature Review'),
            (r'\bkecerdasan buatan\b', r'\bAI\b', 'Kecerdasan Buatan/AI'),
            (r'\bpembelajaran mesin\b', r'\bML\b', 'Pembelajaran Mesin/ML'),
            (r'\btinjauan sistematis\b', r'\bSLR\b', 'Tinjauan Sistematis/SLR'),
        ]

        all_content = " ".join(chapters.values())
        inconsistencies = []

        for term1, term2, pair_name in terminology_pairs:
            count1 = len(re.findall(term1, all_content, re.IGNORECASE))
            count2 = len(re.findall(term2, all_content, re.IGNORECASE))

            if count1 > 0 and count2 > 0:
                # Both terms used - check if inconsistent across chapters
                per_chapter = {}
                for chapter_name, content in chapters.items():
                    c1 = len(re.findall(term1, content, re.IGNORECASE))
                    c2 = len(re.findall(term2, content, re.IGNORECASE))
                    if c1 > 0 or c2 > 0:
                        per_chapter[chapter_name] = (c1, c2)

                # If both forms used in multiple chapters, flag it
                if len(per_chapter) > 1:
                    inconsistencies.append((pair_name, per_chapter))

        if inconsistencies:
            for pair_name, per_chapter in inconsistencies[:3]:  # Max 3 issues
                issues.append(ContinuityIssue(
                    level=IssueLevel.SUGGESTION,
                    chapter="Seluruh dokumen",
                    location="Terminologi",
                    description=f"Inkonsistensi penggunaan istilah: {pair_name}",
                    suggestion="Pilih satu bentuk dan gunakan secara konsisten di seluruh dokumen"
                ))

        score = 100 - (len(inconsistencies) * 10)
        return max(50, score), issues

    def _check_transitions(
        self,
        chapters: Dict[str, str]
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Check quality of transitions between chapters."""
        issues = []

        # Order chapters
        chapter_order = ['bab_1', 'bab_2', 'bab_3', 'bab_4', 'bab_5']
        ordered_chapters = []

        for pattern in chapter_order:
            for key in chapters:
                if pattern in key.lower():
                    ordered_chapters.append((key, chapters[key]))
                    break

        if len(ordered_chapters) < 2:
            return 70.0, issues

        transition_scores = []

        # Check transitions between consecutive chapters
        for i in range(len(ordered_chapters) - 1):
            current_name, current_content = ordered_chapters[i]
            next_name, next_content = ordered_chapters[i + 1]

            # Get end of current chapter and start of next
            current_end = current_content[-500:] if len(current_content) > 500 else current_content
            next_start = next_content[:500] if len(next_content) > 500 else next_content

            # Look for transition phrases
            transition_phrases = [
                r'\b(selanjutnya|selanjut|berikut|next|following)\b',
                r'\b(berdasarkan|based on|sesuai dengan)\b',
                r'\b(sebagaimana|as mentioned|seperti yang)\b',
                r'\b(bab sebelumnya|previous chapter)\b',
            ]

            has_transition = any(
                re.search(phrase, next_start, re.IGNORECASE)
                for phrase in transition_phrases
            )

            # Check conceptual overlap
            current_words = set(re.findall(r'\b\w{5,}\b', current_end.lower()))
            next_words = set(re.findall(r'\b\w{5,}\b', next_start.lower()))

            overlap = len(current_words & next_words)
            transition_score = 70 if has_transition else 50
            transition_score += min(30, overlap * 3)

            transition_scores.append(transition_score)

            if transition_score < 60:
                issues.append(ContinuityIssue(
                    level=IssueLevel.SUGGESTION,
                    chapter=next_name,
                    location="Awal bab",
                    description=f"Transisi dari bab sebelumnya kurang smooth",
                    suggestion="Tambahkan kalimat penghubung yang merujuk pada bab sebelumnya",
                    related_chapters=[current_name]
                ))

        return sum(transition_scores) / len(transition_scores) if transition_scores else 70.0, issues

    def _analyze_chapter(
        self,
        chapter_name: str,
        content: str,
        research_question: str
    ) -> Tuple[float, List[ContinuityIssue]]:
        """Analyze individual chapter quality."""
        issues = []
        score = 80

        # Check chapter length
        word_count = len(content.split())
        min_lengths = {
            'bab_1': 500,
            'bab_2': 800,
            'bab_3': 600,
            'bab_4': 1000,
            'bab_5': 400,
        }

        for pattern, min_len in min_lengths.items():
            if pattern in chapter_name.lower():
                if word_count < min_len * 0.5:
                    issues.append(ContinuityIssue(
                        level=IssueLevel.WARNING,
                        chapter=chapter_name,
                        location="Keseluruhan bab",
                        description=f"Bab terlalu pendek ({word_count} kata, minimal {min_len})",
                        suggestion="Perkaya konten dengan lebih banyak detail dan penjelasan"
                    ))
                    score -= 20
                elif word_count < min_len:
                    score -= 10

        # Check for required sections
        required_sections = {
            'bab_1': ['latar belakang', 'rumusan masalah', 'tujuan'],
            'bab_2': ['landasan teori', 'kajian', 'kerangka'],
            'bab_3': ['desain', 'kriteria', 'analisis'],
            'bab_4': ['karakteristik', 'kualitas', 'temuan'],
            'bab_5': ['kesimpulan', 'saran', 'rekomendasi'],
        }

        for pattern, sections in required_sections.items():
            if pattern in chapter_name.lower():
                content_lower = content.lower()
                missing = [s for s in sections if s not in content_lower]

                if missing:
                    issues.append(ContinuityIssue(
                        level=IssueLevel.WARNING if len(missing) > 1 else IssueLevel.SUGGESTION,
                        chapter=chapter_name,
                        location="Struktur bab",
                        description=f"Bagian yang tidak ditemukan: {', '.join(missing)}",
                        suggestion="Pertimbangkan untuk menambahkan bagian-bagian standar"
                    ))
                    score -= len(missing) * 5

        return max(50, score), issues

    def _llm_deep_analysis(
        self,
        chapters: Dict[str, str],
        research_question: str
    ) -> List[ContinuityIssue]:
        """Use LLM for deeper continuity analysis."""
        if not self.llm_client:
            return []

        issues = []

        # Prepare condensed version of all chapters
        chapter_summaries = []
        for name, content in chapters.items():
            # Take first 1000 chars of each chapter
            summary = content[:1000] if len(content) > 1000 else content
            chapter_summaries.append(f"=== {name.upper()} ===\n{summary}\n")

        full_text = "\n".join(chapter_summaries)

        prompt = f"""Sebagai reviewer penelitian ilmiah, analisis keterkaitan logis (benang merah) dari laporan penelitian berikut.

Pertanyaan Penelitian: {research_question}

{full_text}

Identifikasi masalah kontinuitas logis dalam format berikut (maksimal 5 masalah):
1. [LEVEL: CRITICAL/WARNING/SUGGESTION] Bab X: Deskripsi masalah | Saran perbaikan
2. ...

Fokus pada:
- Apakah setiap bab mendukung jawaban pertanyaan penelitian?
- Apakah ada inkonsistensi antara metodologi dan hasil?
- Apakah kesimpulan didukung temuan?
- Apakah ada gap logika antar bab?

Output dalam Bahasa Indonesia."""

        try:
            response = self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse LLM response
            lines = response_text.strip().split('\n')
            for line in lines:
                if '[LEVEL:' in line.upper():
                    try:
                        # Extract level
                        level_match = re.search(r'\[LEVEL:\s*(CRITICAL|WARNING|SUGGESTION)\]', line, re.IGNORECASE)
                        level = IssueLevel(level_match.group(1).lower()) if level_match else IssueLevel.SUGGESTION

                        # Extract chapter
                        chapter_match = re.search(r'Bab\s*(\d+|[IVX]+)', line, re.IGNORECASE)
                        chapter = chapter_match.group(0) if chapter_match else "Umum"

                        # Split description and suggestion
                        parts = line.split('|')
                        description = re.sub(r'\[LEVEL:[^\]]+\]', '', parts[0]).strip()
                        description = re.sub(r'Bab\s*\d+:', '', description).strip()
                        suggestion = parts[1].strip() if len(parts) > 1 else "Tinjau kembali bagian ini"

                        issues.append(ContinuityIssue(
                            level=level,
                            chapter=chapter,
                            location="LLM Analysis",
                            description=description[:200],
                            suggestion=suggestion[:200]
                        ))
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        return issues[:5]  # Max 5 issues from LLM

    def _calculate_overall_score(
        self,
        rq_alignment: float,
        method_results: float,
        conclusion_support: float,
        terminology: float,
        transitions: float,
        chapter_scores: Dict[str, float]
    ) -> float:
        """Calculate overall continuity score."""
        weights = {
            'rq_alignment': 0.25,
            'method_results': 0.20,
            'conclusion_support': 0.25,
            'terminology': 0.10,
            'transitions': 0.10,
            'chapters': 0.10,
        }

        chapter_avg = sum(chapter_scores.values()) / len(chapter_scores) if chapter_scores else 70

        score = (
            rq_alignment * weights['rq_alignment'] +
            method_results * weights['method_results'] +
            conclusion_support * weights['conclusion_support'] +
            terminology * weights['terminology'] +
            transitions * weights['transitions'] +
            chapter_avg * weights['chapters']
        )

        return round(score, 1)

    def _generate_summary(self, score: float, issues: List[ContinuityIssue]) -> str:
        """Generate summary of analysis."""
        critical_count = sum(1 for i in issues if i.level == IssueLevel.CRITICAL)
        warning_count = sum(1 for i in issues if i.level == IssueLevel.WARNING)

        if score >= 85:
            quality = "sangat baik"
        elif score >= 70:
            quality = "baik"
        elif score >= 55:
            quality = "cukup"
        else:
            quality = "perlu perbaikan"

        summary = f"""Analisis Kontinuitas Logis

Skor Keseluruhan: {score}/100 ({quality})

Temuan:
- {critical_count} masalah kritis
- {warning_count} peringatan
- {len(issues) - critical_count - warning_count} saran perbaikan

"""

        if critical_count > 0:
            summary += "PERHATIAN: Terdapat masalah kritis yang harus diperbaiki sebelum finalisasi.\n"

        if score >= 70:
            summary += "Benang merah penelitian terjalin dengan baik antar bab."
        else:
            summary += "Beberapa bagian memerlukan penguatan keterkaitan dengan pertanyaan penelitian."

        return summary

    def _generate_recommendations(self, issues: List[ContinuityIssue]) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        # Group by level
        critical = [i for i in issues if i.level == IssueLevel.CRITICAL]
        warnings = [i for i in issues if i.level == IssueLevel.WARNING]
        suggestions = [i for i in issues if i.level == IssueLevel.SUGGESTION]

        if critical:
            recommendations.append("PRIORITAS TINGGI:")
            for issue in critical[:3]:
                recommendations.append(f"  - {issue.chapter}: {issue.suggestion}")

        if warnings:
            recommendations.append("\nPRIORITAS SEDANG:")
            for issue in warnings[:3]:
                recommendations.append(f"  - {issue.chapter}: {issue.suggestion}")

        if suggestions:
            recommendations.append("\nOPSIONAL:")
            for issue in suggestions[:2]:
                recommendations.append(f"  - {issue.chapter}: {issue.suggestion}")

        return recommendations

    def format_report(self, report: ContinuityReport) -> str:
        """Format continuity report as readable text."""
        lines = [
            "=" * 60,
            "LAPORAN ANALISIS KONTINUITAS LOGIS",
            "=" * 60,
            "",
            report.summary,
            "",
            "-" * 60,
            "SKOR PER ASPEK:",
            "-" * 60,
            f"  Keterkaitan dengan Pertanyaan Penelitian: {report.research_question_alignment:.0f}%",
            f"  Konsistensi Metodologi-Hasil: {report.methodology_results_match:.0f}%",
            f"  Dukungan Bukti untuk Kesimpulan: {report.conclusion_support_score:.0f}%",
            f"  Konsistensi Terminologi: {report.terminology_consistency:.0f}%",
            f"  Kualitas Transisi Antar Bab: {report.transition_quality:.0f}%",
            "",
        ]

        if report.chapter_scores:
            lines.append("SKOR PER BAB:")
            for chapter, score in report.chapter_scores.items():
                lines.append(f"  {chapter}: {score:.0f}%")
            lines.append("")

        if report.issues:
            lines.append("-" * 60)
            lines.append("DETAIL TEMUAN:")
            lines.append("-" * 60)

            for i, issue in enumerate(report.issues, 1):
                level_icon = {
                    IssueLevel.CRITICAL: "[!!!]",
                    IssueLevel.WARNING: "[!]",
                    IssueLevel.SUGGESTION: "[i]",
                    IssueLevel.INFO: "[.]"
                }
                lines.append(f"\n{i}. {level_icon[issue.level]} {issue.chapter} - {issue.location}")
                lines.append(f"   Masalah: {issue.description}")
                lines.append(f"   Saran: {issue.suggestion}")
                if issue.related_chapters:
                    lines.append(f"   Terkait: {', '.join(issue.related_chapters)}")

        if report.recommendations:
            lines.append("")
            lines.append("-" * 60)
            lines.append("REKOMENDASI PERBAIKAN:")
            lines.append("-" * 60)
            lines.extend(report.recommendations)

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Dianalisis pada: {report.analyzed_at}")
        lines.append("=" * 60)

        return "\n".join(lines)


def check_report_continuity(
    chapters: Dict[str, str],
    research_question: str = None,
    api_key: str = None
) -> ContinuityReport:
    """
    Convenience function to check report continuity.

    Args:
        chapters: Dictionary of chapter contents
        research_question: Main research question
        api_key: Anthropic API key for LLM analysis

    Returns:
        ContinuityReport
    """
    agent = LogicContinuityAgent(anthropic_api_key=api_key)
    return agent.analyze_report(chapters, research_question)
