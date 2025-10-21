import logging
import warnings
from pathlib import Path
from typing import Any
from docling.document_converter import DocumentConverter

# Suppress harmless multiprocessing warning from docling
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*leaked semaphore", category=UserWarning)

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Handles document parsing and text extraction using Docling.
    Supports PDF, DOCX, XLSX, and other common document formats.
    """
    
    def __init__(self):
        """
        Initializes the Docling document converter.
        Pre-configures for optimal text extraction and table parsing.
        """
        self.converter = DocumentConverter()
    
    
    def extract(self, file_path: str) -> dict[str, Any]:
        """
        Extracts structured content from any supported document.
        Returns dict with text, tables, metadata, and sections.
        
        Supported formats: PDF, DOCX, XLSX, PPTX, HTML, MD, and more.
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"📄 Processing document: {path.name}")
            
            result = self.converter.convert(str(path))
            doc = result.document
            
            extracted = {
                "text": doc.export_to_markdown(),
                "tables": self._extract_tables(doc),
                "metadata": self._extract_metadata(doc),
                "sections": self._extract_sections(doc),
                "filename": path.name,
                "file_type": path.suffix[1:],
            }
            
            logger.info(f"✅ Extracted {len(extracted['text'])} chars from {path.name}")
            return extracted
            
        except Exception as e:
            logger.error(f"❌ Failed to process {file_path}: {e}")
            raise
    
    
    def _extract_tables(self, doc) -> list[dict]:
        """
        Extracts all tables from the document.
        Returns list of tables with headers and rows as structured data.
        """
        tables = []
        for table in doc.tables:
            tables.append({
                "headers": table.headers if hasattr(table, 'headers') else [],
                "rows": table.data if hasattr(table, 'data') else [],
            })
        return tables
    
    
    def _extract_metadata(self, doc) -> dict:
        """
        Extracts document metadata like title, author, dates.
        Returns dict with all available metadata fields.
        """
        metadata = {}
        if hasattr(doc, 'metadata'):
            for key, value in doc.metadata.items():
                metadata[key] = str(value)
        return metadata
    
    
    def _extract_sections(self, doc) -> list[dict]:
        """
        Extracts document sections with hierarchy and headings.
        Returns list of sections with titles and content.
        """
        sections = []
        
        if hasattr(doc, 'pages'):
            for page in doc.pages:
                if hasattr(page, 'sections'):
                    for section in page.sections:
                        sections.append({
                            "title": getattr(section, 'title', ''),
                            "content": getattr(section, 'text', ''),
                            "level": getattr(section, 'level', 0),
                        })
        
        return sections
    
    
    def extract_text_only(self, file_path: str) -> str:
        """
        Quick extraction of just the text content without structure.
        Useful for simple text processing and analysis.
        """
        result = self.extract(file_path)
        return result.get("text", "")


document_processor = DocumentProcessor()

