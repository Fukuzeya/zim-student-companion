# ============================================================================
# Answer Evaluation Service
# ============================================================================
"""
Intelligent answer evaluation service with multiple strategies:
- Rule-based evaluation for MCQ and numerical answers
- Fuzzy matching for text answers
- AI-powered semantic evaluation using RAG engine
- Partial credit calculation
- Detailed feedback generation

Integrates with the RAG pipeline for:
- Semantic similarity checking
- Context-aware evaluation
- Curriculum-aligned feedback
"""
from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
import re
import logging
from difflib import SequenceMatcher

from app.models.curriculum import Question

# Import from updated RAG pipeline
from app.services.rag import (
    RAGEngine,
    ResponseMode,
    get_metrics_collector,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================
class EvaluationStrategy(str, Enum):
    """Available evaluation strategies"""
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    NUMERICAL = "numerical"
    KEY_TERMS = "key_terms"
    AI_SEMANTIC = "ai_semantic"
    HYBRID = "hybrid"


@dataclass
class EvaluationResult:
    """Structured evaluation result"""
    is_correct: bool
    marks_earned: float
    max_marks: float
    feedback: str
    
    # Detailed breakdown
    strategy_used: EvaluationStrategy
    confidence: float = 1.0
    partial_credit: bool = False
    
    # For analytics
    key_terms_matched: int = 0
    key_terms_total: int = 0
    similarity_score: float = 0.0
    
    # Additional context
    correct_answer: str = ""
    explanation: str = ""
    improvement_tips: List[str] = None
    
    def __post_init__(self):
        if self.improvement_tips is None:
            self.improvement_tips = []
    
    def to_tuple(self) -> Tuple[bool, float, str]:
        """Convert to legacy tuple format for backward compatibility"""
        return (self.is_correct, self.marks_earned, self.feedback)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_correct": self.is_correct,
            "marks_earned": self.marks_earned,
            "max_marks": self.max_marks,
            "feedback": self.feedback,
            "strategy": self.strategy_used.value,
            "confidence": self.confidence,
            "partial_credit": self.partial_credit,
            "similarity_score": self.similarity_score,
            "key_terms": {
                "matched": self.key_terms_matched,
                "total": self.key_terms_total,
            },
            "improvement_tips": self.improvement_tips,
        }


# ============================================================================
# Configuration
# ============================================================================
@dataclass
class EvaluationConfig:
    """Configuration for answer evaluation"""
    # Numerical tolerance
    numerical_tolerance: float = 0.01  # 1%
    numerical_partial_tolerance: float = 0.10  # 10% for partial credit
    
    # Text matching thresholds
    exact_match_threshold: float = 0.95
    high_similarity_threshold: float = 0.85
    partial_match_threshold: float = 0.60
    
    # Key terms
    min_key_term_match_ratio: float = 0.50
    
    # AI evaluation
    use_ai_for_text: bool = True
    ai_confidence_threshold: float = 0.7
    
    # Partial credit
    enable_partial_credit: bool = True
    partial_credit_for_close_numerical: float = 0.5
    partial_credit_for_key_terms: float = 0.6


DEFAULT_CONFIG = EvaluationConfig()


# ============================================================================
# Main Answer Evaluator
# ============================================================================
class AnswerEvaluator:
    """
    Evaluate student answers with multiple strategies.
    
    Features:
    - Automatic strategy selection based on question type
    - Rule-based evaluation for objective questions
    - AI-powered semantic evaluation for subjective answers
    - Partial credit calculation
    - Detailed, encouraging feedback
    
    Usage:
        evaluator = AnswerEvaluator(db, rag_engine)
        result = await evaluator.evaluate(question, student_answer)
        
        # Legacy tuple format
        is_correct, marks, feedback = result.to_tuple()
        
        # Or use structured result
        print(f"Score: {result.marks_earned}/{result.max_marks}")
        print(f"Feedback: {result.feedback}")
    """
    
    # Stop words for key term extraction
    STOP_WORDS = frozenset({
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'and', 'or', 'but', 'it',
        'this', 'that', 'these', 'those', 'what', 'which', 'who',
        'how', 'when', 'where', 'why', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'also', 'now', 'here', 'there',
    })
    
    def __init__(
        self,
        db: AsyncSession,
        rag_engine: Optional[RAGEngine] = None,
        config: Optional[EvaluationConfig] = None
    ):
        self.db = db
        self.rag_engine = rag_engine
        self.config = config or DEFAULT_CONFIG
        self._metrics = get_metrics_collector()
    
    # ==================== Main Evaluation Method ====================
    
    async def evaluate(
        self,
        question: Question,
        student_answer: str,
        student_context: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> EvaluationResult:
        """
        Evaluate a student's answer.
        
        Args:
            question: Question object with correct answer
            student_answer: Student's submitted answer
            student_context: Optional context about the student
            use_ai: Whether to use AI for text evaluation
        
        Returns:
            EvaluationResult with detailed feedback
        """
        # Normalize inputs
        student_answer = student_answer.strip()
        correct_answer = question.correct_answer.strip()
        max_marks = float(question.marks)
        
        # Route to appropriate evaluator based on question type
        question_type = question.question_type.lower() if question.question_type else "text"
        
        if question_type == "multiple_choice":
            result = await self._evaluate_mcq(question, student_answer)
        
        elif question_type in ["calculation", "numerical"]:
            result = await self._evaluate_numerical(question, student_answer)
        
        elif question_type in ["short_answer", "long_answer", "essay", "text"]:
            result = await self._evaluate_text(
                question, student_answer, student_context, use_ai
            )
        
        else:
            # Default to text evaluation
            result = await self._evaluate_text(
                question, student_answer, student_context, use_ai
            )
        
        # Add common fields
        result.max_marks = max_marks
        result.correct_answer = correct_answer
        result.explanation = question.explanation or ""
        
        # Log evaluation
        logger.debug(
            f"Evaluated answer: type={question_type}, "
            f"strategy={result.strategy_used.value}, "
            f"score={result.marks_earned}/{max_marks}, "
            f"correct={result.is_correct}"
        )
        
        return result
    
    # ==================== Legacy Interface ====================
    
    async def evaluate_legacy(
        self,
        question: Question,
        student_answer: str,
        use_ai: bool = True
    ) -> Tuple[bool, float, str]:
        """
        Legacy evaluation interface returning tuple.
        
        For backward compatibility with existing code.
        """
        result = await self.evaluate(question, student_answer, use_ai=use_ai)
        return result.to_tuple()
    
    # ==================== MCQ Evaluation ====================
    
    async def _evaluate_mcq(
        self,
        question: Question,
        student_answer: str
    ) -> EvaluationResult:
        """
        Evaluate multiple choice question.
        
        Handles:
        - Letter answers (A, B, C, D)
        - Full option text
        - Case-insensitive matching
        """
        correct = question.correct_answer.strip().lower()
        answer = student_answer.strip().lower()
        
        # Handle letter answers (A, B, C, D)
        if len(answer) == 1 and answer.isalpha():
            index = ord(answer) - ord('a')
            if question.options and 0 <= index < len(question.options):
                # Get the full option text
                answer = question.options[index].lower()
                # Also check if correct answer is a letter
                if len(correct) == 1 and correct.isalpha():
                    # Compare letters directly
                    is_correct = answer == question.options[ord(correct) - ord('a')].lower()
                else:
                    is_correct = answer == correct or correct in answer
            else:
                is_correct = False
        else:
            # Direct comparison
            is_correct = (answer == correct) or (answer in correct) or (correct in answer)
        
        marks = float(question.marks) if is_correct else 0.0
        
        if is_correct:
            feedback = self._generate_correct_feedback()
        else:
            feedback = self._generate_incorrect_mcq_feedback(question)
        
        return EvaluationResult(
            is_correct=is_correct,
            marks_earned=marks,
            max_marks=float(question.marks),
            feedback=feedback,
            strategy_used=EvaluationStrategy.EXACT_MATCH,
            confidence=1.0,
            similarity_score=1.0 if is_correct else 0.0,
        )
    
    # ==================== Numerical Evaluation ====================
    
    async def _evaluate_numerical(
        self,
        question: Question,
        student_answer: str
    ) -> EvaluationResult:
        """
        Evaluate numerical/calculation answer.
        
        Features:
        - Tolerance-based matching
        - Partial credit for close answers
        - Fraction handling
        - Unit extraction
        """
        student_num = self._extract_number(student_answer)
        correct_num = self._extract_number(question.correct_answer)
        max_marks = float(question.marks)
        
        # Handle parse failures
        if student_num is None:
            return EvaluationResult(
                is_correct=False,
                marks_earned=0.0,
                max_marks=max_marks,
                feedback=(
                    "I couldn't parse your answer as a number. 🔢\n\n"
                    "Please provide a numerical answer (e.g., '42', '3.14', or '1/2')."
                ),
                strategy_used=EvaluationStrategy.NUMERICAL,
                confidence=1.0,
                improvement_tips=["Make sure to enter only the number without extra text"],
            )
        
        if correct_num is None:
            # Fall back to text comparison
            return await self._evaluate_text(question, student_answer, use_ai=False)
        
        # Calculate relative error
        if correct_num == 0:
            is_exact = abs(student_num) < 0.0001
            relative_error = abs(student_num)
        else:
            relative_error = abs(student_num - correct_num) / abs(correct_num)
            is_exact = relative_error <= self.config.numerical_tolerance
        
        # Determine result
        if is_exact:
            return EvaluationResult(
                is_correct=True,
                marks_earned=max_marks,
                max_marks=max_marks,
                feedback=self._generate_correct_calculation_feedback(),
                strategy_used=EvaluationStrategy.NUMERICAL,
                confidence=1.0,
                similarity_score=1.0,
            )
        
        # Check for partial credit
        if self.config.enable_partial_credit and correct_num != 0:
            if relative_error <= self.config.numerical_partial_tolerance:
                partial_marks = max_marks * self.config.partial_credit_for_close_numerical
                
                return EvaluationResult(
                    is_correct=False,
                    marks_earned=partial_marks,
                    max_marks=max_marks,
                    feedback=(
                        f"Close! Your answer ({student_num}) is approximately correct. 📊\n\n"
                        f"The exact answer is **{correct_num}**.\n"
                        f"You earned partial marks for being within 10%."
                    ),
                    strategy_used=EvaluationStrategy.NUMERICAL,
                    confidence=0.9,
                    partial_credit=True,
                    similarity_score=1.0 - relative_error,
                    improvement_tips=["Double-check your calculations", "Watch for rounding errors"],
                )
        
        # Incorrect
        feedback = f"Not quite right. The correct answer is **{correct_num}**. ❌"
        
        if question.marking_scheme:
            feedback += f"\n\n📝 **Marking guide:**\n{question.marking_scheme}"
        
        improvement_tips = [
            "Review the formula or method used",
            "Check your arithmetic step by step",
            "Make sure you used the right units",
        ]
        
        return EvaluationResult(
            is_correct=False,
            marks_earned=0.0,
            max_marks=max_marks,
            feedback=feedback,
            strategy_used=EvaluationStrategy.NUMERICAL,
            confidence=1.0,
            similarity_score=max(0, 1.0 - relative_error),
            improvement_tips=improvement_tips,
        )
    
    # ==================== Text Evaluation ====================
    
    async def _evaluate_text(
        self,
        question: Question,
        student_answer: str,
        student_context: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> EvaluationResult:
        """
        Evaluate text-based answers using multiple strategies.
        
        Strategy order:
        1. Exact/fuzzy string matching
        2. Key term matching
        3. AI semantic evaluation (if enabled)
        """
        correct = question.correct_answer.lower().strip()
        answer = student_answer.lower().strip()
        max_marks = float(question.marks)
        
        # Strategy 1: Fuzzy string matching
        similarity = self._calculate_similarity(answer, correct)
        
        if similarity >= self.config.exact_match_threshold:
            return EvaluationResult(
                is_correct=True,
                marks_earned=max_marks,
                max_marks=max_marks,
                feedback=self._generate_excellent_feedback(),
                strategy_used=EvaluationStrategy.FUZZY_MATCH,
                confidence=1.0,
                similarity_score=similarity,
            )
        
        if similarity >= self.config.high_similarity_threshold:
            marks = max_marks * 0.9
            return EvaluationResult(
                is_correct=True,
                marks_earned=marks,
                max_marks=max_marks,
                feedback=(
                    "Great answer! ✨ You captured the main points very well.\n\n"
                    "Small refinement: Check the exact wording for full marks."
                ),
                strategy_used=EvaluationStrategy.FUZZY_MATCH,
                confidence=0.95,
                partial_credit=True,
                similarity_score=similarity,
            )
        
        # Strategy 2: Key term matching
        key_terms = self._extract_key_terms(correct)
        matched_terms = [term for term in key_terms if term in answer]
        
        if key_terms:
            term_match_ratio = len(matched_terms) / len(key_terms)
            
            if term_match_ratio >= self.config.min_key_term_match_ratio:
                marks = max_marks * min(term_match_ratio, 0.8)
                
                return EvaluationResult(
                    is_correct=term_match_ratio >= 0.7,
                    marks_earned=marks,
                    max_marks=max_marks,
                    feedback=(
                        f"Good effort! You mentioned {len(matched_terms)}/{len(key_terms)} "
                        f"key concepts. 📚\n\n"
                        f"To improve, also include: {', '.join(set(key_terms) - set(matched_terms))[:3]}"
                    ),
                    strategy_used=EvaluationStrategy.KEY_TERMS,
                    confidence=0.8,
                    partial_credit=True,
                    key_terms_matched=len(matched_terms),
                    key_terms_total=len(key_terms),
                    similarity_score=similarity,
                    improvement_tips=[
                        f"Include the term '{term}'" 
                        for term in list(set(key_terms) - set(matched_terms))[:2]
                    ],
                )
        
        # Strategy 3: AI semantic evaluation
        if use_ai and self.rag_engine and self.config.use_ai_for_text:
            ai_result = await self._ai_evaluate(question, student_answer, student_context)
            
            if ai_result.confidence >= self.config.ai_confidence_threshold:
                return ai_result
        
        # Fallback: Incorrect
        feedback = self._generate_incorrect_text_feedback(question, similarity)
        
        return EvaluationResult(
            is_correct=False,
            marks_earned=0.0,
            max_marks=max_marks,
            feedback=feedback,
            strategy_used=EvaluationStrategy.HYBRID,
            confidence=0.7,
            similarity_score=similarity,
            key_terms_matched=len(matched_terms) if key_terms else 0,
            key_terms_total=len(key_terms) if key_terms else 0,
            improvement_tips=[
                "Review the topic in your textbook",
                "Focus on the key concepts asked in the question",
            ],
        )
    
    # ==================== AI Evaluation ====================
    
    async def _ai_evaluate(
        self,
        question: Question,
        student_answer: str,
        student_context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Use RAG engine for semantic answer evaluation.
        
        Leverages the RAG engine's check_answer method for
        curriculum-aligned evaluation.
        """
        try:
            # Build context for evaluation
            eval_context = {
                "first_name": "Student",
                "grade": "Form 3",
                "marks": question.marks,
                **(student_context or {})
            }
            
            # Use RAG engine's built-in answer checking
            result = await self.rag_engine.check_answer(
                question=question.question_text,
                student_answer=student_answer,
                correct_answer=question.correct_answer,
                student_context=eval_context,
                marking_scheme=question.marking_scheme or ""
            )
            
            # Parse result
            is_correct = result.get("is_correct", False)
            marks_earned = float(result.get("marks_earned", 0))
            feedback = result.get("feedback", "")
            explanation = result.get("explanation", "")
            encouragement = result.get("encouragement", "")
            
            # Build comprehensive feedback
            full_feedback = feedback
            if explanation and not is_correct:
                full_feedback += f"\n\n📖 **Explanation:** {explanation}"
            if encouragement:
                full_feedback += f"\n\n{encouragement}"
            
            # Determine confidence based on marks ratio
            max_marks = float(question.marks)
            confidence = 0.9 if marks_earned > 0 else 0.8
            
            return EvaluationResult(
                is_correct=is_correct,
                marks_earned=marks_earned,
                max_marks=max_marks,
                feedback=full_feedback,
                strategy_used=EvaluationStrategy.AI_SEMANTIC,
                confidence=confidence,
                partial_credit=0 < marks_earned < max_marks,
                similarity_score=marks_earned / max_marks if max_marks > 0 else 0,
            )
            
        except Exception as e:
            logger.warning(f"AI evaluation failed: {e}")
            # Return low-confidence fallback
            return EvaluationResult(
                is_correct=False,
                marks_earned=0.0,
                max_marks=float(question.marks),
                feedback=f"The expected answer was: {question.correct_answer}",
                strategy_used=EvaluationStrategy.AI_SEMANTIC,
                confidence=0.3,
            )
    
    # ==================== Helper Methods ====================
    
    def _extract_number(self, text: str) -> Optional[float]:
        """
        Extract numerical value from text.
        
        Handles:
        - Integers and decimals
        - Fractions (1/2, 3/4)
        - Scientific notation
        - Numbers with units
        """
        # Remove common units and text
        cleaned = re.sub(r'[a-zA-Z°%$£€]+', '', text)
        cleaned = cleaned.replace(',', '').strip()
        
        # Handle fractions
        fraction_match = re.match(r'(-?\d+)\s*/\s*(\d+)', cleaned)
        if fraction_match:
            num = int(fraction_match.group(1))
            denom = int(fraction_match.group(2))
            return num / denom if denom != 0 else None
        
        # Handle mixed numbers (2 1/2)
        mixed_match = re.match(r'(-?\d+)\s+(\d+)\s*/\s*(\d+)', cleaned)
        if mixed_match:
            whole = int(mixed_match.group(1))
            num = int(mixed_match.group(2))
            denom = int(mixed_match.group(3))
            if denom != 0:
                return whole + (num / denom) if whole >= 0 else whole - (num / denom)
        
        # Handle decimals and scientific notation
        try:
            return float(cleaned)
        except ValueError:
            # Try to find any number in the text
            numbers = re.findall(r'-?\d+\.?\d*(?:[eE][+-]?\d+)?', cleaned)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    pass
            return None
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate string similarity using SequenceMatcher.
        
        Returns value between 0 and 1.
        """
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from correct answer.
        
        Removes stop words and returns meaningful terms.
        """
        # Extract words (3+ characters)
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Remove stop words
        key_terms = [w for w in words if w not in self.STOP_WORDS]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    # ==================== Feedback Generation ====================
    
    def _generate_correct_feedback(self) -> str:
        """Generate feedback for correct MCQ answer"""
        responses = [
            "Correct! Well done! ✅",
            "That's right! Excellent! 🌟",
            "Perfect! You got it! ✨",
            "Correct! Great job! 🎯",
        ]
        import random
        return random.choice(responses)
    
    def _generate_correct_calculation_feedback(self) -> str:
        """Generate feedback for correct calculation"""
        responses = [
            "Correct! Your calculation is spot on! ✅",
            "Perfect! You nailed the calculation! 🧮",
            "Excellent work! The answer is correct! 🌟",
        ]
        import random
        return random.choice(responses)
    
    def _generate_excellent_feedback(self) -> str:
        """Generate feedback for excellent text answer"""
        responses = [
            "Excellent answer! You've demonstrated a clear understanding. ✨",
            "Outstanding! Your answer shows great comprehension. 🌟",
            "Perfect response! You've captured all the key points. 🎯",
        ]
        import random
        return random.choice(responses)
    
    def _generate_incorrect_mcq_feedback(self, question: Question) -> str:
        """Generate helpful feedback for incorrect MCQ"""
        feedback = f"Not quite. The correct answer was: **{question.correct_answer}** ❌"
        
        if question.explanation:
            feedback += f"\n\n📖 **Explanation:** {question.explanation}"
        
        feedback += "\n\nDon't worry - mistakes help us learn! 💪"
        
        return feedback
    
    def _generate_incorrect_text_feedback(
        self,
        question: Question,
        similarity: float
    ) -> str:
        """Generate helpful feedback for incorrect text answer"""
        feedback = "Not quite right. "
        
        if similarity > 0.4:
            feedback += "You're on the right track though! "
        
        feedback += f"\n\n📝 **Expected answer:** {question.correct_answer}"
        
        if question.explanation:
            feedback += f"\n\n📖 **Explanation:** {question.explanation}"
        
        feedback += "\n\nKeep studying - you'll get it! 💪"
        
        return feedback