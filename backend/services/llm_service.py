import openai
import asyncio
import logging
from typing import List, Dict, Any
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        # Use o3-mini as primary model with gpt-4o-mini as fallback
        self.primary_model = os.getenv("LLM_MODEL", "o3-mini")
        self.fallback_model = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
        self.reasoning_effort = os.getenv("LLM_REASONING_EFFORT", "medium")
        self.max_completion_tokens = 2000
        self.current_model = self.primary_model
        
        logger.info(f"LLM Service initialized with primary model: {self.primary_model}, fallback: {self.fallback_model}, reasoning effort: {self.reasoning_effort}")
        
    async def generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate answer using o3-mini with gpt-4o-mini fallback based on search results"""
        try:
            # Try primary model first (o3-mini)
            return await self._generate_with_model(query, search_results, self.primary_model, use_reasoning=True)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for various error conditions that should trigger fallback
            should_fallback = any(keyword in error_str for keyword in [
                'quota', 'rate', 'insufficient_quota', '429', 'limit',
                'model_not_found', 'invalid_model', 'model not found',
                'unavailable', 'overloaded', 'timeout'
            ])
            
            if should_fallback:
                logger.warning(f"Primary model {self.primary_model} failed: {str(e)}")
                logger.info(f"Falling back to {self.fallback_model}")
                
                try:
                    # Use fallback model (gpt-4o-mini)
                    return await self._generate_with_model(query, search_results, self.fallback_model, use_reasoning=False)
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback model {self.fallback_model} also failed: {str(fallback_error)}")
                    return f"I apologize, but both primary ({self.primary_model}) and fallback ({self.fallback_model}) models are currently unavailable. Please try again later."
            else:
                logger.error(f"Error generating answer with {self.primary_model}: {str(e)}")
                return f"I apologize, but I encountered an error while generating the answer: {str(e)}"
    
    async def _generate_with_model(self, query: str, search_results: List[Dict[str, Any]], model: str, use_reasoning: bool = False) -> str:
        """Generate answer with specified model"""
        # Prepare context from search results
        context = self._format_context(search_results)
        
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        # Prepare messages and parameters based on model capabilities
        if model == "o3-mini" and use_reasoning:
            # o3-mini configuration with reasoning capabilities
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Generate response with o3-mini specific parameters
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=self.max_completion_tokens,
                reasoning_effort=self.reasoning_effort,
                stream=False
                # Note: o3-mini doesn't support temperature parameter
            )
        else:
            # Use standard format for gpt-4o-mini, gpt-3.5-turbo and other models
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            # Generate response with standard parameters
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=min(self.max_completion_tokens, 4000),  # Ensure within limits
                temperature=0.1,
                stream=False
            )
        
        answer = response.choices[0].message.content
        self.current_model = model
        logger.info(f"Generated answer using {model}" + (f" with {self.reasoning_effort} reasoning effort" if use_reasoning else ""))
        
        return answer
    
    def _get_system_prompt(self) -> str:
        """Get system prompt optimized for o3-mini reasoning capabilities"""
        return """You are an AI assistant specialized in analyzing meeting transcripts using advanced reasoning capabilities.

Your task is to:
1. Carefully analyze the provided meeting transcript excerpts
2. Use logical reasoning to connect related information across different parts of the transcripts
3. Answer the user's question with well-structured responses
4. Think step-by-step when processing complex queries
5. Provide clear, actionable insights when appropriate

Guidelines for reasoning:
- Break down complex questions into smaller components
- Look for patterns and connections across different speakers and meetings
- Consider context and implicit information
- Verify consistency of information across sources
- Use markdown formatting for better readability
- Always base your reasoning on the provided transcript excerpts
- If information is insufficient, clearly state what additional context would be helpful

Quality standards:
- Be precise and factual
- Organize information logically
- Provide actionable insights when relevant
- Maintain objectivity and neutrality

IMPORTANT RESPONSE GUIDELINES:
- Do not make up your own information. Just answer from the context
- Do not cite the transcript sources or meeting IDs in the response
- Do not mention unrelated meeting excerpts or content
- Do not add notes about "Additional Context" or mention irrelevant meetings
- Focus only on information that directly answers the user's question
- Keep responses clean and focused without meta-commentary about the data sources
- If multiple meetings contain relevant information, synthesize it naturally without calling attention to the different sources
"""
    
    def _format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into clean context without metadata"""
        if not search_results:
            return "No relevant information found in the meeting transcripts."
        
        context_parts = []
        
        # Group by meeting_id for better organization
        meetings = {}
        for result in search_results:
            meeting_id = result["meeting_id"]
            if meeting_id not in meetings:
                meetings[meeting_id] = []
            meetings[meeting_id].append(result)
        
        # Format each meeting's content without metadata
        for meeting_id, results in meetings.items():
            context_parts.append(f"## Meeting {meeting_id}")
            
            for i, result in enumerate(results, 1):
                text = result["text"]
                context_parts.append(f"{text}")
        
        return "\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """Create optimized prompt for o3-mini reasoning"""
        return f"""Please analyze the following meeting transcript excerpts and provide a comprehensive answer to the user's question.

**User Question:** {query}

**Meeting Transcript Excerpts:**
{context}

**Analysis Instructions:**
1. Read through all the provided excerpts carefully
2. Identify key themes, decisions, and action items relevant to the question
3. Look for connections between different speakers and meetings
4. Reason through the information step-by-step
5. Provide a well-structured answer with clear evidence

**Response Format:**
- Use markdown formatting for better readability
- Include relevant speaker quotes when appropriate
- If multiple perspectives exist, present them objectively
- Provide actionable insights when relevant
- If information is incomplete, specify what additional context would be helpful

**Your Answer:**"""
    
    async def test_connection(self) -> bool:
        """Test connection with primary model and fallback if needed"""
        try:
            # Test primary model first
            if self.primary_model == "o3-mini":
                # Try o3-mini with system and user roles
                response = await self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI assistant with reasoning capabilities."
                        },
                        {
                            "role": "user",
                            "content": "Test: Calculate 2+2 and explain your reasoning briefly."
                        }
                    ],
                    max_completion_tokens=100,
                    reasoning_effort="low"
                )
            else:
                # Standard models (gpt-4o-mini, gpt-3.5-turbo, etc.)
                response = await self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant."
                        },
                        {
                            "role": "user",
                            "content": "Test: Calculate 2+2 and explain briefly."
                        }
                    ],
                    max_tokens=100,
                    temperature=0.1
                )
            
            result = response.choices[0].message.content
            # Check if the response contains the correct answer
            if "4" in result and len(result) > 10:
                logger.info(f"Primary model {self.primary_model} connection test successful")
                return True
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for various error conditions
            should_fallback = any(keyword in error_str for keyword in [
                'quota', 'rate', 'insufficient_quota', '429', 'limit',
                'model_not_found', 'invalid_model', 'model not found',
                'unavailable', 'overloaded', 'does not exist'
            ])
            
            if should_fallback:
                logger.warning(f"Primary model {self.primary_model} test failed: {str(e)}")
                logger.info(f"Testing fallback model {self.fallback_model}")
                
                try:
                    # Test fallback model with standard parameters
                    response = await self.client.chat.completions.create(
                        model=self.fallback_model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant."
                            },
                            {
                                "role": "user",
                                "content": "Calculate 2+2 and provide a brief explanation."
                            }
                        ],
                        max_tokens=100,
                        temperature=0.1
                    )
                    
                    result = response.choices[0].message.content
                    if "4" in result:
                        logger.info(f"Fallback model {self.fallback_model} connection test successful")
                        return True
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback model {self.fallback_model} test also failed: {str(fallback_error)}")
                    
            else:
                logger.error(f"Primary model {self.primary_model} connection test failed: {str(e)}")
                
        return False
    
    def get_model_info(self) -> Dict[str, str]:
        """Get current model information"""
        return {
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "current_model": self.current_model,
            "reasoning_effort": self.reasoning_effort
        }