import io
import os
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process various document formats and extract text content"""
    
    def __init__(self):
        self.supported_types = {
            'text/plain': self._process_text,
            'application/json': self._process_json,
            'text/markdown': self._process_text,
            'text/csv': self._process_text,
            'application/pdf': self._process_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._process_docx,
            'application/msword': self._process_doc,
        }
    
    async def process_file(
        self, 
        file_content: bytes, 
        filename: str, 
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process uploaded file and extract text content"""
        try:
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                # Try to detect from content
                mime_type = self._detect_mime_type(file_content, filename)
            
            logger.info(f"Processing file: {filename}, MIME type: {mime_type}")
            
            # Get appropriate processor
            processor = self.supported_types.get(mime_type)
            if not processor:
                # Try plain text as fallback
                processor = self._process_text
            
            # Extract text content
            text_content = await processor(file_content, filename)
            
            # Generate document ID
            document_id = str(uuid.uuid4())
            
            # Prepare document metadata
            metadata = {
                'filename': filename,
                'mime_type': mime_type,
                'uploaded_at': datetime.now().isoformat(),
                'file_size': len(file_content),
                'category': category or 'general'
            }
            
            return {
                'document_id': document_id,
                'name': filename,
                'content': text_content,
                'category': category or 'general',
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {str(e)}")
            raise ValueError(f"Failed to process file: {str(e)}")
    
    def _detect_mime_type(self, content: bytes, filename: str) -> str:
        """Detect MIME type from content"""
        # Check file extension
        ext = os.path.splitext(filename)[1].lower()
        
        ext_map = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
        }
        
        return ext_map.get(ext, 'text/plain')
    
    async def _process_text(self, content: bytes, filename: str) -> str:
        """Process plain text files"""
        try:
            # Try UTF-8 first
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1
            return content.decode('latin-1', errors='ignore')
    
    async def _process_json(self, content: bytes, filename: str) -> str:
        """Process JSON files"""
        import json
        try:
            data = json.loads(content.decode('utf-8'))
            # Convert JSON to readable text
            return json.dumps(data, indent=2)
        except Exception as e:
            logger.warning(f"Failed to parse JSON, treating as text: {e}")
            return await self._process_text(content, filename)
    
    async def _process_pdf(self, content: bytes, filename: str) -> str:
        """Process PDF files"""
        try:
            import PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return '\n\n'.join(text_content)
        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            raise ValueError("PDF processing not available. PyPDF2 required.")
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    async def _process_docx(self, content: bytes, filename: str) -> str:
        """Process DOCX files"""
        try:
            import docx
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            return '\n\n'.join(text_content)
        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            raise ValueError("DOCX processing not available. python-docx required.")
        except Exception as e:
            logger.error(f"Failed to process DOCX: {e}")
            raise ValueError(f"Failed to process DOCX: {str(e)}")
    
    async def _process_doc(self, content: bytes, filename: str) -> str:
        """Process DOC files (older Word format)"""
        # DOC format is complex, requires antiword or similar
        # For now, attempt to read as text
        logger.warning("DOC format support is limited. Consider converting to DOCX.")
        return await self._process_text(content, filename)
    
    def is_supported(self, filename: str) -> bool:
        """Check if file type is supported"""
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            ext = os.path.splitext(filename)[1].lower()
            return ext in ['.txt', '.json', '.md', '.csv', '.pdf', '.docx', '.doc']
        return mime_type in self.supported_types
