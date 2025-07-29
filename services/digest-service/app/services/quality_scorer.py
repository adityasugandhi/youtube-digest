import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DigestQualityScorer:
    """Score digest quality based on Robinhood criteria"""
    
    def __init__(self):
        self.weights = {
            'bullet_count': 0.2,      # 3-5 bullets is ideal
            'word_count': 0.15,       # ~20 words per bullet
            'numbers_present': 0.25,  # Contains specific numbers/percentages
            'financial_terms': 0.2,   # Contains relevant financial terminology
            'clarity': 0.2           # Clear, actionable language
        }
    
    def score_digest(self, parsed_digest: Dict, original_transcript: str) -> float:
        """Calculate overall quality score for digest"""
        
        bullet_points = parsed_digest.get('bullet_points', [])
        
        if not bullet_points:
            return 0.0
        
        scores = {
            'bullet_count': self._score_bullet_count(bullet_points),
            'word_count': self._score_word_count(bullet_points),
            'numbers_present': self._score_numbers_present(bullet_points),
            'financial_terms': self._score_financial_terms(bullet_points),
            'clarity': self._score_clarity(bullet_points)
        }
        
        # Calculate weighted average
        total_score = sum(
            score * self.weights[metric] 
            for metric, score in scores.items()
        )
        
        logger.debug(f"Quality scores: {scores}, Total: {total_score}")
        return round(total_score, 2)
    
    def _score_bullet_count(self, bullet_points: List) -> float:
        """Score based on number of bullet points (3-5 is ideal)"""
        count = len(bullet_points)
        
        if 3 <= count <= 5:
            return 1.0
        elif count == 2 or count == 6:
            return 0.7
        elif count == 1 or count == 7:
            return 0.4
        else:
            return 0.0
    
    def _score_word_count(self, bullet_points: List) -> float:
        """Score based on word count per bullet (ideal: 15-20 words)"""
        if not bullet_points:
            return 0.0
        
        scores = []
        for bullet in bullet_points:
            word_count = bullet.word_count if hasattr(bullet, 'word_count') else len(bullet.text.split())
            
            if 15 <= word_count <= 20:
                scores.append(1.0)
            elif 10 <= word_count <= 25:
                scores.append(0.7)
            elif 5 <= word_count <= 30:
                scores.append(0.4)
            else:
                scores.append(0.0)
        
        return sum(scores) / len(scores)
    
    def _score_numbers_present(self, bullet_points: List) -> float:
        """Score based on presence of specific numbers/percentages"""
        if not bullet_points:
            return 0.0
        
        number_pattern = r'\d+\.?\d*%?|\$\d+\.?\d*[KMB]?'
        points_with_numbers = 0
        
        for bullet in bullet_points:
            text = bullet.text if hasattr(bullet, 'text') else str(bullet)
            if re.search(number_pattern, text):
                points_with_numbers += 1
        
        # At least 60% of bullets should have numbers
        ratio = points_with_numbers / len(bullet_points)
        if ratio >= 0.6:
            return 1.0
        elif ratio >= 0.4:
            return 0.7
        elif ratio >= 0.2:
            return 0.4
        else:
            return 0.0
    
    def _score_financial_terms(self, bullet_points: List) -> float:
        """Score based on presence of financial terminology"""
        financial_terms = {
            'earnings', 'revenue', 'profit', 'growth', 'stock', 'shares',
            'market', 'trading', 'investment', 'portfolio', 'dividend',
            'valuation', 'price', 'bull', 'bear', 'volatility', 'options',
            'futures', 'bonds', 'etf', 'ipo', 'merger', 'acquisition',
            'fed', 'rates', 'inflation', 'gdp', 'unemployment'
        }
        
        if not bullet_points:
            return 0.0
        
        total_terms = 0
        for bullet in bullet_points:
            text = bullet.text.lower() if hasattr(bullet, 'text') else str(bullet).lower()
            terms_found = sum(1 for term in financial_terms if term in text)
            total_terms += terms_found
        
        # Normalize by number of bullets
        avg_terms = total_terms / len(bullet_points)
        
        if avg_terms >= 2:
            return 1.0
        elif avg_terms >= 1:
            return 0.7
        elif avg_terms >= 0.5:
            return 0.4
        else:
            return 0.0
    
    def _score_clarity(self, bullet_points: List) -> float:
        """Score based on language clarity and structure"""
        if not bullet_points:
            return 0.0
        
        clarity_indicators = {
            'action_words': ['announces', 'reports', 'increases', 'decreases', 'launches', 'expects'],
            'clear_structure': ['•', '-', 'will', 'plans to', 'aims to'],
            'specific_language': ['specifically', 'exactly', 'precisely', 'particularly']
        }
        
        scores = []
        for bullet in bullet_points:
            text = bullet.text.lower() if hasattr(bullet, 'text') else str(bullet).lower()
            
            score = 0.5  # Base score
            
            # Check for action words
            if any(word in text for word in clarity_indicators['action_words']):
                score += 0.2
            
            # Check for clear structure
            if any(indicator in text for indicator in clarity_indicators['clear_structure']):
                score += 0.1
            
            # Check for specific language
            if any(word in text for word in clarity_indicators['specific_language']):
                score += 0.2
            
            # Penalize for overly complex sentences
            if len(text.split(',')) > 3:
                score -= 0.1
            
            scores.append(min(score, 1.0))
        
        return sum(scores) / len(scores)