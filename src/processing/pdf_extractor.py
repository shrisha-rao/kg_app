# src/processing/pdf_extractor.py
import logging
import io
from typing import Optional, Tuple, List
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from src.config import settings

logger = logging.getLogger(__name__)
"""
This implementation provides:

    Text extraction using PyMuPDF's efficient text extraction

    OCR fallback for scanned PDFs with low text content

    Metadata extraction from PDF documents

    Image extraction from PDF files

    Basic table extraction (with room for improvement using specialized libraries)

    Error handling and logging

    Configurable OCR with language support

The implementation includes:

    Main text extraction with fallback to OCR when needed

    Metadata extraction for PDF documents

    Image extraction capability

    Basic table detection (could be enhanced with specialized libraries)

    Global instance and public function for easy use

    Configurable behavior through environment variables

You can enable OCR for scanned PDFs by setting PDF_USE_OCR=true in your environment variables. The OCR language can be configured with PDF_OCR_LANGUAGE (e.g., "eng" for English, "deu" for German, etc.).

This implementation provides a robust foundation for PDF text extraction that can handle both text-based and scanned PDFs.
"""


class PDFExtractor:
    """Service for extracting text and metadata from PDF files"""

    def __init__(self):
        self.use_ocr = settings.pdf_use_ocr  # Whether to use OCR for scanned PDFs
        self.ocr_language = settings.pdf_ocr_language  # Language for OCR

    def extract_text_from_pdf(self, pdf_content: bytes) -> Tuple[str, dict]:
        """
        Extract text from a PDF file
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            # Open the PDF from bytes
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            text_parts = []
            metadata = self._extract_metadata(pdf_document)

            # Extract text from each page
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                page_text = page.get_text()

                # If text extraction returns very little content and OCR is enabled, try OCR
                if self.use_ocr and len(page_text.strip()) < 50:
                    logger.info(
                        f"Using OCR for page {page_num + 1} (low text content)"
                    )
                    page_text = self._extract_text_with_ocr(page)

                text_parts.append(page_text)

            pdf_document.close()

            full_text = "\n".join(text_parts)
            logger.info(
                f"Successfully extracted text from PDF ({len(full_text)} characters)"
            )

            return full_text, metadata

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

    def _extract_metadata(self, pdf_document) -> dict:
        """Extract metadata from the PDF document"""
        try:
            metadata = pdf_document.metadata
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": len(pdf_document)
            }
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return {}

    def _extract_text_with_ocr(self, page) -> str:
        """Extract text from a PDF page using OCR"""
        try:
            # Render page as an image
            mat = fitz.Matrix(2, 2)  # High resolution matrix
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))

            # Use pytesseract to extract text
            text = pytesseract.image_to_string(image, lang=self.ocr_language)

            return text

        except Exception as e:
            logger.error(f"Error in OCR extraction: {e}")
            # Fall back to regular text extraction
            return page.get_text()

    def extract_images(self,
                       pdf_content: bytes,
                       max_images: int = 10) -> List[bytes]:
        """
        Extract images from a PDF file
        
        Args:
            pdf_content: PDF file content as bytes
            max_images: Maximum number of images to extract
            
        Returns:
            List of image bytes
        """
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            images = []

            for page_num in range(len(pdf_document)):
                if len(images) >= max_images:
                    break

                page = pdf_document.load_page(page_num)
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    if len(images) >= max_images:
                        break

                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    images.append(image_bytes)

            pdf_document.close()
            logger.info(f"Extracted {len(images)} images from PDF")

            return images

        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return []

    def extract_tables(self, pdf_content: bytes) -> List[List[List[str]]]:
        """
        Extract tables from a PDF file (basic implementation)
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of tables (each table is a 2D list of strings)
        """
        # This is a basic implementation. For production use, consider using
        # specialized libraries like camelot, tabula, or pdfplumber
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            tables = []

            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text = page.get_text()

                # Simple table detection based on patterns
                # This is a placeholder - real table extraction would be more complex
                lines = text.split('\n')
                table_candidates = []
                current_table = []

                for line in lines:
                    # Check if line has table-like structure (multiple columns)
                    if '\t' in line or '  ' in line:  # Tabs or multiple spaces
                        # Clean up the line and split into cells
                        cells = [
                            cell.strip() for cell in line.split('\t')
                            if cell.strip()
                        ]
                        if len(cells) > 1:  # Likely a table row
                            current_table.append(cells)
                        elif current_table:  # End of table
                            if len(current_table) > 1:  # At least 2 rows
                                table_candidates.append(current_table)
                            current_table = []
                    elif current_table:  # End of table
                        if len(current_table) > 1:  # At least 2 rows
                            table_candidates.append(current_table)
                        current_table = []

                # Add the last table if it exists
                if current_table and len(current_table) > 1:
                    table_candidates.append(current_table)

                tables.extend(table_candidates)

            pdf_document.close()
            logger.info(f"Extracted {len(tables)} tables from PDF")

            return tables

        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return []


# Global instance
pdf_extractor = PDFExtractor()


# Public function to use the extractor
def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from a PDF file (simplified interface for backward compatibility)
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
    """
    text, _ = pdf_extractor.extract_text_from_pdf(pdf_content)
    return text
