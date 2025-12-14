# ============================================================================
# Document Ingestion
# ============================================================================
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import re
import hashlib
import json
from datetime import datetime

@dataclass
class DocumentChunk:
    """Represents a chunk of document content"""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str = ""
    parent_chunk_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = hashlib.md5(
                f"{self.content[:100]}{json.dumps(self.metadata)}".encode()
            ).hexdigest()

@dataclass
class ZIMSECDocument:
    """Represents a ZIMSEC curriculum document"""
    file_path: str
    document_type: str  # syllabus, past_paper, marking_scheme, textbook, notes
    subject: str
    education_level: str  # primary, secondary, a_level
    grade: str
    year: Optional[int] = None
    paper: Optional[str] = None  # Paper 1, Paper 2, etc.
    raw_content: str = ""
    chunks: List[DocumentChunk] = field(default_factory=list)

class DocumentProcessor:
    """Process ZIMSEC documents for RAG ingestion"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    async def process_document(self, doc: ZIMSECDocument) -> ZIMSECDocument:
        """Main entry point for document processing"""
        file_path = Path(doc.file_path)
        
        if file_path.suffix.lower() == '.pdf':
            doc.raw_content = await self._extract_pdf(file_path)
        elif file_path.suffix.lower() == '.docx':
            doc.raw_content = await self._extract_docx(file_path)
        elif file_path.suffix.lower() == '.txt':
            doc.raw_content = file_path.read_text(encoding='utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        # Clean and preprocess
        doc.raw_content = self._preprocess_content(doc.raw_content)
        
        # Create chunks based on document type
        if doc.document_type == "past_paper":
            doc.chunks = await self._chunk_past_paper(doc)
        elif doc.document_type == "marking_scheme":
            doc.chunks = await self._chunk_marking_scheme(doc)
        elif doc.document_type == "syllabus":
            doc.chunks = await self._chunk_syllabus(doc)
        else:
            doc.chunks = await self._chunk_general(doc)
        
        return doc
    
    async def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF"""
        content_parts = []
        
        with fitz.open(file_path) as pdf:
            for page_num, page in enumerate(pdf, 1):
                text = page.get_text("text")
                content_parts.append(f"\n--- Page {page_num} ---\n{text}")
                
                # Extract tables as structured data
                tables = page.find_tables()
                for table in tables:
                    df = table.to_pandas()
                    content_parts.append(f"\n[TABLE]\n{df.to_string()}\n[/TABLE]")
        
        return "\n".join(content_parts)
    
    async def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)
        content_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                # Preserve heading structure
                if para.style.name.startswith('Heading'):
                    level = para.style.name.replace('Heading ', '')
                    content_parts.append(f"\n{'#' * int(level)} {para.text}\n")
                else:
                    content_parts.append(para.text)
        
        # Extract tables
        for table in doc.tables:
            content_parts.append("\n[TABLE]")
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                content_parts.append(row_text)
            content_parts.append("[/TABLE]\n")
        
        return "\n".join(content_parts)
    
    def _preprocess_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        # Normalize bullet points
        content = re.sub(r'^[\s]*[•●○▪]\s*', '- ', content, flags=re.MULTILINE)
        
        # Clean up common OCR artifacts
        content = re.sub(r'[^\S\n]+', ' ', content)
        
        return content.strip()
    
    async def _chunk_past_paper(self, doc: ZIMSECDocument) -> List[DocumentChunk]:
        """Special chunking for past papers - preserve questions"""
        chunks = []
        base_metadata = {
            "document_type": doc.document_type,
            "subject": doc.subject,
            "education_level": doc.education_level,
            "grade": doc.grade,
            "year": doc.year,
            "paper": doc.paper,
            "source_file": doc.file_path
        }
        
        # Pattern to identify questions
        question_pattern = r'(?:Question\s*(\d+)|(\d+)\.?\s*\(a\)|^(\d+)\.\s+(?=[A-Z]))'
        
        # Split by questions
        parts = re.split(question_pattern, doc.raw_content, flags=re.MULTILINE)
        
        current_question = None
        current_content = []
        
        for part in parts:
            if part and part.strip():
                # Check if it's a question number
                if re.match(r'^\d+$', part.strip()):
                    # Save previous question
                    if current_question and current_content:
                        content = "\n".join(current_content)
                        if len(content) >= self.min_chunk_size:
                            chunks.append(DocumentChunk(
                                content=content,
                                metadata={
                                    **base_metadata,
                                    "question_number": current_question,
                                    "chunk_type": "question"
                                }
                            ))
                    current_question = part.strip()
                    current_content = [f"Question {current_question}:"]
                else:
                    current_content.append(part)
        
        # Don't forget the last question
        if current_question and current_content:
            content = "\n".join(current_content)
            if len(content) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    content=content,
                    metadata={
                        **base_metadata,
                        "question_number": current_question,
                        "chunk_type": "question"
                    }
                ))
        
        # If no questions found, fall back to general chunking
        if not chunks:
            chunks = await self._chunk_general(doc)
        
        return chunks
    
    async def _chunk_marking_scheme(self, doc: ZIMSECDocument) -> List[DocumentChunk]:
        """Chunk marking schemes - link to questions"""
        chunks = []
        base_metadata = {
            "document_type": doc.document_type,
            "subject": doc.subject,
            "education_level": doc.education_level,
            "grade": doc.grade,
            "year": doc.year,
            "paper": doc.paper,
            "source_file": doc.file_path
        }
        
        # Pattern for marking scheme entries
        pattern = r'(?:Question\s*(\d+)|^(\d+)[\.\)])'
        parts = re.split(pattern, doc.raw_content, flags=re.MULTILINE)
        
        current_q = None
        current_content = []
        
        for part in parts:
            if part and part.strip():
                if re.match(r'^\d+$', part.strip()):
                    if current_q and current_content:
                        content = "\n".join(current_content)
                        if len(content) >= self.min_chunk_size:
                            chunks.append(DocumentChunk(
                                content=content,
                                metadata={
                                    **base_metadata,
                                    "question_number": current_q,
                                    "chunk_type": "marking_scheme"
                                }
                            ))
                    current_q = part.strip()
                    current_content = [f"Marking Scheme - Question {current_q}:"]
                else:
                    current_content.append(part)
        
        if current_q and current_content:
            content = "\n".join(current_content)
            if len(content) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    content=content,
                    metadata={
                        **base_metadata,
                        "question_number": current_q,
                        "chunk_type": "marking_scheme"
                    }
                ))
        
        if not chunks:
            chunks = await self._chunk_general(doc)
        
        return chunks
    
    async def _chunk_syllabus(self, doc: ZIMSECDocument) -> List[DocumentChunk]:
        """Chunk syllabus by topics and learning objectives"""
        chunks = []
        base_metadata = {
            "document_type": doc.document_type,
            "subject": doc.subject,
            "education_level": doc.education_level,
            "grade": doc.grade,
            "source_file": doc.file_path
        }
        
        # Split by headers (topics)
        header_pattern = r'^#{1,3}\s+(.+)$|^([A-Z][A-Z\s]+)$'
        
        sections = re.split(header_pattern, doc.raw_content, flags=re.MULTILINE)
        
        current_topic = "General"
        current_content = []
        
        for section in sections:
            if section and section.strip():
                # Check if it's a header
                if re.match(r'^[A-Z][A-Z\s]{5,}$', section.strip()):
                    if current_content:
                        content = "\n".join(current_content)
                        chunks.extend(
                            self._split_into_chunks(content, {
                                **base_metadata,
                                "topic": current_topic,
                                "chunk_type": "syllabus_content"
                            })
                        )
                    current_topic = section.strip().title()
                    current_content = []
                else:
                    current_content.append(section)
        
        # Last section
        if current_content:
            content = "\n".join(current_content)
            chunks.extend(
                self._split_into_chunks(content, {
                    **base_metadata,
                    "topic": current_topic,
                    "chunk_type": "syllabus_content"
                })
            )
        
        return chunks
    
    async def _chunk_general(self, doc: ZIMSECDocument) -> List[DocumentChunk]:
        """General chunking with overlap"""
        base_metadata = {
            "document_type": doc.document_type,
            "subject": doc.subject,
            "education_level": doc.education_level,
            "grade": doc.grade,
            "source_file": doc.file_path
        }
        
        return self._split_into_chunks(doc.raw_content, base_metadata)
    
    def _split_into_chunks(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks"""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para.split())
            
            if current_length + para_length > self.chunk_size:
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(DocumentChunk(
                            content=chunk_text,
                            metadata=metadata
                        ))
                    
                    # Keep overlap
                    overlap_paras = []
                    overlap_length = 0
                    for p in reversed(current_chunk):
                        p_len = len(p.split())
                        if overlap_length + p_len <= self.chunk_overlap:
                            overlap_paras.insert(0, p)
                            overlap_length += p_len
                        else:
                            break
                    
                    current_chunk = overlap_paras
                    current_length = overlap_length
            
            current_chunk.append(para)
            current_length += para_length
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    metadata=metadata
                ))
        
        return chunks