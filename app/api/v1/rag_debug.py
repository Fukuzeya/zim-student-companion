from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import logging

from app.config import get_settings
from app.services.rag.vector_store import VectorStore
from app.services.rag.document_processor import DocumentProcessor, ZIMSECDocument
from app.services.rag.rag_engine import RAGEngine
from app.api.deps import get_rag_engine

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-debug", tags=["rag-debug"])


# ============================================================================
# 1. CHECK COLLECTIONS - See what's in your vector store
# ============================================================================
@router.get("/collections")
async def check_collections():
    """Check all collections and their document counts"""
    vector_store = VectorStore(settings)
    
    collections_info = {}
    
    for key, collection_name in vector_store.collections.items():
        try:
            # Get collection info from Qdrant
            collection_info = vector_store.client.get_collection(collection_name)
            collections_info[collection_name] = {
                "status": "exists",
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
            }
        except Exception as e:
            collections_info[collection_name] = {
                "status": "not_found",
                "error": str(e)
            }
    
    return {
        "collections": collections_info,
        "total_documents": sum(
            c.get("points_count", 0) 
            for c in collections_info.values() 
            if isinstance(c.get("points_count"), int)
        )
    }


# ============================================================================
# 2. BROWSE COLLECTION - See actual documents in a collection
# ============================================================================
@router.get("/collections/{collection_name}/browse")
async def browse_collection(
    collection_name: str,
    limit: int = 10,
    offset: int = 0
):
    """Browse documents in a specific collection"""
    vector_store = VectorStore(settings)
    
    try:
        # Scroll through points
        points, next_offset = vector_store.client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        documents = []
        for point in points:
            documents.append({
                "id": point.id,
                "content_preview": point.payload.get("content", "")[:300] + "...",
                "metadata": {
                    k: v for k, v in point.payload.items() 
                    if k != "content"
                }
            })
        
        return {
            "collection": collection_name,
            "documents": documents,
            "count": len(documents),
            "next_offset": next_offset
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Collection error: {str(e)}")


# ============================================================================
# 3. SIMPLE SEARCH - Search without filters (to test basic functionality)
# ============================================================================
class SimpleSearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None  # None = search all
    limit: int = 5

@router.post("/search/simple")
async def simple_search(request: SimpleSearchRequest):
    """
    Simple search WITHOUT filters - use this to verify documents exist
    """
    vector_store = VectorStore(settings)
    
    # Generate query embedding
    query_embedding = await vector_store.generate_query_embedding(request.query)
    
    results = []
    collections_to_search = (
        [request.collection] if request.collection 
        else list(vector_store.collections.values())
    )
    
    for collection_name in collections_to_search:
        try:
            search_results = vector_store.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=request.limit,
                with_payload=True
                # NO FILTERS - search everything
            )
            
            for result in search_results:
                results.append({
                    "collection": collection_name,
                    "score": result.score,
                    "content_preview": result.payload.get("content", "")[:300],
                    "metadata": {
                        k: v for k, v in result.payload.items() 
                        if k != "content"
                    }
                })
        except Exception as e:
            logger.error(f"Search error in {collection_name}: {e}")
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": request.query,
        "total_results": len(results),
        "results": results[:request.limit]
    }


# ============================================================================
# 4. FILTERED SEARCH - Search with metadata filters
# ============================================================================
class FilteredSearchRequest(BaseModel):
    query: str
    subject: Optional[str] = None
    education_level: Optional[str] = None
    grade: Optional[str] = None
    document_type: Optional[str] = None
    limit: int = 5

@router.post("/search/filtered")
async def filtered_search(request: FilteredSearchRequest):
    """
    Search WITH filters - to test if filters are matching
    """
    vector_store = VectorStore(settings)
    
    filters = {}
    if request.subject:
        filters["subject"] = request.subject
    if request.education_level:
        filters["education_level"] = request.education_level
    if request.grade:
        filters["grade"] = request.grade
    if request.document_type:
        filters["document_type"] = request.document_type
    
    logger.info(f"Searching with filters: {filters}")
    
    results = await vector_store.search(
        query=request.query,
        filters=filters if filters else None,
        limit=request.limit
    )
    
    return {
        "query": request.query,
        "filters_applied": filters,
        "total_results": len(results),
        "results": [
            {
                "score": r["score"],
                "content_preview": r["content"][:300],
                "metadata": r["metadata"]
            }
            for r in results
        ]
    }


# ============================================================================
# 5. QUICK INGEST - Ingest a document directly via API
# ============================================================================
class QuickIngestRequest(BaseModel):
    content: str
    subject: str = "Computer Science"
    education_level: str = "secondary"
    grade: str = "Form 3"
    document_type: str = "syllabus"  # syllabus, past_paper, etc.
    topic: Optional[str] = None

@router.post("/ingest/quick")
async def quick_ingest(request: QuickIngestRequest):
    """
    Quickly ingest text content for testing
    """
    vector_store = VectorStore(settings)
    await vector_store.initialize_collections()
    
    # Create a simple chunk
    from app.services.rag.document_processor import DocumentChunk
    
    chunk = DocumentChunk(
        content=request.content,
        metadata={
            "subject": request.subject,
            "education_level": request.education_level,
            "grade": request.grade,
            "document_type": request.document_type,
            "topic": request.topic,
            "source": "quick_ingest"
        }
    )
    
    # Determine collection
    collection_map = {
        "syllabus": "zimsec_syllabi",
        "past_paper": "zimsec_past_papers",
        "marking_scheme": "zimsec_marking_schemes",
        "textbook": "textbooks",
        "notes": "teacher_notes"
    }
    collection = collection_map.get(request.document_type, "zimsec_past_papers")
    
    # Add to vector store
    num_added = await vector_store.add_chunks([chunk], collection)
    
    return {
        "success": True,
        "chunks_added": num_added,
        "collection": collection,
        "metadata": chunk.metadata
    }


# ============================================================================
# 6. FILE INGEST - Upload and ingest a file
# ============================================================================
@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    subject: str = "Computer Science",
    education_level: str = "secondary",
    grade: str = "Form 3",
    document_type: str = "past_paper",
    year: Optional[int] = None,
    paper: Optional[str] = None
):
    """
    Upload and ingest a document file (PDF, DOCX, TXT)
    """
    # Save file temporarily
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Create document object
        doc = ZIMSECDocument(
            file_path=tmp_path,
            document_type=document_type,
            subject=subject,
            education_level=education_level,
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
        
        # Store in vector database
        vector_store = VectorStore(settings)
        await vector_store.initialize_collections()
        
        collection_map = {
            "syllabus": "zimsec_syllabi",
            "past_paper": "zimsec_past_papers",
            "marking_scheme": "zimsec_marking_schemes",
            "textbook": "textbooks",
            "notes": "teacher_notes"
        }
        collection = collection_map.get(document_type, "zimsec_past_papers")
        
        num_stored = await vector_store.add_chunks(processed_doc.chunks, collection)
        
        return {
            "success": True,
            "filename": file.filename,
            "chunks_created": len(processed_doc.chunks),
            "chunks_stored": num_stored,
            "collection": collection,
            "sample_chunk": processed_doc.chunks[0].content[:500] if processed_doc.chunks else None
        }
    
    finally:
        # Cleanup temp file
        import os
        os.unlink(tmp_path)


# ============================================================================
# 7. FULL RAG TEST - Test complete RAG pipeline
# ============================================================================
class FullRAGTestRequest(BaseModel):
    question: str
    subject: Optional[str] = "Computer Science"
    grade: Optional[str] = "Form 3"
    education_level: Optional[str] = "secondary"
    mode: str = "socratic"

@router.post("/test/full-rag")
async def test_full_rag(request: FullRAGTestRequest):
    """
    Test the complete RAG pipeline with detailed logging
    """
    vector_store = VectorStore(settings)
    rag_engine = RAGEngine(vector_store, settings)
    
    student_context = {
        "first_name": "Test Student",
        "education_level": request.education_level,
        "grade": request.grade,
        "current_subject": request.subject,
        "preferred_language": "english"
    }
    
    # Step 1: Check what's in the vector store
    collections_status = {}
    for name, coll in vector_store.collections.items():
        try:
            info = vector_store.client.get_collection(coll)
            collections_status[coll] = info.points_count
        except:
            collections_status[coll] = 0
    
    # Step 2: Do a simple search first (no filters)
    simple_results = await vector_store.search(
        query=request.question,
        filters=None,  # No filters
        limit=5
    )
    
    # Step 3: Do filtered search
    filtered_results = await vector_store.search(
        query=request.question,
        filters={
            "subject": request.subject,
            "education_level": request.education_level
        },
        limit=5
    )
    
    # Step 4: Run full RAG
    response, sources = await rag_engine.query(
        question=request.question,
        student_context=student_context,
        mode=request.mode
    )
    
    return {
        "debug_info": {
            "collections_document_count": collections_status,
            "simple_search_results": len(simple_results),
            "filtered_search_results": len(filtered_results),
            "filters_used": {
                "subject": request.subject,
                "education_level": request.education_level
            }
        },
        "simple_search_preview": [
            {
                "score": r["score"],
                "content": r["content"][:200],
                "metadata": r["metadata"]
            }
            for r in simple_results[:3]
        ],
        "filtered_search_preview": [
            {
                "score": r["score"],
                "content": r["content"][:200],
                "metadata": r["metadata"]
            }
            for r in filtered_results[:3]
        ],
        "rag_response": response,
        "sources_used": len(sources)
    }


# ============================================================================
# 8. CLEAR COLLECTION - Delete all documents in a collection
# ============================================================================
@router.delete("/collections/{collection_name}/clear")
async def clear_collection(collection_name: str, confirm: bool = False):
    """
    Clear all documents from a collection (USE WITH CAUTION!)
    """
    if not confirm:
        return {
            "warning": "This will delete ALL documents in the collection!",
            "action": f"Add ?confirm=true to proceed"
        }
    
    vector_store = VectorStore(settings)
    
    try:
        # Delete and recreate collection
        vector_store.client.delete_collection(collection_name)
        await vector_store.initialize_collections()
        
        return {
            "success": True,
            "message": f"Collection {collection_name} cleared and recreated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
