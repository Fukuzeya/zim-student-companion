# ============================================================================
# RAG System Tests
# ============================================================================
import pytest
from app.services.rag.document_processor import DocumentProcessor, ZIMSECDocument, DocumentChunk
from app.services.rag.query_processor import QueryProcessor
from app.services.rag.prompts import ZIMSECPrompts

class TestDocumentProcessor:
    """Tests for document processing"""
    
    @pytest.fixture
    def processor(self):
        return DocumentProcessor(chunk_size=100, chunk_overlap=20)
    
    def test_preprocess_content(self, processor):
        """Test content preprocessing"""
        content = "This is   a test\n\n\n\nWith multiple   spaces"
        result = processor._preprocess_content(content)
        
        assert "   " not in result
        assert "\n\n\n\n" not in result
    
    def test_extract_key_terms(self, processor):
        """Test keyword extraction"""
        text = "The quadratic equation formula is used to solve equations"
        # Using QueryProcessor for this
        qp = QueryProcessor()
        keywords = qp._extract_keywords(text)
        
        assert "quadratic" in keywords
        assert "equation" in keywords
        assert "the" not in keywords  # Stop word
    
    def test_chunk_creation(self, processor):
        """Test chunk creation"""
        chunks = processor._split_into_chunks(
            "First paragraph about mathematics.\n\nSecond paragraph about algebra.\n\nThird paragraph about equations.",
            {"subject": "Mathematics"}
        )
        
        assert len(chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.metadata["subject"] == "Mathematics" for c in chunks)

class TestQueryProcessor:
    """Tests for query processing"""
    
    @pytest.fixture
    def processor(self):
        return QueryProcessor()
    
    def test_detect_subject_math(self, processor):
        """Test subject detection for mathematics"""
        query = "How do I solve quadratic equations?"
        result = processor.process(query)
        
        assert result.subject_hint == "mathematics"
    
    def test_detect_subject_physics(self, processor):
        """Test subject detection for physics"""
        query = "What is the formula for force?"
        result = processor.process(query)
        
        assert result.subject_hint == "physics"
    
    def test_detect_intent_explanation(self, processor):
        """Test intent detection for explanation"""
        query = "Explain photosynthesis"
        result = processor.process(query)
        
        assert result.intent == "explanation"
    
    def test_detect_intent_practice(self, processor):
        """Test intent detection for practice"""
        query = "Give me a practice question"
        result = processor.process(query)
        
        assert result.intent == "practice"
    
    def test_generate_variations(self, processor):
        """Test query variation generation"""
        query = "quadratic equations"
        result = processor.process(query)
        
        assert len(result.variations) >= 2
        assert query in result.variations

class TestPromptBuilder:
    """Tests for prompt building"""
    
    def test_build_socratic_prompt(self):
        """Test Socratic mode prompt building"""
        student_context = {
            "first_name": "Tatenda",
            "education_level": "secondary",
            "grade": "Form 3",
            "current_subject": "Mathematics",
            "preferred_language": "english"
        }
        
        prompt = ZIMSECPrompts.build_prompt(
            mode="socratic",
            student_context=student_context,
            context="Test curriculum context",
            question="How do I solve this equation?"
        )
        
        assert "Tatenda" in prompt
        assert "NEVER give direct answers" in prompt
        assert "Test curriculum context" in prompt
    
    def test_build_explain_prompt(self):
        """Test explanation mode prompt building"""
        student_context = {
            "first_name": "Test",
            "education_level": "secondary",
            "grade": "Form 3",
            "current_subject": "Physics",
            "preferred_language": "english"
        }
        
        prompt = ZIMSECPrompts.build_prompt(
            mode="explain",
            student_context=student_context,
            question="Explain momentum"
        )
        
        assert "EXPLANATION MODE" in prompt