# ============================================================================
# Answer Evaluation Service
# ============================================================================
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import re
import math
from difflib import SequenceMatcher

from app.models.curriculum import Question
from app.services.rag.rag_engine import RAGEngine

class AnswerEvaluator:
    """Evaluate student answers with multiple strategies"""
    
    # Tolerance for numerical answers
    NUMERICAL_TOLERANCE = 0.01  # 1% tolerance
    
    def __init__(self, db: AsyncSession, rag_engine: Optional[RAGEngine] = None):
        self.db = db
        self.rag_engine = rag_engine
    
    async def evaluate(
        self,
        question: Question,
        student_answer: str,
        use_ai: bool = True
    ) -> Tuple[bool, float, str]:
        """
        Evaluate a student's answer.
        
        Returns:
            Tuple of (is_correct, marks_earned, feedback)
        """
        student_answer = student_answer.strip()
        correct_answer = question.correct_answer.strip()
        
        # Route to appropriate evaluator based on question type
        if question.question_type == "multiple_choice":
            return await self._evaluate_mcq(question, student_answer)
        elif question.question_type == "calculation":
            return await self._evaluate_numerical(question, student_answer)
        elif question.question_type in ["short_answer", "long_answer", "essay"]:
            return await self._evaluate_text(question, student_answer, use_ai)
        else:
            # Default text comparison
            return await self._evaluate_text(question, student_answer, use_ai)
    
    async def _evaluate_mcq(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, float, str]:
        """Evaluate multiple choice question"""
        correct = question.correct_answer.strip().lower()
        answer = student_answer.strip().lower()
        
        # Handle letter answers (A, B, C, D)
        if len(answer) == 1 and answer.isalpha():
            index = ord(answer) - ord('a')
            if question.options and 0 <= index < len(question.options):
                answer = question.options[index].lower()
        
        is_correct = (answer == correct) or (answer in correct)
        marks = float(question.marks) if is_correct else 0.0
        
        if is_correct:
            feedback = "Correct! Well done."
        else:
            feedback = f"Incorrect. The correct answer was: {question.correct_answer}"
            if question.explanation:
                feedback += f"\n\nExplanation: {question.explanation}"
        
        return is_correct, marks, feedback
    
    async def _evaluate_numerical(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, float, str]:
        """Evaluate numerical/calculation answer"""
        # Extract numbers from both answers
        student_num = self._extract_number(student_answer)
        correct_num = self._extract_number(question.correct_answer)
        
        if student_num is None:
            return False, 0.0, "Could not parse your answer as a number. Please provide a numerical answer."
        
        if correct_num is None:
            # Fall back to string comparison
            return await self._evaluate_text(question, student_answer, use_ai=False)
        
        # Check with tolerance
        if correct_num == 0:
            is_correct = abs(student_num) < 0.0001
        else:
            relative_error = abs(student_num - correct_num) / abs(correct_num)
            is_correct = relative_error <= self.NUMERICAL_TOLERANCE
        
        if is_correct:
            marks = float(question.marks)
            feedback = "Correct! Your calculation is right."
        else:
            # Check if partially correct (within 10%)
            if correct_num != 0:
                relative_error = abs(student_num - correct_num) / abs(correct_num)
                if relative_error <= 0.1:
                    marks = float(question.marks) * 0.5
                    feedback = f"Close! Your answer {student_num} is approximately correct. The exact answer is {correct_num}."
                else:
                    marks = 0.0
                    feedback = f"Incorrect. The correct answer is {correct_num}."
            else:
                marks = 0.0
                feedback = f"Incorrect. The correct answer is {correct_num}."
            
            if question.marking_scheme:
                feedback += f"\n\nMarking guide: {question.marking_scheme}"
        
        return is_correct, marks, feedback
    
    async def _evaluate_text(
        self,
        question: Question,
        student_answer: str,
        use_ai: bool = True
    ) -> Tuple[bool, float, str]:
        """Evaluate text-based answers"""
        correct = question.correct_answer.lower().strip()
        answer = student_answer.lower().strip()
        
        # First try exact/fuzzy string matching
        similarity = self._calculate_similarity(answer, correct)
        
        if similarity >= 0.9:
            return True, float(question.marks), "Correct! Excellent answer."
        
        if similarity >= 0.7:
            # Partially correct
            marks = float(question.marks) * 0.7
            return True, marks, "Good answer! You captured the main points."
        
        # Check for key terms
        key_terms = self._extract_key_terms(correct)
        matched_terms = sum(1 for term in key_terms if term in answer)
        term_match_ratio = matched_terms / len(key_terms) if key_terms else 0
        
        if term_match_ratio >= 0.6:
            marks = float(question.marks) * term_match_ratio
            return True, marks, f"Partially correct. You mentioned {matched_terms}/{len(key_terms)} key concepts."
        
        # Use AI for more nuanced evaluation if available
        if use_ai and self.rag_engine:
            return await self._ai_evaluate(question, student_answer)
        
        # Default: incorrect
        feedback = f"Not quite right. The expected answer was: {question.correct_answer}"
        if question.explanation:
            feedback += f"\n\nExplanation: {question.explanation}"
        
        return False, 0.0, feedback
    
    async def _ai_evaluate(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, float, str]:
        """Use AI for nuanced answer evaluation"""
        try:
            prompt = f"""Evaluate this student answer against the correct answer.

Question: {question.question_text}
Correct Answer: {question.correct_answer}
Marking Scheme: {question.marking_scheme or 'N/A'}
Total Marks: {question.marks}

Student's Answer: {student_answer}

Evaluate and respond with ONLY a JSON object:
{{
    "is_correct": true/false,
    "marks_earned": <number between 0 and {question.marks}>,
    "feedback": "<specific feedback for the student>"
}}"""
            
            response, _ = await self.rag_engine.query(
                question=prompt,
                student_context={"education_level": "secondary", "grade": "Form 3"},
                mode="marking"
            )
            
            # Parse response
            import json
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return (
                    result.get("is_correct", False),
                    float(result.get("marks_earned", 0)),
                    result.get("feedback", "Please review the correct answer.")
                )
        except Exception as e:
            pass
        
        # Fallback
        return False, 0.0, f"The expected answer was: {question.correct_answer}"
    
    def _extract_number(self, text: str) -> Optional[float]:
        """Extract numerical value from text"""
        # Remove common units and text
        cleaned = re.sub(r'[a-zA-Z°%$£€]', '', text)
        cleaned = cleaned.replace(',', '').strip()
        
        # Handle fractions
        fraction_match = re.match(r'(-?\d+)\s*/\s*(\d+)', cleaned)
        if fraction_match:
            num = int(fraction_match.group(1))
            denom = int(fraction_match.group(2))
            return num / denom if denom != 0 else None
        
        # Handle decimals
        try:
            return float(cleaned)
        except ValueError:
            # Try to find any number in the text
            numbers = re.findall(r'-?\d+\.?\d*', cleaned)
            if numbers:
                return float(numbers[0])
            return None
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from correct answer"""
        # Remove stop words and get important terms
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'and', 'or', 'but', 'it',
            'this', 'that', 'these', 'those'
        }
        
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]