"""
Muezza AI - Exclusion Reasons Module
=====================================
PRISMA 2020 compliant exclusion reason management with bilingual support.

Inspired by Covidence and Rayyan exclusion workflows.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import i18n if available, fallback to simple dict lookup
try:
    from utils.i18n import get_text, get_current_language
except ImportError:
    def get_text(key: str, lang: str = "id") -> str:
        return key
    def get_current_language() -> str:
        return "id"


class ExclusionCategory(Enum):
    """
    PRISMA 2020 compliant exclusion categories.

    These categories align with the PRISMA 2020 flow diagram requirements
    for documenting reasons for exclusion at each stage.
    """
    POPULATION = "population"
    INTERVENTION = "intervention"
    COMPARATOR = "comparator"
    OUTCOME = "outcome"
    STUDY_DESIGN = "study_design"
    PUBLICATION_TYPE = "publication_type"
    LANGUAGE = "language"
    DUPLICATE = "duplicate"
    FULL_TEXT_UNAVAILABLE = "full_text_unavailable"
    OTHER = "other"


# Mapping of categories to i18n text keys
CATEGORY_TEXT_KEYS: Dict[ExclusionCategory, str] = {
    ExclusionCategory.POPULATION: "cat_population",
    ExclusionCategory.INTERVENTION: "cat_intervention",
    ExclusionCategory.COMPARATOR: "cat_comparator",
    ExclusionCategory.OUTCOME: "cat_outcome",
    ExclusionCategory.STUDY_DESIGN: "cat_study_design",
    ExclusionCategory.PUBLICATION_TYPE: "cat_publication_type",
    ExclusionCategory.LANGUAGE: "cat_language",
    ExclusionCategory.DUPLICATE: "cat_duplicate",
    ExclusionCategory.FULL_TEXT_UNAVAILABLE: "cat_full_text_unavailable",
    ExclusionCategory.OTHER: "cat_other",
}


# Predefined reasons for each category (i18n text keys)
PREDEFINED_REASON_KEYS: Dict[ExclusionCategory, List[str]] = {
    ExclusionCategory.POPULATION: [
        "reason_not_human",
        "reason_wrong_age",
        "reason_wrong_disease",
        "reason_wrong_setting",
    ],
    ExclusionCategory.INTERVENTION: [
        "reason_wrong_intervention",
        "reason_no_intervention",
        "reason_combined_intervention",
    ],
    ExclusionCategory.COMPARATOR: [
        "reason_no_comparator",
        "reason_wrong_comparator",
    ],
    ExclusionCategory.OUTCOME: [
        "reason_wrong_outcome",
        "reason_no_outcome_data",
        "reason_composite_outcome",
    ],
    ExclusionCategory.STUDY_DESIGN: [
        "reason_not_empirical",
        "reason_review_only",
        "reason_case_report",
        "reason_editorial",
        "reason_protocol",
        "reason_conference_abstract",
    ],
    ExclusionCategory.PUBLICATION_TYPE: [
        "reason_letter",
        "reason_erratum",
        "reason_retracted",
        "reason_book_chapter",
    ],
    ExclusionCategory.LANGUAGE: [
        "reason_not_english",
        "reason_no_translation",
    ],
    ExclusionCategory.DUPLICATE: [
        "reason_exact_duplicate",
        "reason_same_study",
        "reason_subset_data",
    ],
    ExclusionCategory.FULL_TEXT_UNAVAILABLE: [
        "reason_full_text_not_found",
        "reason_paywall",
        "reason_abstract_only",
    ],
    ExclusionCategory.OTHER: [],
}


@dataclass
class ExclusionReason:
    """
    Represents a specific exclusion reason for a paper.

    Attributes:
        category: The PRISMA exclusion category
        reason_key: The i18n key for predefined reasons, or None for custom
        custom_text: Custom reason text if not predefined
        is_custom: Whether this is a user-defined custom reason
        created_at: Timestamp when the reason was created
    """
    category: ExclusionCategory
    reason_key: Optional[str] = None
    custom_text: Optional[str] = None
    is_custom: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_display_text(self, lang: Optional[str] = None) -> str:
        """Get the display text for this reason in the specified language."""
        if self.is_custom and self.custom_text:
            return self.custom_text
        elif self.reason_key:
            return get_text(self.reason_key, lang)
        else:
            return get_text("cat_other", lang)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "reason_key": self.reason_key,
            "custom_text": self.custom_text,
            "is_custom": self.is_custom,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExclusionReason":
        """Create from dictionary."""
        return cls(
            category=ExclusionCategory(data["category"]),
            reason_key=data.get("reason_key"),
            custom_text=data.get("custom_text"),
            is_custom=data.get("is_custom", False),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class PaperExclusion:
    """
    Records the exclusion of a specific paper.

    Attributes:
        paper_doi: DOI of the excluded paper
        paper_title: Title of the paper (for display)
        reason: The exclusion reason
        notes: Additional notes from the reviewer
        excluded_at: Timestamp of exclusion
        excluded_by: Identifier of who made the decision
    """
    paper_doi: str
    paper_title: str
    reason: ExclusionReason
    notes: str = ""
    excluded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    excluded_by: str = "user"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "paper_doi": self.paper_doi,
            "paper_title": self.paper_title,
            "reason": self.reason.to_dict(),
            "notes": self.notes,
            "excluded_at": self.excluded_at,
            "excluded_by": self.excluded_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperExclusion":
        """Create from dictionary."""
        return cls(
            paper_doi=data["paper_doi"],
            paper_title=data["paper_title"],
            reason=ExclusionReason.from_dict(data["reason"]),
            notes=data.get("notes", ""),
            excluded_at=data.get("excluded_at", datetime.now().isoformat()),
            excluded_by=data.get("excluded_by", "user"),
        )


class ExclusionReasonManager:
    """
    Manages exclusion reasons for a systematic review.

    Features:
    - Predefined PRISMA 2020 compliant categories
    - Bilingual support (Indonesian/English)
    - Custom reason creation
    - Statistics by category for PRISMA diagram
    """

    def __init__(self, language: str = "id"):
        """
        Initialize the exclusion reason manager.

        Args:
            language: Default language code ('id' or 'en')
        """
        self.language = language
        self.custom_reasons: Dict[ExclusionCategory, List[str]] = {
            cat: [] for cat in ExclusionCategory
        }
        self.exclusions: List[PaperExclusion] = []

    def get_category_label(
        self,
        category: ExclusionCategory,
        lang: Optional[str] = None
    ) -> str:
        """
        Get the display label for a category.

        Args:
            category: The exclusion category
            lang: Language code (optional)

        Returns:
            Localized category label
        """
        text_key = CATEGORY_TEXT_KEYS.get(category, "cat_other")
        return get_text(text_key, lang or self.language)

    def get_all_categories(self, lang: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get all categories with their labels.

        Returns:
            List of dicts with 'value' and 'label' keys
        """
        return [
            {
                "value": cat.value,
                "label": self.get_category_label(cat, lang),
                "enum": cat,
            }
            for cat in ExclusionCategory
        ]

    def get_predefined_reasons(
        self,
        category: ExclusionCategory,
        lang: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get predefined reasons for a category.

        Args:
            category: The exclusion category
            lang: Language code (optional)

        Returns:
            List of dicts with 'key' and 'text' for each reason
        """
        reason_keys = PREDEFINED_REASON_KEYS.get(category, [])
        language = lang or self.language

        return [
            {
                "key": key,
                "text": get_text(key, language),
                "is_custom": False,
            }
            for key in reason_keys
        ]

    def get_custom_reasons(
        self,
        category: ExclusionCategory
    ) -> List[Dict[str, str]]:
        """
        Get custom reasons for a category.

        Args:
            category: The exclusion category

        Returns:
            List of dicts with 'key' and 'text' for each custom reason
        """
        return [
            {
                "key": None,
                "text": reason_text,
                "is_custom": True,
            }
            for reason_text in self.custom_reasons.get(category, [])
        ]

    def get_all_reasons_for_category(
        self,
        category: ExclusionCategory,
        lang: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get all reasons (predefined + custom) for a category.

        Args:
            category: The exclusion category
            lang: Language code (optional)

        Returns:
            List of all available reasons
        """
        predefined = self.get_predefined_reasons(category, lang)
        custom = self.get_custom_reasons(category)
        return predefined + custom

    def add_custom_reason(
        self,
        category: ExclusionCategory,
        reason_text: str
    ) -> None:
        """
        Add a custom exclusion reason.

        Args:
            category: The exclusion category
            reason_text: The custom reason text
        """
        if category not in self.custom_reasons:
            self.custom_reasons[category] = []

        if reason_text not in self.custom_reasons[category]:
            self.custom_reasons[category].append(reason_text)

    def create_exclusion_reason(
        self,
        category: ExclusionCategory,
        reason_key: Optional[str] = None,
        custom_text: Optional[str] = None
    ) -> ExclusionReason:
        """
        Create an exclusion reason.

        Args:
            category: The exclusion category
            reason_key: i18n key for predefined reason (optional)
            custom_text: Custom reason text (optional)

        Returns:
            ExclusionReason instance
        """
        is_custom = custom_text is not None and reason_key is None

        if is_custom and custom_text:
            # Register custom reason for future use
            self.add_custom_reason(category, custom_text)

        return ExclusionReason(
            category=category,
            reason_key=reason_key,
            custom_text=custom_text,
            is_custom=is_custom,
        )

    def record_exclusion(
        self,
        paper_doi: str,
        paper_title: str,
        category: ExclusionCategory,
        reason_key: Optional[str] = None,
        custom_text: Optional[str] = None,
        notes: str = "",
        excluded_by: str = "user"
    ) -> PaperExclusion:
        """
        Record a paper exclusion.

        Args:
            paper_doi: DOI of the paper
            paper_title: Title of the paper
            category: Exclusion category
            reason_key: Predefined reason key (optional)
            custom_text: Custom reason text (optional)
            notes: Additional notes
            excluded_by: Identifier of the reviewer

        Returns:
            PaperExclusion instance
        """
        reason = self.create_exclusion_reason(category, reason_key, custom_text)

        exclusion = PaperExclusion(
            paper_doi=paper_doi,
            paper_title=paper_title,
            reason=reason,
            notes=notes,
            excluded_by=excluded_by,
        )

        self.exclusions.append(exclusion)
        return exclusion

    def get_exclusion_statistics(
        self,
        lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get exclusion statistics by category.

        Returns:
            Dict with category counts and labels for PRISMA diagram
        """
        language = lang or self.language
        stats: Dict[ExclusionCategory, int] = {cat: 0 for cat in ExclusionCategory}

        for exclusion in self.exclusions:
            stats[exclusion.reason.category] += 1

        # Convert to display format
        result = {
            "total": len(self.exclusions),
            "by_category": [],
        }

        for category, count in stats.items():
            if count > 0:
                result["by_category"].append({
                    "category": category.value,
                    "label": self.get_category_label(category, language),
                    "count": count,
                })

        # Sort by count (descending)
        result["by_category"].sort(key=lambda x: x["count"], reverse=True)

        return result

    def get_exclusions_for_category(
        self,
        category: ExclusionCategory
    ) -> List[PaperExclusion]:
        """
        Get all exclusions for a specific category.

        Args:
            category: The exclusion category

        Returns:
            List of PaperExclusion instances
        """
        return [
            exc for exc in self.exclusions
            if exc.reason.category == category
        ]

    def get_exclusion_for_paper(
        self,
        paper_doi: str
    ) -> Optional[PaperExclusion]:
        """
        Get exclusion record for a specific paper.

        Args:
            paper_doi: DOI of the paper

        Returns:
            PaperExclusion if found, None otherwise
        """
        for exclusion in self.exclusions:
            if exclusion.paper_doi == paper_doi:
                return exclusion
        return None

    def remove_exclusion(self, paper_doi: str) -> bool:
        """
        Remove an exclusion record (e.g., if decision is reversed).

        Args:
            paper_doi: DOI of the paper

        Returns:
            True if removed, False if not found
        """
        for i, exclusion in enumerate(self.exclusions):
            if exclusion.paper_doi == paper_doi:
                self.exclusions.pop(i)
                return True
        return False

    def export_for_prisma(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """
        Export exclusion data formatted for PRISMA diagram.

        Returns:
            Dict with exclusion counts suitable for PRISMA flow
        """
        stats = self.get_exclusion_statistics(lang)

        # Format for PRISMA narrative
        prisma_data = {
            "total_excluded": stats["total"],
            "reasons": [],
        }

        for cat_stat in stats["by_category"]:
            prisma_data["reasons"].append(
                f"{cat_stat['label']} (n={cat_stat['count']})"
            )

        return prisma_data

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state to dictionary."""
        return {
            "language": self.language,
            "custom_reasons": {
                cat.value: reasons
                for cat, reasons in self.custom_reasons.items()
            },
            "exclusions": [exc.to_dict() for exc in self.exclusions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExclusionReasonManager":
        """Restore manager state from dictionary."""
        manager = cls(language=data.get("language", "id"))

        # Restore custom reasons
        for cat_value, reasons in data.get("custom_reasons", {}).items():
            try:
                category = ExclusionCategory(cat_value)
                manager.custom_reasons[category] = reasons
            except ValueError:
                pass

        # Restore exclusions
        for exc_data in data.get("exclusions", []):
            try:
                exclusion = PaperExclusion.from_dict(exc_data)
                manager.exclusions.append(exclusion)
            except (KeyError, ValueError):
                pass

        return manager


# Convenience function for quick exclusion
def create_quick_exclusion(
    category: str,
    reason_text: str,
    paper_doi: str,
    paper_title: str
) -> PaperExclusion:
    """
    Quickly create a paper exclusion with a custom reason.

    Args:
        category: Category value string
        reason_text: The reason text
        paper_doi: DOI of the paper
        paper_title: Title of the paper

    Returns:
        PaperExclusion instance
    """
    try:
        cat_enum = ExclusionCategory(category)
    except ValueError:
        cat_enum = ExclusionCategory.OTHER

    reason = ExclusionReason(
        category=cat_enum,
        custom_text=reason_text,
        is_custom=True,
    )

    return PaperExclusion(
        paper_doi=paper_doi,
        paper_title=paper_title,
        reason=reason,
    )
