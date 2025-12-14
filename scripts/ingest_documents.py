# ============================================================================
# Document Ingestion Script
# ============================================================================
"""
Script to ingest ZIMSEC documents into the vector store.

Usage:
    python scripts/ingest_documents.py --dir ./documents/syllabi --type syllabus
    python scripts/ingest_documents.py --dir ./documents/past_papers --type past_paper
    python scripts/ingest_documents.py --file ./documents/math_form3.pdf --type textbook --subject Mathematics --grade "Form 3"
"""

import asyncio
import argparse
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.rag.document_processor import DocumentProcessor, ZIMSECDocument
from app.services.rag.vector_store import VectorStore

settings = get_settings()

# Subject code mapping
SUBJECT_CODES = {
    "mathematics": "4008",
    "english": "1122",
    "physics": "4023",
    "chemistry": "4024",
    "biology": "4025",
    "geography": "4022",
    "history": "2167",
    "accounting": "4043",
    "commerce": "4044",
    "shona": "3159",
}

def parse_filename(filename: str) -> dict:
    """Parse document metadata from filename"""
    # Expected format: subject_level_grade_year_paper.pdf
    # Example: mathematics_secondary_form4_2023_paper1.pdf
    
    parts = filename.lower().replace('.pdf', '').replace('.docx', '').split('_')
    
    metadata = {
        "subject": parts[0] if len(parts) > 0 else "unknown",
        "education_level": parts[1] if len(parts) > 1 else "secondary",
        "grade": parts[2] if len(parts) > 2 else "Form 3",
        "year": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None,
        "paper": parts[4] if len(parts) > 4 else None,
    }
    
    return metadata

async def ingest_file(
    file_path: Path,
    doc_type: str,
    subject: str = None,
    grade: str = None,
    education_level: str = None,
    year: int = None,
    paper: str = None
):
    """Ingest a single document"""
    print(f"Processing: {file_path.name}")
    
    # Parse metadata from filename if not provided
    if not all([subject, grade]):
        parsed = parse_filename(file_path.name)
        subject = subject or parsed["subject"]
        grade = grade or parsed["grade"]
        education_level = education_level or parsed["education_level"]
        year = year or parsed["year"]
        paper = paper or parsed["paper"]
    
    # Create document object
    doc = ZIMSECDocument(
        file_path=str(file_path),
        document_type=doc_type,
        subject=subject,
        education_level=education_level or "secondary",
        grade=grade,
        year=year,
        paper=paper
    )
    
    # Process document
    processor = DocumentProcessor(
        chunk_size=500,
        chunk_overlap=50,
        min_chunk_size=100
    )
    
    processed_doc = await processor.process_document(doc)
    print(f"  - Created {len(processed_doc.chunks)} chunks")
    
    # Store in vector database
    vector_store = VectorStore(settings)
    await vector_store.initialize_collections()
    
    collection_map = {
        "syllabus": "zimsec_syllabi",
        "past_paper": "zimsec_past_papers",
        "marking_scheme": "zimsec_marking_schemes",
        "textbook": "textbooks",
        "teacher_notes": "teacher_notes"
    }
    
    collection = collection_map.get(doc_type, "zimsec_past_papers")
    
    num_stored = await vector_store.add_chunks(processed_doc.chunks, collection)
    print(f"  - Stored {num_stored} chunks in '{collection}'")
    
    return num_stored

async def ingest_directory(
    directory: Path,
    doc_type: str,
    subject: str = None,
    education_level: str = None
):
    """Ingest all documents in a directory"""
    total_chunks = 0
    files_processed = 0
    
    for file_path in directory.glob("**/*"):
        if file_path.suffix.lower() in ['.pdf', '.docx', '.txt']:
            try:
                chunks = await ingest_file(
                    file_path=file_path,
                    doc_type=doc_type,
                    subject=subject,
                    education_level=education_level
                )
                total_chunks += chunks
                files_processed += 1
            except Exception as e:
                print(f"  - ERROR: {e}")
    
    return files_processed, total_chunks

def main():
    parser = argparse.ArgumentParser(description="Ingest ZIMSEC documents")
    parser.add_argument("--file", type=str, help="Single file to ingest")
    parser.add_argument("--dir", type=str, help="Directory to ingest")
    parser.add_argument("--type", type=str, required=True, 
                       choices=["syllabus", "past_paper", "marking_scheme", "textbook", "teacher_notes"],
                       help="Document type")
    parser.add_argument("--subject", type=str, help="Subject name")
    parser.add_argument("--grade", type=str, help="Grade/Form")
    parser.add_argument("--level", type=str, choices=["primary", "secondary", "a_level"],
                       help="Education level")
    parser.add_argument("--year", type=int, help="Year (for past papers)")
    parser.add_argument("--paper", type=str, help="Paper number")
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.error("Either --file or --dir must be specified")
    
    async def run():
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"File not found: {args.file}")
                return
            
            await ingest_file(
                file_path=file_path,
                doc_type=args.type,
                subject=args.subject,
                grade=args.grade,
                education_level=args.level,
                year=args.year,
                paper=args.paper
            )
        
        elif args.dir:
            directory = Path(args.dir)
            if not directory.exists():
                print(f"Directory not found: {args.dir}")
                return
            
            files, chunks = await ingest_directory(
                directory=directory,
                doc_type=args.type,
                subject=args.subject,
                education_level=args.level
            )
            
            print(f"\nCompleted: {files} files, {chunks} total chunks")
    
    asyncio.run(run())

if __name__ == "__main__":
    main()