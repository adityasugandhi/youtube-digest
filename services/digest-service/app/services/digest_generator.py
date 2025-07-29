from typing import Dict, List, Optional
import re
import logging
from datetime import datetime
import asyncio
import sys
import os

# Add shared schemas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from schemas.common import DigestRequest, DigestResponse, BulletPoint

from app.services.ai_client import AIClient, AIResponse
from app.services.quality_scorer import DigestQualityScorer
from app.core.config import settings

logger = logging.getLogger(__name__)


class RobinhoodDigestGenerator:
    """Generate Robinhood Cortex-style financial digests from transcripts"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.quality_scorer = DigestQualityScorer()
        
        # Robinhood Cortex-style system prompt
        self.system_prompt = """
You are the AI engine behind Robinhood Cortex, creating investment insights for retail traders.

CONTEXT: You analyze completed YouTube live stream transcripts about financial markets, companies, or investing. Your job is to extract the most tradeable insights.

ANALYSIS FRAMEWORK:
1. Market Impact: What could move stock prices?
2. Timing: Is this information actionable now?
3. Accessibility: Can a 25-year-old retail investor understand and act on this?

OUTPUT FORMAT (Robinhood Cortex Style):
📊 [Topic/Company] - [Key Status/Movement]

• [Insight 1: Specific fact with number/percentage]
• [Insight 2: Market implication or opportunity]  
• [Insight 3: Expert opinion or prediction]
• [Insight 4: Technical/fundamental driver]
• [Insight 5: Forward-looking statement]

QUALITY CHECKLIST:
✅ Each bullet contains a specific, actionable insight
✅ Numbers and percentages included where available
✅ No financial jargon (EPS → earnings per share)
✅ Focus on "what this means for traders"
✅ Maximum 20 words per bullet point

STYLE: Professional but accessible, confident language, present tense, mobile-first format for quick consumption.
"""
    
    async def generate_digest(self, request: DigestRequest) -> DigestResponse:
        """Generate a complete Robinhood-style digest"""
        
        try:
            # Prepare user prompt with transcript and metadata
            user_prompt = self._build_user_prompt(request)
            
            # Generate digest using AI
            ai_responses = await self.ai_client.generate_digest_ensemble(
                transcript=request.transcript,
                metadata=request.metadata,
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                providers=request.ai_providers or ["groq"]
            )
            
            if not ai_responses:
                raise ValueError("No valid AI responses generated")
            
            # Select best response
            best_response = self._select_best_response(ai_responses)
            
            # Parse digest into structured format
            parsed_digest = self._parse_digest(best_response.content)
            
            # Calculate quality score
            quality_score = self.quality_scorer.score_digest(
                parsed_digest, request.transcript
            )
            
            return DigestResponse(
                video_id=request.video_id,
                title=parsed_digest.get("title", "Market Update"),
                bullet_points=parsed_digest.get("bullet_points", []),
                raw_digest=best_response.content,
                quality_score=quality_score,
                ai_model=best_response.model,
                tokens_used=best_response.tokens_used,
                processing_time=best_response.processing_time,
                confidence_score=best_response.confidence_score,
                generated_at=datetime.utcnow(),
                metadata=request.metadata
            )
            
        except Exception as e:
            logger.error(f"Error generating digest: {e}")
            return DigestResponse(
                video_id=request.video_id,
                title="Error",
                bullet_points=[],
                raw_digest="",
                quality_score=0.0,
                ai_model="error",
                tokens_used=0,
                processing_time=0.0,
                confidence_score=0.0,
                generated_at=datetime.utcnow(),
                error=str(e)
            )
    
    def _build_user_prompt(self, request: DigestRequest) -> str:
        """Build user prompt with transcript and metadata"""
        
        # Process transcript - handle both string and segment list formats
        if isinstance(request.transcript, str):
            transcript_text = request.transcript
        elif isinstance(request.transcript, list):
            # Handle list of transcript segments
            transcript_text = ' '.join([
                seg.get('text', '') if isinstance(seg, dict) else str(seg)
                for seg in request.transcript
            ])
        else:
            transcript_text = str(request.transcript)
        
        # Clean and prepare transcript
        transcript_text = transcript_text.strip()
        
        # Truncate if too long (keep within token limits for GPT-4)
        max_transcript_chars = 6000  # Conservative limit to ensure we stay under token limits
        if len(transcript_text) > max_transcript_chars:
            transcript_text = transcript_text[:max_transcript_chars]
            transcript_text += "\n\n[TRANSCRIPT TRUNCATED FOR LENGTH]"
        
        # Extract key financial terms from transcript for better prompting
        financial_keywords = ['tesla', 'nvidia', 'palantir', 'apple', 'microsoft', 'fed', 'trump', 'market', 'stock', 'earnings']
        found_keywords = [kw for kw in financial_keywords if kw.lower() in transcript_text.lower()]
        
        prompt = f"""
TRANSCRIPT TO ANALYZE:
{transcript_text}

STREAM METADATA:
• Channel: {request.metadata.get('channel_name', 'Financial Analyst')}
• Title: {request.metadata.get('video_title', 'Market Analysis Stream')}
• Date: {request.metadata.get('stream_date', 'Recent')}
• Duration: {request.metadata.get('duration', 'Unknown')}
• View Count: {request.metadata.get('view_count', 'N/A')}

KEY TOPICS DETECTED: {', '.join(found_keywords[:5]) if found_keywords else 'General market discussion'}

ANALYSIS FOCUS:
{request.focus_areas or 'Extract actionable financial insights, market trends, and investment opportunities from this live stream content. Focus on specific companies, price movements, and market-moving events.'}

TASK: Generate a Robinhood Cortex-style digest with:
1. A clear, engaging title with relevant emoji
2. Exactly 4-5 bullet points
3. Each bullet should be specific, actionable, and include numbers/percentages when available
4. Focus on what retail investors need to know
5. Use accessible language (avoid complex financial jargon)
"""
        
        return prompt
    
    def _select_best_response(self, responses: List[AIResponse]) -> AIResponse:
        """Select the best AI response based on quality metrics"""
        
        if len(responses) == 1:
            return responses[0]
        
        # Score each response
        scored_responses = []
        for response in responses:
            score = (
                response.confidence_score * 0.4 +
                self._score_response_content(response.content) * 0.6
            )
            scored_responses.append((score, response))
        
        # Return highest scoring response
        scored_responses.sort(key=lambda x: x[0], reverse=True)
        return scored_responses[0][1]
    
    def _score_response_content(self, content: str) -> float:
        """Score response content based on Robinhood criteria"""
        
        score = 0.0
        
        # Check for bullet points (3-5 is ideal)
        bullet_count = len(re.findall(r'^•', content, re.MULTILINE))
        if 3 <= bullet_count <= 5:
            score += 0.3
        elif bullet_count == 2 or bullet_count == 6:
            score += 0.2
        
        # Check for numbers/percentages
        if re.search(r'\d+\.?\d*%', content):
            score += 0.2
        
        # Check for financial terms
        financial_terms = ['stock', 'market', 'trading', 'earnings', 'revenue', 'growth']
        for term in financial_terms:
            if term.lower() in content.lower():
                score += 0.05
                break
        
        # Check for clear title with emoji
        if '📊' in content or '💰' in content or '📈' in content:
            score += 0.1
        
        return min(score, 1.0)
    
    def _parse_digest(self, raw_digest: str) -> Dict:
        """Parse raw digest into structured format"""
        
        lines = raw_digest.strip().split('\n')
        
        # Extract title (first non-empty line or line with emoji)
        title = "Market Update"
        for line in lines:
            line = line.strip()
            if line and ('📊' in line or '💰' in line or '📈' in line or len(line) > 10):
                title = line.replace('📊', '').replace('💰', '').replace('📈', '').strip()
                break
        
        # Extract bullet points
        bullet_points = []
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-'):
                # Clean up bullet point
                point_text = line[1:].strip()
                if point_text:
                    bullet_points.append(BulletPoint(
                        text=point_text,
                        word_count=len(point_text.split()),
                        has_numbers=bool(re.search(r'\d+\.?\d*%?', point_text))
                    ))
        
        return {
            "title": title,
            "bullet_points": bullet_points
        }
    
    async def batch_generate_digests(
        self, 
        requests: List[DigestRequest]
    ) -> List[DigestResponse]:
        """Generate multiple digests concurrently"""
        
        tasks = [self.generate_digest(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, DigestResponse):
                valid_results.append(result)
            else:
                logger.error(f"Digest generation failed for request {i}: {result}")
                # Create error response
                error_response = DigestResponse(
                    video_id=requests[i].video_id,
                    title="Error",
                    bullet_points=[],
                    raw_digest="",
                    quality_score=0.0,
                    ai_model="error",
                    tokens_used=0,
                    processing_time=0.0,
                    confidence_score=0.0,
                    generated_at=datetime.utcnow(),
                    error=str(result)
                )
                valid_results.append(error_response)
        
        return valid_results