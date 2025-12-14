# ============================================================================
# Practice System Tests
# ============================================================================
import pytest
from uuid import uuid4
from app.services.practice.answer_evaluator import AnswerEvaluator
from app.services.practice.adaptive_difficulty import AdaptiveDifficultySystem, DifficultyLevel

class TestAnswerEvaluator:
    """Tests for answer evaluation"""
    
    @pytest.fixture
    def evaluator(self, db_session):
        return AnswerEvaluator(db_session)
    
    def test_extract_number_integer(self, evaluator):
        """Test number extraction from integer"""
        result = evaluator._extract_number("42")
        assert result == 42.0
    
    def test_extract_number_decimal(self, evaluator):
        """Test number extraction from decimal"""
        result = evaluator._extract_number("3.14")
        assert result == 3.14
    
    def test_extract_number_with_unit(self, evaluator):
        """Test number extraction with unit"""
        result = evaluator._extract_number("100 m/s")
        assert result == 100.0
    
    def test_extract_number_fraction(self, evaluator):
        """Test number extraction from fraction"""
        result = evaluator._extract_number("1/2")
        assert result == 0.5
    
    def test_calculate_similarity_identical(self, evaluator):
        """Test similarity calculation for identical strings"""
        result = evaluator._calculate_similarity("hello", "hello")
        assert result == 1.0
    
    def test_calculate_similarity_similar(self, evaluator):
        """Test similarity calculation for similar strings"""
        result = evaluator._calculate_similarity("photosynthesis", "photosynthisis")
        assert result > 0.8
    
    def test_extract_key_terms(self, evaluator):
        """Test key term extraction"""
        text = "the process of photosynthesis converts light energy"
        terms = evaluator._extract_key_terms(text)
        
        assert "photosynthesis" in terms
        assert "the" not in terms

class TestAdaptiveDifficulty:
    """Tests for adaptive difficulty"""
    
    def test_difficulty_calculation_high_performance(self):
        """Test difficulty for high performing student"""
        system = AdaptiveDifficultySystem(None)
        
        difficulty = system._calculate_difficulty(
            recent_performance={"accuracy": 0.90, "trend": "improving", "count": 10},
            topic_mastery=85.0
        )
        
        assert difficulty in [DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
    
    def test_difficulty_calculation_low_performance(self):
        """Test difficulty for struggling student"""
        system = AdaptiveDifficultySystem(None)
        
        difficulty = system._calculate_difficulty(
            recent_performance={"accuracy": 0.40, "trend": "declining", "count": 10},
            topic_mastery=30.0
        )
        
        assert difficulty == DifficultyLevel.EASY
    
    def test_difficulty_insufficient_data(self):
        """Test difficulty with insufficient data"""
        system = AdaptiveDifficultySystem(None)
        
        difficulty = system._calculate_difficulty(
            recent_performance={"accuracy": 0.5, "trend": "stable", "count": 2},
            topic_mastery=None
        )
        
        assert difficulty == DifficultyLevel.EASY