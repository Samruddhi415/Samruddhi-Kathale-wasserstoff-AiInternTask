import os
import pytesseract
from PIL import Image
import PyPDF2
import cv2
import numpy as np
from docx import Document
from typing import Dict, List, Tuple
import logging
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
class DocumentProcessor:
    def __init__(self):
        pass
    
    def process_document(self, file_path: str, doc_id: str) -> Dict:
        """Process a document and extract text with metadata"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                return self._process_pdf(file_path, doc_id)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return self._process_image(file_path, doc_id)
            elif file_extension == '.docx':
                return self._process_docx(file_path, doc_id)
            elif file_extension == '.txt':
                return self._process_txt(file_path, doc_id)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {str(e)}")
            return {"doc_id": doc_id, "content": [], "error": str(e)}
    
    def _process_pdf(self, file_path: str, doc_id: str) -> Dict:
        """Extract text from PDF, with OCR fallback for scanned pages"""
        content = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        text = text.strip()
                    else:
                        text = ""
                    
                    if len(text) < 50:  # Likely a scanned page
                        # Convert PDF page to image and OCR
                        text = self._ocr_pdf_page(file_path, page_num - 1)
                    
                    if text:
                        # Split into paragraphs
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        for para_num, paragraph in enumerate(paragraphs, 1):
                            content.append({
                                "page": page_num,
                                "paragraph": para_num,
                                "text": paragraph,
                                "citation": f"Page {page_num}, Para {para_num}"
                            })
            
            return {"doc_id": doc_id, "content": content, "total_pages": len(pdf_reader.pages)}
            
        except Exception as e:
            logger.error(f"Error processing PDF {doc_id}: {str(e)}")
            return {"doc_id": doc_id, "content": [], "error": str(e)}
    
    def _process_image(self, file_path: str, doc_id: str) -> Dict:
        """Extract text from image using OCR"""
        try:
            # Preprocess image for better OCR
            image = cv2.imread(file_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get better OCR results
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR
            text = pytesseract.image_to_string(thresh)
            
            content = []
            if text.strip():
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                for para_num, paragraph in enumerate(paragraphs, 1):
                    content.append({
                        "page": 1,
                        "paragraph": para_num,
                        "text": paragraph,
                        "citation": f"Page 1, Para {para_num}"
                    })
            
            return {"doc_id": doc_id, "content": content, "total_pages": 1}
            
        except Exception as e:
            logger.error(f"Error processing image {doc_id}: {str(e)}")
            return {"doc_id": doc_id, "content": [], "error": str(e)}
    
    def _process_docx(self, file_path: str, doc_id: str) -> Dict:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            content = []
            
            for para_num, paragraph in enumerate(doc.paragraphs, 1):
                text = paragraph.text.strip()
                if text:
                    content.append({
                        "page": 1,  # DOCX doesn't have clear page breaks
                        "paragraph": para_num,
                        "text": text,
                        "citation": f"Para {para_num}"
                    })
            
            return {"doc_id": doc_id, "content": content, "total_pages": 1}
            
        except Exception as e:
            logger.error(f"Error processing DOCX {doc_id}: {str(e)}")
            return {"doc_id": doc_id, "content": [], "error": str(e)}
    
    def _process_txt(self, file_path: str, doc_id: str) -> Dict:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            content = []
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            for para_num, paragraph in enumerate(paragraphs, 1):
                content.append({
                    "page": 1,
                    "paragraph": para_num,
                    "text": paragraph,
                    "citation": f"Para {para_num}"
                })
            
            return {"doc_id": doc_id, "content": content, "total_pages": 1}
            
        except Exception as e:
            logger.error(f"Error processing TXT {doc_id}: {str(e)}")
            return {"doc_id": doc_id, "content": [], "error": str(e)}
    
    def _ocr_pdf_page(self, pdf_path: str, page_num: int) -> str:
        """
        OCR a specific PDF page using pdf2image and pytesseract.

        Args:
            pdf_path (str): Path to the PDF file.
            page_num (int): Page number to OCR (0-indexed).

        Returns:
            str: Extracted text from the page, or empty string on failure.
        """
        try:
            # Convert the specific page to an image (page_num is zero-based)
            images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
            if not images:
                logger.error(f"No images extracted from page {page_num} of {pdf_path}")
                return ""
            
            page_image = images[0]

            # OCR the image using pytesseract
            text = pytesseract.image_to_string(page_image)

            return text

        except Exception as e:
            logger.error(f"Error OCRing PDF page {page_num} in {pdf_path}: {str(e)}")
            return ""
