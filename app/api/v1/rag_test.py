from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict

from app.api.deps import get_rag_engine

router = APIRouter(prefix="/rag", tags=["rag-test"])

class RAGQueryRequest(BaseModel):
    question: str
    student_context: Dict
    mode: str = "socratic"
    conversation_history: Optional[List[Dict]] = None

@router.post("/query")
async def query_rag(
    request: RAGQueryRequest,
    rag_engine = Depends(get_rag_engine)
):
    """Direct RAG query endpoint for testing"""
    response, sources = await rag_engine.query(
        question=request.question,
        student_context=request.student_context,
        conversation_history=request.conversation_history,
        mode=request.mode
    )
    
    return {
        "response": response,
        "sources_used": len(sources),
        "sources": [
            {
                "content": s["content"][:700] + "...",
                "score": s["score"],
                "metadata": s["metadata"]
            }
            for s in sources
        ]
    }