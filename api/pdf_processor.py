"""
PDF Processor
=============
Multi-backend PDF processing with text extraction and section detection.

Backends (in order of preference):
1. PyMuPDF (fitz) - Fast, accurate, good for most PDFs
2. pdfplumber - Good for table extraction and simple layouts
3. Basic text extraction fallback
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Check available backends
PYMUPDF_AVAILABLE = False
PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.debug("PyMuPDF not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    logger.debug("pdfplumber not available")


@dataclass
class PDFContent:
    """Represents extracted PDF content."""
    raw_text: str = ""
    markdown: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    page_count: int = 0
    extraction_method: str = ""
    tables: List[List[List[str]]] = field(default_factory=list)
    figures_count: int = 0
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'raw_text': self.raw_text,
            'markdown': self.markdown,
            'sections': self.sections,
            'metadata': self.metadata,
            'page_count': self.page_count,
            'extraction_method': self.extraction_method,
            'tables_count': len(self.tables),
            'figures_count': self.figures_count,
            'references_count': len(self.references),
        }


class PDFProcessor:
    """
    Multi-backend PDF processor.

    Automatically selects the best available backend and provides
    consistent extraction interface.
    """

    # Common academic paper section headers
    SECTION_PATTERNS = [
        (r'(?i)^(?:1\.?\s*)?(?:abstract|summary)', 'abstract'),
        (r'(?i)^(?:2\.?\s*)?(?:introduction|background)', 'introduction'),
        (r'(?i)^(?:\d\.?\s*)?(?:literature\s*review|related\s*work|background)', 'literature_review'),
        (r'(?i)^(?:\d\.?\s*)?(?:method(?:s|ology)?|materials?\s*(?:and|&)\s*methods?)', 'methods'),
        (r'(?i)^(?:\d\.?\s*)?(?:result(?:s)?|findings?)', 'results'),
        (r'(?i)^(?:\d\.?\s*)?(?:discussion)', 'discussion'),
        (r'(?i)^(?:\d\.?\s*)?(?:conclusion(?:s)?|summary)', 'conclusions'),
        (r'(?i)^(?:\d\.?\s*)?(?:reference(?:s)?|bibliography|works?\s*cited)', 'references'),
        (r'(?i)^(?:\d\.?\s*)?(?:appendix|appendices|supplementary)', 'appendix'),
        (r'(?i)^(?:\d\.?\s*)?(?:acknowledgement(?:s)?)', 'acknowledgements'),
    ]

    def __init__(self, prefer_backend: str = "auto"):
        """
        Initialize PDF processor.

        Args:
            prefer_backend: Preferred backend ("pymupdf", "pdfplumber", "auto")
        """
        self.prefer_backend = prefer_backend
        self._select_backend()

    def _select_backend(self):
        """Select the best available backend."""
        if self.prefer_backend == "pymupdf" and PYMUPDF_AVAILABLE:
            self.backend = "pymupdf"
        elif self.prefer_backend == "pdfplumber" and PDFPLUMBER_AVAILABLE:
            self.backend = "pdfplumber"
        elif self.prefer_backend == "auto":
            if PYMUPDF_AVAILABLE:
                self.backend = "pymupdf"
            elif PDFPLUMBER_AVAILABLE:
                self.backend = "pdfplumber"
            else:
                self.backend = "none"
        else:
            self.backend = "none"

        logger.info(f"PDF processor using backend: {self.backend}")

    def process_pdf(self, pdf_path: str) -> Optional[PDFContent]:
        """
        Process a PDF file and extract content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFContent object or None if processing fails
        """
        path = Path(pdf_path)

        if not path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None

        if not path.suffix.lower() == '.pdf':
            logger.error(f"Not a PDF file: {pdf_path}")
            return None

        try:
            if self.backend == "pymupdf":
                return self._process_with_pymupdf(path)
            elif self.backend == "pdfplumber":
                return self._process_with_pdfplumber(path)
            else:
                logger.error("No PDF backend available. Install pymupdf or pdfplumber.")
                return None

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return None

    def process_pdf_bytes(self, pdf_bytes: bytes) -> Optional[PDFContent]:
        """
        Process PDF from bytes.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            PDFContent object or None
        """
        try:
            if self.backend == "pymupdf":
                return self._process_bytes_pymupdf(pdf_bytes)
            elif self.backend == "pdfplumber":
                # pdfplumber needs a file, so write to temp
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    f.write(pdf_bytes)
                    temp_path = f.name

                result = self._process_with_pdfplumber(Path(temp_path))

                # Clean up
                Path(temp_path).unlink(missing_ok=True)
                return result
            else:
                logger.error("No PDF backend available")
                return None

        except Exception as e:
            logger.error(f"Error processing PDF bytes: {e}")
            return None

    def _process_with_pymupdf(self, path: Path) -> PDFContent:
        """Process PDF using PyMuPDF."""
        content = PDFContent(extraction_method="pymupdf")

        doc = fitz.open(str(path))
        content.page_count = len(doc)

        # Extract metadata
        metadata = doc.metadata
        if metadata:
            content.metadata = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'keywords': metadata.get('keywords', ''),
                'creator': metadata.get('creator', ''),
            }

        # Extract text from all pages
        full_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            full_text.append(text)

            # Count figures (images)
            content.figures_count += len(page.get_images())

        content.raw_text = '\n'.join(full_text)
        doc.close()

        # Convert to markdown and extract sections
        content.markdown = self._text_to_markdown(content.raw_text)
        content.sections = self._extract_sections(content.raw_text)
        content.references = self._extract_references(content.raw_text)

        return content

    def _process_bytes_pymupdf(self, pdf_bytes: bytes) -> PDFContent:
        """Process PDF bytes using PyMuPDF."""
        content = PDFContent(extraction_method="pymupdf")

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        content.page_count = len(doc)

        # Extract metadata
        metadata = doc.metadata
        if metadata:
            content.metadata = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'keywords': metadata.get('keywords', ''),
            }

        # Extract text from all pages
        full_text = []
        for page in doc:
            text = page.get_text("text")
            full_text.append(text)
            content.figures_count += len(page.get_images())

        content.raw_text = '\n'.join(full_text)
        doc.close()

        content.markdown = self._text_to_markdown(content.raw_text)
        content.sections = self._extract_sections(content.raw_text)
        content.references = self._extract_references(content.raw_text)

        return content

    def _process_with_pdfplumber(self, path: Path) -> PDFContent:
        """Process PDF using pdfplumber."""
        content = PDFContent(extraction_method="pdfplumber")

        with pdfplumber.open(str(path)) as pdf:
            content.page_count = len(pdf.pages)

            # Extract metadata
            if pdf.metadata:
                content.metadata = {
                    'title': pdf.metadata.get('Title', ''),
                    'author': pdf.metadata.get('Author', ''),
                    'subject': pdf.metadata.get('Subject', ''),
                    'keywords': pdf.metadata.get('Keywords', ''),
                }

            # Extract text and tables from all pages
            full_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)

                # Extract tables
                tables = page.extract_tables()
                if tables:
                    content.tables.extend(tables)

            content.raw_text = '\n'.join(full_text)

        content.markdown = self._text_to_markdown(content.raw_text)
        content.sections = self._extract_sections(content.raw_text)
        content.references = self._extract_references(content.raw_text)

        return content

    def _text_to_markdown(self, text: str) -> str:
        """Convert raw text to basic markdown."""
        lines = text.split('\n')
        markdown_lines = []
        in_list = False

        for line in lines:
            line = line.strip()

            if not line:
                if in_list:
                    in_list = False
                markdown_lines.append('')
                continue

            # Check for section headers
            is_header = False
            for pattern, section_name in self.SECTION_PATTERNS:
                if re.match(pattern, line):
                    markdown_lines.append(f"\n## {line}\n")
                    is_header = True
                    break

            if is_header:
                continue

            # Check for numbered list items
            if re.match(r'^\d+[.)]\s+', line):
                markdown_lines.append(line)
                in_list = True
            # Check for bullet points
            elif re.match(r'^[-*]\s+', line):
                markdown_lines.append(line)
                in_list = True
            else:
                markdown_lines.append(line)

        return '\n'.join(markdown_lines)

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract common academic paper sections."""
        sections = {}
        lines = text.split('\n')

        current_section = None
        current_content = []

        for line in lines:
            # Check if line is a section header
            found_section = None
            for pattern, section_name in self.SECTION_PATTERNS:
                if re.match(pattern, line.strip()):
                    found_section = section_name
                    break

            if found_section:
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()

                current_section = found_section
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _extract_references(self, text: str) -> List[str]:
        """Extract individual references from the references section."""
        references = []

        # Find references section
        ref_match = re.search(
            r'(?i)(?:references?|bibliography|works?\s*cited)\s*\n(.+)',
            text,
            re.DOTALL
        )

        if not ref_match:
            return references

        ref_text = ref_match.group(1)

        # Common reference patterns
        patterns = [
            # Numbered references [1], [2], etc.
            r'\[\d+\]\s*([^\[\]]+?)(?=\[\d+\]|$)',
            # Numbered references 1., 2., etc.
            r'^\d+\.\s*(.+?)(?=^\d+\.|$)',
            # Author-year style (Smith et al., 2020)
            r'([A-Z][^.]+\(\d{4}\)[^.]+\.)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, ref_text, re.MULTILINE)
            if matches:
                references = [m.strip() for m in matches if len(m.strip()) > 20]
                break

        # Fallback: split by common separators
        if not references:
            # Split by double newlines or numbered items
            parts = re.split(r'\n\s*\n|\n\s*\d+[.)]\s+', ref_text)
            references = [p.strip() for p in parts if len(p.strip()) > 30]

        return references[:100]  # Limit to 100 references

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Public method to extract sections from already-extracted text.

        Args:
            text: Raw text or markdown content

        Returns:
            Dictionary of section_name -> content
        """
        return self._extract_sections(text)

    def get_backend_info(self) -> Dict[str, bool]:
        """Get information about available backends."""
        return {
            'pymupdf_available': PYMUPDF_AVAILABLE,
            'pdfplumber_available': PDFPLUMBER_AVAILABLE,
            'current_backend': self.backend,
        }


# Convenience functions
def process_pdf(pdf_path: str) -> Optional[Dict]:
    """
    Quick function to process a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with extracted content or None
    """
    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)
    return result.to_dict() if result else None


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Quick function to extract raw text from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text or empty string
    """
    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)
    return result.raw_text if result else ""


def extract_sections_from_pdf(pdf_path: str) -> Dict[str, str]:
    """
    Quick function to extract sections from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary of sections
    """
    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)
    return result.sections if result else {}


if __name__ == "__main__":
    # Test the processor
    processor = PDFProcessor()
    print(f"Backend info: {processor.get_backend_info()}")

    # Test with a sample PDF if available
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\nProcessing: {pdf_path}")

        result = processor.process_pdf(pdf_path)

        if result:
            print(f"Pages: {result.page_count}")
            print(f"Extraction method: {result.extraction_method}")
            print(f"Metadata: {result.metadata}")
            print(f"\nSections found: {list(result.sections.keys())}")
            print(f"Tables found: {len(result.tables)}")
            print(f"Figures found: {result.figures_count}")
            print(f"References found: {len(result.references)}")

            if result.sections.get('abstract'):
                print(f"\nAbstract preview: {result.sections['abstract'][:200]}...")
        else:
            print("Failed to process PDF")
    else:
        print("\nUsage: python pdf_processor.py <pdf_path>")
