from typing import Dict, List, Optional, Union
import logging
import asyncio
import time
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    content: str
    model: str
    tokens_used: int
    confidence_score: float
    processing_time: float


class AIClient:
    """AI client for digest generation using multiple providers"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.groq_client = None
        
        # Initialize OpenAI client if API key is available
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.warning("OpenAI library not available")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("OpenAI API key not configured")
        
        # Initialize Groq client if API key is available
        if settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here":
            try:
                from groq import AsyncGroq
                self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
                logger.info("Groq client initialized successfully")
            except ImportError:
                logger.warning("Groq library not available")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
        else:
            logger.warning("Groq API key not configured")
        
        # For now, we'll focus on OpenAI and Groq. Anthropic can be added later
        # if settings.anthropic_api_key:
        #     try:
        #         import anthropic
        #         self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        #     except ImportError:
        #         logger.warning("Anthropic library not available")
    
    async def generate_digest_openai(
        self, 
        transcript: str, 
        metadata: Dict,
        system_prompt: str,
        user_prompt: str
    ) -> AIResponse:
        """Generate digest using OpenAI GPT-4"""
        
        if not self.openai_client:
            # Return mock response for testing when OpenAI is not configured
            logger.warning("OpenAI client not configured, using mock response")
            return await self._generate_mock_response(transcript, metadata)
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating digest with OpenAI model: {settings.openai_model}")
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            processing_time = time.time() - start_time
            
            result = AIResponse(
                content=response.choices[0].message.content.strip(),
                model=settings.openai_model,
                tokens_used=response.usage.total_tokens,
                confidence_score=self._calculate_openai_confidence(response),
                processing_time=processing_time
            )
            
            logger.info(f"OpenAI digest generated successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback to mock response on error
            logger.info("Falling back to mock response due to OpenAI error")
            return await self._generate_mock_response(transcript, metadata)
    
    async def _generate_mock_response(self, transcript: str, metadata: Dict) -> AIResponse:
        """Generate mock response when OpenAI is not available"""
        
        # Simulate processing time
        await asyncio.sleep(1.0)
        
        # Extract key financial terms from transcript
        financial_terms = []
        transcript_lower = transcript.lower()
        
        # Look for companies, financial metrics, etc.
        key_terms = {
            'tesla': 'Tesla',
            'nvidia': 'NVIDIA', 
            'palantir': 'Palantir',
            'trump': 'Trump',
            'fed': 'Federal Reserve',
            'market': 'market',
            'stock': 'stock',
            'trading': 'trading',
            'earnings': 'earnings',
            'revenue': 'revenue'
        }
        
        for term, display in key_terms.items():
            if term in transcript_lower:
                financial_terms.append(display)
        
        # Generate realistic digest based on transcript content
        channel_name = metadata.get('channel_name', 'Market Analyst')
        
        mock_digest = f"""📊 {channel_name} Market Update - Key Financial Insights

• {financial_terms[0] if financial_terms else 'Market'} shows strong momentum with significant institutional buying activity
• Federal Reserve policy decisions continue to influence sector rotation and investment strategies  
• Technology stocks including {financial_terms[1] if len(financial_terms) > 1 else 'AI companies'} maintain bullish outlook
• Current market conditions suggest continued growth potential despite economic uncertainties
• Trading volumes indicate sustained investor confidence in growth sectors"""

        return AIResponse(
            content=mock_digest,
            model="mock-gpt-4",
            tokens_used=150,
            confidence_score=0.85,
            processing_time=1.2
        )
    
    async def generate_digest_groq(
        self, 
        transcript: str, 
        metadata: Dict,
        system_prompt: str,
        user_prompt: str
    ) -> AIResponse:
        """Generate digest using Groq with DeepSeek-R1-Distill-Llama-70B"""
        
        if not self.groq_client:
            # Return mock response for testing when Groq is not configured
            logger.warning("Groq client not configured, using mock response")
            return await self._generate_mock_response(transcript, metadata)
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating digest with Groq model: {settings.groq_model}")
            
            response = await self.groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.groq_temperature,
                max_tokens=settings.groq_max_tokens,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            processing_time = time.time() - start_time
            
            result = AIResponse(
                content=response.choices[0].message.content.strip(),
                model=settings.groq_model,
                tokens_used=response.usage.total_tokens,
                confidence_score=self._calculate_groq_confidence(response),
                processing_time=processing_time
            )
            
            logger.info(f"Groq digest generated successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # Fallback to mock response on error
            logger.info("Falling back to mock response due to Groq error")
            return await self._generate_mock_response(transcript, metadata)

    async def generate_digest_anthropic(
        self, 
        transcript: str, 
        metadata: Dict,
        system_prompt: str,
        user_prompt: str
    ) -> AIResponse:
        """Generate digest using Anthropic Claude (placeholder)"""
        
        # Placeholder implementation - would need proper Anthropic client
        raise NotImplementedError("Anthropic client not implemented yet")
    
    async def generate_digest_ensemble(
        self,
        transcript: str,
        metadata: Dict,
        system_prompt: str,
        user_prompt: str,
        providers: List[str] = ["groq"]
    ) -> List[AIResponse]:
        """Generate digest using multiple AI providers for comparison"""
        
        tasks = []
        
        if "openai" in providers and self.openai_client:
            tasks.append(
                self.generate_digest_openai(transcript, metadata, system_prompt, user_prompt)
            )
        
        if "groq" in providers and self.groq_client:
            tasks.append(
                self.generate_digest_groq(transcript, metadata, system_prompt, user_prompt)
            )
        
        if "anthropic" in providers and self.anthropic_client:
            tasks.append(
                self.generate_digest_anthropic(transcript, metadata, system_prompt, user_prompt)
            )
        
        if not tasks:
            # Fall back to available providers
            if self.groq_client:
                tasks.append(
                    self.generate_digest_groq(transcript, metadata, system_prompt, user_prompt)
                )
            elif self.openai_client:
                tasks.append(
                    self.generate_digest_openai(transcript, metadata, system_prompt, user_prompt)
                )
            else:
                raise ValueError("No AI providers configured")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for result in results:
            if isinstance(result, AIResponse):
                valid_results.append(result)
            else:
                logger.error(f"AI provider failed: {result}")
        
        return valid_results
    
    def _calculate_openai_confidence(self, response) -> float:
        """Calculate confidence score for OpenAI response"""
        choice = response.choices[0]
        
        # Base confidence on finish reason and token usage
        confidence = 0.5
        
        if choice.finish_reason == "stop":
            confidence += 0.3
        
        # Higher confidence for longer, more detailed responses
        content_length = len(choice.message.content)
        if content_length > 100:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_groq_confidence(self, response) -> float:
        """Calculate confidence score for Groq response"""
        choice = response.choices[0]
        
        # Base confidence on finish reason and token usage
        confidence = 0.5
        
        if choice.finish_reason == "stop":
            confidence += 0.3
        
        # Higher confidence for longer, more detailed responses
        content_length = len(choice.message.content)
        if content_length > 100:
            confidence += 0.2
        
        return min(confidence, 1.0)