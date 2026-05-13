import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import os
from concurrent.futures import ThreadPoolExecutor
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, TextIteratorStreamer
import torch
from threading import Thread

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Use Mistral-7B-Instruct-v0.2 for chat (lightweight and powerful)
        self.model_name = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", 512))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.7))
        self.initialized = False
        
        logger.info(f"LLM Service initializing with model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        
    async def initialize(self):
        """Initialize the Hugging Face model"""
        try:
            logger.info("Loading Hugging Face model...")
            
            loop = asyncio.get_event_loop()
            
            # Load tokenizer and model in executor to avoid blocking
            def load_model():
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    low_cpu_mem_usage=True
                )
                
                if self.device == "cpu":
                    model = model.to(self.device)
                
                # Create pipeline
                pipe = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device=0 if self.device == "cuda" else -1
                )
                
                return tokenizer, model, pipe
            
            self.tokenizer, self.model, self.pipeline = await loop.run_in_executor(
                self.executor, load_model
            )
            
            self.initialized = True
            logger.info("Hugging Face model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {str(e)}")
            logger.info("Falling back to mock responses...")
            self.initialized = False
    
    async def generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate answer using Hugging Face model based on search results"""
        try:
            if not self.initialized:
                # Fallback response if model not loaded
                return self._generate_fallback_answer(query, search_results)
            
            # Prepare context from search results
            context = self._format_context(search_results)
            
            # Create prompt
            prompt = self._create_prompt(query, context)
            
            # Generate response
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.pipeline(
                    prompt,
                    max_new_tokens=self.max_new_tokens,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.95,
                    top_k=50,
                    repetition_penalty=1.15,
                    return_full_text=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            answer = response[0]['generated_text'].strip()
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return self._generate_fallback_answer(query, search_results)
    
    async def generate_answer_stream(self, query: str, search_results: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """Generate answer with streaming (real-time token generation)"""
        try:
            if not self.initialized:
                # Fallback response if model not loaded
                fallback = self._generate_fallback_answer(query, search_results)
                yield fallback
                return
            
            # Prepare context from search results
            context = self._format_context(search_results)
            
            # Create prompt
            prompt = self._create_prompt(query, context)
            
            # Encode the prompt
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Create streamer
            streamer = TextIteratorStreamer(
                self.tokenizer, 
                skip_prompt=True, 
                skip_special_tokens=True
            )
            
            # Generate in a separate thread
            generation_kwargs = dict(
                inputs,
                streamer=streamer,
                max_new_tokens=self.max_new_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.95,
                top_k=50,
                repetition_penalty=1.15,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Stream tokens as they're generated
            for text in streamer:
                yield text
                await asyncio.sleep(0)  # Allow other tasks to run
            
            thread.join()
            
        except Exception as e:
            logger.error(f"Error in streaming generation: {str(e)}")
            yield self._generate_fallback_answer(query, search_results)
    
    def _format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into context string"""
        if not search_results:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):  # Use top 3 results for speed
            doc_name = result.get('document_name', 'Unknown Document')
            text = result.get('text', '')[:200]  # Limit to 200 chars for speed
            score = result.get('similarity_score', 0)
            
            context_parts.append(f"[{i}] {doc_name}: {text}...")
        
        return "\n\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """Create prompt for the model"""
        # Ultra-simple prompt for TinyLlama - no complex instructions
        prompt = f"""<|system|>
Answer questions based on the context. Use markdown. Be direct and concise.</s>
<|user|>
{context}

{query}</s>
<|assistant|>
"""
        
        return prompt
    
    def _generate_fallback_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate a simple fallback answer when model is not available"""
        if not search_results:
            return "I couldn't find any relevant information in the knowledge base to answer your question."
        
        # Simple concatenation of top results
        answer_parts = ["Based on the available documents:\\n"]
        
        for i, result in enumerate(search_results[:3], 1):
            doc_name = result.get('document_name', 'Unknown')
            text = result.get('text', '')[:200]  # First 200 chars
            answer_parts.append(f"{i}. From {doc_name}: {text}...")
        
        answer_parts.append("\\nNote: Advanced AI model not loaded. Showing raw search results.")
        
        return "\\n".join(answer_parts)
    
    async def test_connection(self) -> bool:
        """Test if the model is loaded and working"""
        return self.initialized
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "current_model": self.model_name if self.initialized else "fallback",
            "device": self.device,
            "initialized": self.initialized,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            if self.pipeline:
                del self.pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
