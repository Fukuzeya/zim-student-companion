# ============================================================================
# Document Ingestion Script
# ============================================================================
"""
Advanced document ingestion pipeline for ZIMSEC educational content.

Features:
- Parallel processing with progress tracking
- Automatic chunking strategy selection
- Duplicate detection
- Comprehensive logging and error handling
- Resume capability for large batches

Usage:
    # Single file
    python scripts/ingest_documents.py --file ./docs/math_form4.pdf \
        --type past_paper --subject Mathematics --grade "Form 4" --year 2023

    # Directory (recursive)
    python scripts/ingest_documents.py --dir ./documents/past_papers \
        --type past_paper --level secondary

    # With custom chunking
    python scripts/ingest_documents.py --dir ./documents/syllabi \
        --type syllabus --chunking hierarchical

    # Dry run (no indexing)
    python scripts/ingest_documents.py --dir ./docs --type textbook --dry-run

    # Clear collection before ingesting
    python scripts/ingest_documents.py --dir ./docs --type past_paper --clear
"""
import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.rag import (
    DocumentProcessor,
    ZIMSECDocument,
    VectorStore,
    EmbeddingService,
    ChunkingStrategy,
    create_embedding_service,
    create_vector_store,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================
@dataclass
class IngestionConfig:
    """Configuration for document ingestion"""
    # Source
    file_path: Optional[str] = None
    directory: Optional[str] = None
    recursive: bool = True
    
    # Document metadata
    document_type: str = "past_paper"
    subject: Optional[str] = None
    grade: Optional[str] = None
    education_level: str = "secondary"
    year: Optional[int] = None
    paper_number: Optional[str] = None
    
    # Processing options
    chunking_strategy: Optional[str] = None  # Auto-select if None
    batch_size: int = 50
    max_concurrent: int = 5
    
    # Behavior
    dry_run: bool = False
    clear_collection: bool = False
    skip_duplicates: bool = True
    verbose: bool = False


# Document type to collection mapping
COLLECTION_MAP = {
    "syllabus": "syllabi",
    "past_paper": "past_papers",
    "marking_scheme": "marking_schemes",
    "textbook": "textbooks",
    "teacher_notes": "teacher_notes",
    "notes": "teacher_notes",
}

# Subject code mapping
SUBJECT_CODES = {
    "mathematics": "4004",
    "english": "1122",
    "physics": "4023",
    "chemistry": "4024",
    "biology": "4025",
    "geography": "4022",
    "history": "2167",
    "accounting": "7112",
    "commerce": "7103",
    "shona": "3159",
    "ndebele": "3155",
    "computer_science": "4041",
    "agriculture": "5035",
}


# ============================================================================
# Filename Parser
# ============================================================================
class FilenameParser:
    """Parse document metadata from filenames"""
    
    # Expected format: subject_level_grade_year_paper.pdf
    # Examples:
    #   mathematics_secondary_form4_2023_paper1.pdf
    #   physics_a_level_lower6_2022.pdf
    #   biology_primary_grade7_2024_term1.pdf
    
    @staticmethod
    def parse(filename: str) -> Dict[str, any]:
        """
        Extract metadata from filename.
        
        Returns dict with: subject, education_level, grade, year, paper
        """
        # Remove extension and lowercase
        name = Path(filename).stem.lower()
        
        # Replace common separators with underscore
        name = name.replace('-', '_').replace(' ', '_')
        parts = [p for p in name.split('_') if p]
        
        result = {
            "subject": None,
            "education_level": None,
            "grade": None,
            "year": None,
            "paper": None,
        }
        
        for part in parts:
            # Check for subject
            if part in SUBJECT_CODES or part.replace('_', ' ') in [
                'combined science', 'pure mathematics', 'literature'
            ]:
                result["subject"] = part.replace('_', ' ').title()
            
            # Check for education level
            elif part in ['primary', 'secondary', 'a_level', 'alevel', 'o_level', 'olevel']:
                result["education_level"] = part.replace('_', ' ')
            
            # Check for grade/form
            elif any(x in part for x in ['form', 'grade', 'lower', 'upper']):
                result["grade"] = part.replace('_', ' ').title()
            
            # Check for year (4 digits)
            elif part.isdigit() and len(part) == 4:
                result["year"] = int(part)
            
            # Check for paper number
            elif 'paper' in part or part in ['p1', 'p2', 'p3']:
                result["paper"] = part.upper().replace('P', 'Paper ')
        
        return result


# ============================================================================
# Progress Tracker
# ============================================================================
class ProgressTracker:
    """Track ingestion progress"""
    
    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.chunks_created = 0
        self.start_time = datetime.now()
        self.errors: List[Tuple[str, str]] = []
    
    def update(
        self,
        success: bool = True,
        chunks: int = 0,
        skipped: bool = False,
        error: Optional[Tuple[str, str]] = None
    ):
        self.processed += 1
        if skipped:
            self.skipped += 1
        elif success:
            self.successful += 1
            self.chunks_created += chunks
        else:
            self.failed += 1
            if error:
                self.errors.append(error)
    
    def log_progress(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Progress: {self.processed}/{self.total} "
            f"({self.successful} ok, {self.failed} failed, {self.skipped} skipped) "
            f"| {rate:.1f} files/sec | {self.chunks_created} chunks"
        )
    
    def summary(self) -> str:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        lines = [
            "\n" + "=" * 60,
            "INGESTION COMPLETE",
            "=" * 60,
            f"Total files processed: {self.processed}",
            f"  ✓ Successful: {self.successful}",
            f"  ✗ Failed: {self.failed}",
            f"  ⊘ Skipped: {self.skipped}",
            f"Total chunks created: {self.chunks_created}",
            f"Time elapsed: {elapsed:.1f} seconds",
            "=" * 60,
        ]
        
        if self.errors:
            lines.append("\nErrors:")
            for filename, error in self.errors[:10]:
                lines.append(f"  - {filename}: {error}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more")
        
        return "\n".join(lines)


# ============================================================================
# Document Ingestion Engine
# ============================================================================
class IngestionEngine:
    """Main document ingestion engine"""
    
    def __init__(self, settings, config: IngestionConfig):
        self.settings = settings
        self.config = config
        
        # Initialize components
        self.embedding_service = create_embedding_service(settings)
        self.vector_store = create_vector_store(settings, self.embedding_service)
        self.doc_processor = DocumentProcessor()
        
        # Chunking strategy override
        self.chunking_strategy = None
        if config.chunking_strategy:
            try:
                self.chunking_strategy = ChunkingStrategy(config.chunking_strategy)
            except ValueError:
                logger.warning(f"Unknown chunking strategy: {config.chunking_strategy}")
    
    async def initialize(self):
        """Initialize vector store collections"""
        logger.info("Initializing vector store collections...")
        await self.vector_store.initialize_collections()
        logger.info("✓ Collections ready")
    
    async def ingest_file(
        self,
        file_path: Path,
        metadata_override: Optional[Dict] = None
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Ingest a single document file.
        
        Returns:
            Tuple of (success, chunks_created, error_message)
        """
        try:
            metadata_override = metadata_override or {}
            # Parse metadata from filename
            parsed_meta = FilenameParser.parse(file_path.name)
            
            # Merge with overrides (overrides take precedence)
            subject = metadata_override.get("subject") or parsed_meta.get("subject") or self.config.subject
            grade = metadata_override.get("grade") or parsed_meta.get("grade") or self.config.grade
            year = metadata_override.get("year") or parsed_meta.get("year") or self.config.year
            paper = metadata_override.get("paper") or parsed_meta.get("paper") or self.config.paper_number
            level = (metadata_override.get("education_level") or 
                    parsed_meta.get("education_level") or 
                    self.config.education_level)
            
            # Create document object
            doc = ZIMSECDocument(
                file_path=str(file_path),
                document_type=self.config.document_type,
                subject=subject or "Unknown",
                education_level=level,
                grade=grade or "Form 3",
                year=year,
                paper_number=paper,
            )
            
            logger.info(f"Processing: {file_path.name}")
            if self.config.verbose:
                logger.info(f"  Subject: {doc.subject}, Grade: {doc.grade}, Year: {doc.year}")
            
            # Process document (extract and chunk)
            processed = await self.doc_processor.process_document(
                doc,
                strategy=self.chunking_strategy
            )
            
            chunks_created = len(processed.chunks)
            logger.info(f"  → Created {chunks_created} chunks")
            
            # Index to vector store (unless dry run)
            if not self.config.dry_run:
                collection_key = COLLECTION_MAP.get(
                    self.config.document_type,
                    "past_papers"
                )
                
                indexed = await self.vector_store.add_documents(
                    chunks=processed.chunks,
                    collection_key=collection_key,
                    batch_size=self.config.batch_size,
                    show_progress=self.config.verbose
                )
                
                logger.info(f"  ✓ Indexed {indexed} chunks to '{collection_key}'")
                return True, indexed, None
            else:
                logger.info(f"  [DRY RUN] Would index {chunks_created} chunks")
                return True, chunks_created, None
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"  ✗ Error: {error_msg}")
            return False, 0, error_msg
    
    async def ingest_directory(
        self,
        directory: Path,
        metadata_override: Optional[Dict] = None
    ) -> ProgressTracker:
        """
        Ingest all documents in a directory.
        
        Returns:
            ProgressTracker with results
        """
        # Find all supported files
        patterns = ['*.pdf', '*.docx', '*.txt']
        files = []
        
        for pattern in patterns:
            if self.config.recursive:
                files.extend(directory.rglob(pattern))
            else:
                files.extend(directory.glob(pattern))
        
        files = sorted(set(files))
        
        if not files:
            logger.warning(f"No supported files found in {directory}")
            return ProgressTracker(0)
        
        logger.info(f"Found {len(files)} files to process")
        tracker = ProgressTracker(len(files))
        
        # Process files with concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def process_with_limit(file_path: Path):
            async with semaphore:
                success, chunks, error = await self.ingest_file(file_path, metadata_override)
                tracker.update(
                    success=success,
                    chunks=chunks,
                    error=(file_path.name, error) if error else None
                )
                
                # Log progress every 10 files
                if tracker.processed % 10 == 0:
                    tracker.log_progress()
        
        # Run all tasks
        tasks = [process_with_limit(f) for f in files]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return tracker
    
    async def clear_collection(self, collection_key: str) -> bool:
        """Clear a collection before ingesting"""
        collection_key = COLLECTION_MAP.get(collection_key, collection_key)
        logger.warning(f"Clearing collection: {collection_key}")
        return await self.vector_store.clear_collection(collection_key)
    
    async def close(self):
        """Clean up resources"""
        await self.vector_store.close()


# ============================================================================
# CLI
# ============================================================================
def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Ingest ZIMSEC documents into the vector store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file with metadata
  python scripts/ingest_documents.py --file math_2023.pdf --type past_paper \\
      --subject Mathematics --grade "Form 4" --year 2023

  # Directory of past papers
  python scripts/ingest_documents.py --dir ./past_papers --type past_paper

  # Syllabi with hierarchical chunking
  python scripts/ingest_documents.py --dir ./syllabi --type syllabus \\
      --chunking hierarchical

  # Dry run to preview
  python scripts/ingest_documents.py --dir ./docs --type textbook --dry-run
        """
    )
    
    # Source (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=str, help="Single file to ingest")
    source.add_argument("--dir", type=str, help="Directory to ingest")
    
    # Document metadata
    parser.add_argument(
        "--type", "-t",
        type=str,
        required=True,
        choices=["syllabus", "past_paper", "marking_scheme", "textbook", "teacher_notes", "notes"],
        help="Document type"
    )
    parser.add_argument("--subject", "-s", type=str, help="Subject name")
    parser.add_argument("--grade", "-g", type=str, help="Grade/Form (e.g., 'Form 4')")
    parser.add_argument(
        "--level", "-l",
        type=str,
        choices=["primary", "secondary", "a_level"],
        default="secondary",
        help="Education level"
    )
    parser.add_argument("--year", "-y", type=int, help="Year (for past papers)")
    parser.add_argument("--paper", "-p", type=str, help="Paper number (e.g., 'Paper 1')")
    
    # Processing options
    parser.add_argument(
        "--chunking", "-c",
        type=str,
        choices=["fixed_size", "semantic", "hierarchical", "sliding_window", "question_aware"],
        help="Chunking strategy (auto-selected if not specified)"
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for indexing")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent file processing")
    
    # Behavior
    parser.add_argument("--dry-run", action="store_true", help="Process without indexing")
    parser.add_argument("--clear", action="store_true", help="Clear collection before ingesting")
    parser.add_argument("--no-recursive", action="store_true", help="Don't recurse into subdirectories")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()
    settings = get_settings()
    
    # Build configuration
    config = IngestionConfig(
        file_path=args.file,
        directory=args.dir,
        recursive=not args.no_recursive,
        document_type=args.type,
        subject=args.subject,
        grade=args.grade,
        education_level=args.level,
        year=args.year,
        paper_number=args.paper,
        chunking_strategy=args.chunking,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent,
        dry_run=args.dry_run,
        clear_collection=args.clear,
        verbose=args.verbose,
    )
    
    # Create engine
    engine = IngestionEngine(settings, config)
    
    try:
        await engine.initialize()
        
        # Clear collection if requested
        if config.clear_collection and not config.dry_run:
            await engine.clear_collection(config.document_type)
        
        # Process single file or directory
        if config.file_path:
            file_path = Path(config.file_path)
            if not file_path.exists():
                logger.error(f"File not found: {config.file_path}")
                return 1
            
            success, chunks, error = await engine.ingest_file(file_path)
            if success:
                logger.info(f"✓ Successfully ingested {file_path.name} ({chunks} chunks)")
                return 0
            else:
                logger.error(f"✗ Failed to ingest: {error}")
                return 1
        
        elif config.directory:
            directory = Path(config.directory)
            if not directory.exists():
                logger.error(f"Directory not found: {config.directory}")
                return 1
            
            tracker = await engine.ingest_directory(directory)
            print(tracker.summary())
            
            return 0 if tracker.failed == 0 else 1
    
    finally:
        await engine.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)