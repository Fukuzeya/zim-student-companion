# ============================================================================
# Query Processing & Enhancement
# ============================================================================
"""
Advanced query processing for the RAG pipeline:
- Intent detection
- Subject/topic classification
- Query expansion and reformulation
- Spelling correction suggestions
- Query complexity analysis
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================
class QueryIntent(str, Enum):
    """Detected query intent"""
    EXPLAIN = "explain"           # Asking for explanation
    CALCULATE = "calculate"       # Math/calculation request
    COMPARE = "compare"           # Compare concepts
    DEFINE = "define"             # Definition request
    EXAMPLE = "example"           # Asking for examples
    PRACTICE = "practice"         # Practice questions
    HELP = "help"                 # General help
    CLARIFY = "clarify"           # Clarification needed
    GREETING = "greeting"         # Social greeting
    UNKNOWN = "unknown"           # Cannot determine


class QueryComplexity(str, Enum):
    """Query complexity level"""
    SIMPLE = "simple"             # Single concept, direct question
    MODERATE = "moderate"         # Multiple concepts or steps
    COMPLEX = "complex"           # Multi-part, requires synthesis


@dataclass
class ProcessedQuery:
    """Result of query processing"""
    original: str
    cleaned: str
    normalized: str
    
    # Classification
    intent: QueryIntent
    complexity: QueryComplexity
    
    # Extracted information
    subject: Optional[str] = None
    topic: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    
    # Query expansion
    variations: List[str] = field(default_factory=list)
    reformulations: List[str] = field(default_factory=list)
    
    # Metadata
    is_question: bool = True
    language_hints: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "cleaned": self.cleaned,
            "intent": self.intent.value,
            "complexity": self.complexity.value,
            "subject": self.subject,
            "topic": self.topic,
            "keywords": self.keywords,
            "variations": self.variations,
        }


# ============================================================================
# Subject and Topic Detection
# ============================================================================
class SubjectDetector:
    """Detect subject from query text"""
    
    # Subject keyword patterns
    SUBJECT_PATTERNS: Dict[str, List[str]] = {
        "mathematics": [
            r'\b(math|maths|algebra|geometry|calculus|equation|formula|trigonometry)\b',
            r'\b(quadratic|linear|polynomial|fraction|decimal|percentage)\b',
            r'\b(solve|calculate|simplify|factor|expand)\b',
            r'\b(pythagoras|theorem|proof|matrices|vectors)\b',
        ],
        "physics": [
            r'\b(physics|force|energy|motion|velocity|acceleration|momentum)\b',
            r'\b(electricity|magnetism|current|voltage|resistance|circuit)\b',
            r'\b(wave|frequency|wavelength|sound|light|optics)\b',
            r'\b(newton|gravity|mass|weight|pressure)\b',
        ],
        "chemistry": [
            r'\b(chemistry|chemical|element|compound|atom|molecule)\b',
            r'\b(reaction|reactant|product|catalyst|equilibrium)\b',
            r'\b(acid|base|salt|ph|titration|neutralization)\b',
            r'\b(periodic|table|electron|proton|neutron|ion)\b',
            r'\b(organic|inorganic|hydrocarbon|polymer)\b',
        ],
        "biology": [
            r'\b(biology|cell|organism|species|evolution)\b',
            r'\b(photosynthesis|respiration|mitosis|meiosis)\b',
            r'\b(genetics|gene|dna|chromosome|heredity|mutation)\b',
            r'\b(ecology|ecosystem|food chain|habitat|biodiversity)\b',
            r'\b(anatomy|physiology|organ|tissue|circulatory)\b',
        ],
        "english": [
            r'\b(english|grammar|essay|composition|comprehension)\b',
            r'\b(literature|poem|poetry|prose|novel|story)\b',
            r'\b(tense|verb|noun|adjective|adverb|preposition)\b',
            r'\b(summary|analysis|theme|character|plot)\b',
        ],
        "geography": [
            r'\b(geography|map|continent|country|region)\b',
            r'\b(climate|weather|temperature|rainfall|humidity)\b',
            r'\b(population|settlement|migration|urbanization)\b',
            r'\b(river|mountain|valley|plateau|erosion)\b',
        ],
        "history": [
            r'\b(history|historical|war|battle|revolution)\b',
            r'\b(colonial|independence|liberation|chimurenga)\b',
            r'\b(empire|kingdom|dynasty|civilization)\b',
            r'\b(treaty|constitution|government|democracy)\b',
        ],
        "commerce": [
            r'\b(commerce|business|trade|market|economy)\b',
            r'\b(retail|wholesale|import|export|tariff)\b',
            r'\b(insurance|banking|finance|investment)\b',
        ],
        "accounting": [
            r'\b(accounting|accounts|ledger|journal|bookkeeping)\b',
            r'\b(debit|credit|balance|trial|asset|liability)\b',
            r'\b(profit|loss|income|expense|revenue)\b',
        ],
    }
    
    # Topic patterns within subjects
    TOPIC_PATTERNS: Dict[str, Dict[str, List[str]]] = {
        "mathematics": {
            "algebra": [r'\b(algebra|equation|variable|expression|polynomial)\b'],
            "geometry": [r'\b(geometry|triangle|circle|angle|polygon|area|perimeter)\b'],
            "trigonometry": [r'\b(trigonometry|sin|cos|tan|angle|triangle)\b'],
            "statistics": [r'\b(statistics|mean|median|mode|probability|data)\b'],
            "calculus": [r'\b(calculus|derivative|integral|differentiation|limit)\b'],
        },
        "physics": {
            "mechanics": [r'\b(mechanics|force|motion|momentum|velocity|acceleration)\b'],
            "electricity": [r'\b(electricity|current|voltage|resistance|circuit|ohm)\b'],
            "waves": [r'\b(wave|frequency|wavelength|amplitude|sound|light)\b'],
            "thermodynamics": [r'\b(heat|temperature|thermal|energy|entropy)\b'],
        },
        "chemistry": {
            "organic": [r'\b(organic|carbon|hydrocarbon|alkane|alkene|alcohol)\b'],
            "inorganic": [r'\b(inorganic|metal|salt|oxide|hydroxide)\b'],
            "physical": [r'\b(rate|equilibrium|thermochemistry|electrochemistry)\b'],
        },
        "biology": {
            "cells": [r'\b(cell|membrane|nucleus|organelle|mitochondria)\b'],
            "genetics": [r'\b(gene|dna|chromosome|heredity|mutation|allele)\b'],
            "ecology": [r'\b(ecology|ecosystem|habitat|food chain|population)\b'],
            "physiology": [r'\b(respiration|digestion|circulation|excretion)\b'],
        },
    }
    
    @classmethod
    def detect_subject(cls, text: str) -> Optional[str]:
        """Detect subject from text"""
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        
        for subject, patterns in cls.SUBJECT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                score += len(matches)
            if score > 0:
                scores[subject] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    @classmethod
    def detect_topic(cls, text: str, subject: Optional[str]) -> Optional[str]:
        """Detect topic within a subject"""
        if not subject or subject not in cls.TOPIC_PATTERNS:
            return None
        
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        
        for topic, patterns in cls.TOPIC_PATTERNS[subject].items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                score += len(matches)
            if score > 0:
                scores[topic] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None


# ============================================================================
# Intent Detection
# ============================================================================
class IntentDetector:
    """Detect user intent from query"""
    
    INTENT_PATTERNS: Dict[QueryIntent, List[str]] = {
        QueryIntent.EXPLAIN: [
            r'\b(explain|describe|tell me about|how does|why does|what happens)\b',
            r'\b(help me understand|can you explain|what is meant by)\b',
        ],
        QueryIntent.DEFINE: [
            r'\b(what is|what are|define|definition of|meaning of)\b',
            r'\b(what\'s the|whats the)\b',
        ],
        QueryIntent.CALCULATE: [
            r'\b(calculate|solve|find|compute|work out|determine)\b',
            r'\b(what is the value|how much|how many)\b',
            r'[\d\+\-\*\/\=]',  # Mathematical operators
        ],
        QueryIntent.COMPARE: [
            r'\b(compare|difference|differ|similar|contrast|versus|vs)\b',
            r'\b(between|distinguish|differentiate)\b',
        ],
        QueryIntent.EXAMPLE: [
            r'\b(example|examples|show me|demonstrate|illustrate)\b',
            r'\b(give me|provide|such as)\b',
        ],
        QueryIntent.PRACTICE: [
            r'\b(practice|quiz|test|question|exercise|problem)\b',
            r'\b(try|attempt|more questions)\b',
        ],
        QueryIntent.HELP: [
            r'\b(help|stuck|confused|don\'t understand|struggling)\b',
            r'\b(assist|support|guidance)\b',
        ],
        QueryIntent.CLARIFY: [
            r'\b(what do you mean|clarify|not sure|unclear)\b',
            r'\b(can you repeat|say again|rephrase)\b',
        ],
        QueryIntent.GREETING: [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)\b',
            r'\b(how are you|thanks|thank you|bye|goodbye)\b',
        ],
    }
    
    @classmethod
    def detect_intent(cls, text: str) -> Tuple[QueryIntent, float]:
        """
        Detect primary intent from text.
        
        Returns:
            Tuple of (intent, confidence)
        """
        text_lower = text.lower().strip()
        scores: Dict[QueryIntent, int] = {}
        
        for intent, patterns in cls.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                score += len(matches)
            if score > 0:
                scores[intent] = score
        
        if not scores:
            # Default based on question mark
            if '?' in text:
                return QueryIntent.EXPLAIN, 0.5
            return QueryIntent.UNKNOWN, 0.3
        
        best_intent = max(scores, key=scores.get)
        total_matches = sum(scores.values())
        confidence = scores[best_intent] / total_matches if total_matches > 0 else 0.5
        
        return best_intent, min(confidence, 1.0)


# ============================================================================
# Main Query Processor
# ============================================================================
class QueryProcessor:
    """
    Main query processor that combines all processing steps.
    
    Usage:
        processor = QueryProcessor()
        result = processor.process("How do I solve quadratic equations?")
        
        print(result.intent)      # QueryIntent.EXPLAIN
        print(result.subject)     # "mathematics"
        print(result.keywords)    # ["solve", "quadratic", "equations"]
    """
    
    # Stop words for keyword extraction
    STOP_WORDS: Set[str] = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once',
        'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
        'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
        'i', 'me', 'my', 'you', 'your', 'we', 'our', 'they', 'their', 'it',
        'its', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
        'please', 'help', 'want', 'know', 'tell', 'give', 'show', 'let',
    }
    
    def __init__(self):
        self.subject_detector = SubjectDetector()
        self.intent_detector = IntentDetector()
    
    def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessedQuery:
        """
        Process a user query through all analysis steps.
        
        Args:
            query: Raw user query
            context: Optional context (student info, conversation history)
        
        Returns:
            ProcessedQuery with all extracted information
        """
        context = context or {}
        
        # Clean query
        cleaned = self._clean_query(query)
        normalized = self._normalize_query(cleaned)
        
        # Detect intent
        intent, intent_confidence = self.intent_detector.detect_intent(cleaned)
        
        # Detect subject (use context if not detected)
        subject = SubjectDetector.detect_subject(cleaned)
        if not subject and context.get("subject"):
            subject = context["subject"]
        
        # Detect topic
        topic = SubjectDetector.detect_topic(cleaned, subject)
        if not topic and context.get("topic"):
            topic = context["topic"]
        
        # Extract keywords
        keywords = self._extract_keywords(cleaned)
        
        # Extract entities (proper nouns, technical terms)
        entities = self._extract_entities(cleaned)
        
        # Analyze complexity
        complexity = self._analyze_complexity(cleaned, keywords)
        
        # Generate variations
        variations = self._generate_variations(cleaned, subject, context)
        
        # Generate reformulations
        reformulations = self._generate_reformulations(cleaned, intent)
        
        # Check if it's a question
        is_question = '?' in query or intent in [
            QueryIntent.EXPLAIN, QueryIntent.DEFINE,
            QueryIntent.CALCULATE, QueryIntent.COMPARE
        ]
        
        return ProcessedQuery(
            original=query,
            cleaned=cleaned,
            normalized=normalized,
            intent=intent,
            complexity=complexity,
            subject=subject,
            topic=topic,
            keywords=keywords,
            entities=entities,
            variations=variations,
            reformulations=reformulations,
            is_question=is_question,
            confidence=intent_confidence,
        )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query"""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', query.strip())
        
        # Remove excessive punctuation
        cleaned = re.sub(r'[!?]{2,}', '?', cleaned)
        
        # Remove leading filler words
        fillers = ['um', 'uh', 'like', 'so', 'well', 'okay', 'ok', 'right']
        words = cleaned.split()
        while words and words[0].lower().strip('.,') in fillers:
            words.pop(0)
        
        return ' '.join(words) if words else cleaned
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching"""
        return query.lower().strip()
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords"""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        keywords = [w for w in words if w not in self.STOP_WORDS]
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        
        return unique
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities and technical terms"""
        entities = []
        
        # Capitalized words (potential proper nouns)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(caps)
        
        # Technical terms (words with numbers, formulas)
        technical = re.findall(r'\b[A-Za-z]+\d+[A-Za-z]*\b', query)
        entities.extend(technical)
        
        return list(set(entities))
    
    def _analyze_complexity(
        self,
        query: str,
        keywords: List[str]
    ) -> QueryComplexity:
        """Analyze query complexity"""
        # Count complexity indicators
        complexity_score = 0
        
        # Multiple questions
        if query.count('?') > 1:
            complexity_score += 2
        
        # Connectives suggesting multiple parts
        connectives = ['and', 'also', 'plus', 'as well as', 'in addition']
        for conn in connectives:
            if conn in query.lower():
                complexity_score += 1
        
        # Length-based
        word_count = len(query.split())
        if word_count > 30:
            complexity_score += 2
        elif word_count > 15:
            complexity_score += 1
        
        # Multiple keywords
        if len(keywords) > 5:
            complexity_score += 1
        
        if complexity_score >= 3:
            return QueryComplexity.COMPLEX
        elif complexity_score >= 1:
            return QueryComplexity.MODERATE
        return QueryComplexity.SIMPLE
    
    def _generate_variations(
        self,
        query: str,
        subject: Optional[str],
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate query variations for multi-query retrieval"""
        variations = [query]
        
        # Add subject prefix
        if subject and subject.lower() not in query.lower():
            variations.append(f"{subject} {query}")
        
        # Add ZIMSEC prefix
        if 'zimsec' not in query.lower():
            variations.append(f"ZIMSEC {query}")
        
        # Add grade context
        grade = context.get("grade")
        if grade and grade.lower() not in query.lower():
            variations.append(f"{grade} {query}")
        
        # Rephrase as question
        if not query.strip().endswith('?'):
            if not any(query.lower().startswith(w) for w in ['what', 'how', 'why', 'explain']):
                variations.append(f"How to {query}?")
        
        return variations[:5]  # Limit
    
    def _generate_reformulations(
        self,
        query: str,
        intent: QueryIntent
    ) -> List[str]:
        """Generate alternative phrasings"""
        reformulations = []
        query_lower = query.lower()
        
        if intent == QueryIntent.EXPLAIN:
            if 'explain' not in query_lower:
                reformulations.append(f"Explain {query}")
            reformulations.append(f"What is {query}?")
        
        elif intent == QueryIntent.DEFINE:
            reformulations.append(f"Definition of {query}")
        
        elif intent == QueryIntent.CALCULATE:
            reformulations.append(f"How to solve {query}")
            reformulations.append(f"Steps to calculate {query}")
        
        return reformulations[:3]