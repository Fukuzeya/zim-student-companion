# ============================================================================
# Query Processing & Enhancement
# ============================================================================
from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass

@dataclass
class ProcessedQuery:
    """Processed and enhanced query"""
    original: str
    cleaned: str
    keywords: List[str]
    subject_hint: Optional[str]
    topic_hint: Optional[str]
    intent: str  # question, explanation, practice, help
    variations: List[str]

class QueryProcessor:
    """Process and enhance user queries for better retrieval"""
    
    # Subject keywords mapping
    SUBJECT_KEYWORDS = {
        "mathematics": ["math", "maths", "algebra", "geometry", "calculus", 
                       "equation", "formula", "number", "calculate"],
        "english": ["english", "grammar", "essay", "comprehension", "literature",
                   "writing", "reading", "vocabulary", "poem", "story"],
        "physics": ["physics", "force", "energy", "motion", "electricity",
                   "wave", "light", "momentum", "gravity"],
        "chemistry": ["chemistry", "chemical", "reaction", "element", "compound",
                     "atom", "molecule", "acid", "base", "periodic"],
        "biology": ["biology", "cell", "organism", "photosynthesis", "respiration",
                   "genetics", "evolution", "ecosystem", "anatomy"],
        "geography": ["geography", "map", "climate", "weather", "population",
                     "settlement", "river", "mountain", "continent"],
        "history": ["history", "war", "independence", "colonial", "civilization",
                   "revolution", "empire", "treaty"]
    }
    
    # Intent patterns
    INTENT_PATTERNS = {
        "explanation": [
            r"what is", r"what are", r"explain", r"describe", r"define",
            r"how does", r"why does", r"tell me about", r"meaning of"
        ],
        "practice": [
            r"practice", r"quiz", r"test me", r"give me question",
            r"example question", r"past paper"
        ],
        "help": [
            r"help", r"stuck", r"don't understand", r"confused",
            r"can you assist", r"i need help"
        ],
        "calculation": [
            r"calculate", r"solve", r"find the value", r"work out",
            r"compute", r"determine"
        ]
    }
    
    def process(self, query: str) -> ProcessedQuery:
        """Process a user query"""
        # Clean the query
        cleaned = self._clean_query(query)
        
        # Extract keywords
        keywords = self._extract_keywords(cleaned)
        
        # Detect subject
        subject_hint = self._detect_subject(cleaned, keywords)
        
        # Detect topic (more specific)
        topic_hint = self._detect_topic(cleaned, subject_hint)
        
        # Detect intent
        intent = self._detect_intent(cleaned)
        
        # Generate query variations for multi-query retrieval
        variations = self._generate_variations(cleaned, subject_hint)
        
        return ProcessedQuery(
            original=query,
            cleaned=cleaned,
            keywords=keywords,
            subject_hint=subject_hint,
            topic_hint=topic_hint,
            intent=intent,
            variations=variations
        )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query"""
        # Convert to lowercase
        cleaned = query.lower().strip()
        
        # Remove excessive punctuation
        cleaned = re.sub(r'[!?]{2,}', '?', cleaned)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common filler words at start
        fillers = ["um", "uh", "like", "so", "well", "okay", "ok"]
        words = cleaned.split()
        while words and words[0] in fillers:
            words.pop(0)
        
        return ' '.join(words)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "i", "me", "my", "you", "your",
            "we", "our", "they", "their", "it", "its", "this", "that"
        }
        
        words = re.findall(r'\b[a-z]+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _detect_subject(
        self,
        query: str,
        keywords: List[str]
    ) -> Optional[str]:
        """Detect the subject from query"""
        query_lower = query.lower()
        
        for subject, subject_keywords in self.SUBJECT_KEYWORDS.items():
            for kw in subject_keywords:
                if kw in query_lower or kw in keywords:
                    return subject
        
        return None
    
    def _detect_topic(
        self,
        query: str,
        subject: Optional[str]
    ) -> Optional[str]:
        """Detect specific topic within subject"""
        # Topic detection based on subject-specific patterns
        topic_patterns = {
            "mathematics": {
                "quadratic": ["quadratic", "x squared", "x^2"],
                "trigonometry": ["sin", "cos", "tan", "trig", "angle"],
                "algebra": ["equation", "variable", "solve for"],
                "geometry": ["triangle", "circle", "area", "perimeter"],
                "statistics": ["mean", "median", "mode", "probability"]
            },
            "physics": {
                "mechanics": ["force", "motion", "momentum", "velocity"],
                "electricity": ["current", "voltage", "resistance", "circuit"],
                "waves": ["wave", "frequency", "wavelength", "sound", "light"]
            },
            "chemistry": {
                "organic": ["carbon", "hydrocarbon", "organic"],
                "reactions": ["reaction", "reactant", "product"],
                "periodic_table": ["element", "periodic", "atom"]
            },
            "biology": {
                "cells": ["cell", "membrane", "nucleus", "organelle"],
                "genetics": ["gene", "dna", "chromosome", "heredity"],
                "ecology": ["ecosystem", "food chain", "habitat"]
            }
        }
        
        if subject and subject in topic_patterns:
            query_lower = query.lower()
            for topic, patterns in topic_patterns[subject].items():
                for pattern in patterns:
                    if pattern in query_lower:
                        return topic
        
        return None
    
    def _detect_intent(self, query: str) -> str:
        """Detect the user's intent"""
        query_lower = query.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        # Default to question if contains question mark
        if "?" in query:
            return "question"
        
        return "question"  # Default intent
    
    def _generate_variations(
        self,
        query: str,
        subject: Optional[str]
    ) -> List[str]:
        """Generate query variations for multi-query retrieval"""
        variations = [query]
        
        # Add subject-prefixed variation
        if subject:
            variations.append(f"{subject} {query}")
        
        # Add ZIMSEC-specific variation
        variations.append(f"ZIMSEC {query}")
        
        # Add question-style variation
        if not query.endswith("?"):
            variations.append(f"How to {query}?")
        
        return variations[:4]  # Limit to 4 variations