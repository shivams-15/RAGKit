import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

from models.schemas import MeetingTranscript, ProgressUpdate, BatchIngestionResponse
from services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.max_workers = int(os.getenv("BATCH_MAX_WORKERS", 4))
        self.batch_size = int(os.getenv("BATCH_PROCESSING_SIZE", 10))
        self.max_memory_usage_percent = float(os.getenv("MAX_MEMORY_USAGE_PERCENT", 80.0))
        self.progress_callbacks: Dict[str, Callable] = {}
        
    def register_progress_callback(self, batch_id: str, callback: Callable):
        """Register a callback for progress updates"""
        self.progress_callbacks[batch_id] = callback
    
    def unregister_progress_callback(self, batch_id: str):
        """Remove progress callback"""
        if batch_id in self.progress_callbacks:
            del self.progress_callbacks[batch_id]
    
    async def _send_progress_update(self, batch_id: str, update: ProgressUpdate):
        """Send progress update via callback if registered"""
        if batch_id in self.progress_callbacks:
            try:
                await self.progress_callbacks[batch_id](update)
            except Exception as e:
                logger.error(f"Error sending progress update: {e}")
    
    def _check_memory_usage(self) -> bool:
        """Check if memory usage is within acceptable limits"""
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < self.max_memory_usage_percent
    
    async def _process_transcript_batch(
        self, 
        batch: List[MeetingTranscript], 
        batch_id: str, 
        batch_index: int,
        total_batches: int
    ) -> Dict[str, Any]:
        """Process a batch of transcripts"""
        batch_start_time = time.time()
        batch_chunks = 0
        failed_transcripts = []
        
        logger.info(f"[{batch_id}] Processing batch {batch_index + 1}/{total_batches} with {len(batch)} transcripts")
        
        for i, transcript in enumerate(batch):
            try:
                # Check memory usage before processing
                if not self._check_memory_usage():
                    logger.warning(f"[{batch_id}] High memory usage detected, pausing...")
                    await asyncio.sleep(2)  # Brief pause to allow memory cleanup
                
                # Send progress update
                progress = ProgressUpdate(
                    batch_id=batch_id,
                    current_transcript=(batch_index * self.batch_size) + i + 1,
                    total_transcripts=0,  # Will be set by caller
                    processed_chunks=batch_chunks,
                    current_meeting_id=transcript.meeting_id,
                    status="processing",
                    timestamp=datetime.now()
                )
                await self._send_progress_update(batch_id, progress)
                
                # Process transcript
                chunks_count = await self.vector_store.ingest_transcript(transcript)
                batch_chunks += chunks_count
                
                logger.info(f"[{batch_id}] Processed meeting {transcript.meeting_id}: {chunks_count} chunks")
                
            except Exception as e:
                logger.error(f"[{batch_id}] Failed to process transcript {transcript.meeting_id}: {e}")
                failed_transcripts.append(transcript.meeting_id)
        
        batch_time = time.time() - batch_start_time
        
        return {
            "chunks": batch_chunks,
            "failed": failed_transcripts,
            "processing_time": batch_time
        }
    
    async def process_large_batch(
        self, 
        transcripts: List[MeetingTranscript], 
        batch_size: Optional[int] = None,
        enable_progress: bool = False
    ) -> BatchIngestionResponse:
        """Process a large batch of transcripts with batching and progress reporting"""
        
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        batch_size = batch_size or self.batch_size
        
        logger.info(f"[{batch_id}] Starting large batch processing: {len(transcripts)} transcripts")
        
        # Split into smaller batches
        batches = [transcripts[i:i + batch_size] for i in range(0, len(transcripts), batch_size)]
        
        total_chunks = 0
        all_failed_transcripts = []
        processed_transcripts = 0
        
        try:
            for batch_index, batch in enumerate(batches):
                # Send batch start progress
                if enable_progress:
                    progress = ProgressUpdate(
                        batch_id=batch_id,
                        current_transcript=processed_transcripts + 1,
                        total_transcripts=len(transcripts),
                        processed_chunks=total_chunks,
                        current_meeting_id=batch[0].meeting_id if batch else "",
                        status="processing",
                        timestamp=datetime.now()
                    )
                    await self._send_progress_update(batch_id, progress)
                
                # Process batch
                batch_result = await self._process_transcript_batch(
                    batch, batch_id, batch_index, len(batches)
                )
                
                total_chunks += batch_result["chunks"]
                all_failed_transcripts.extend(batch_result["failed"])
                processed_transcripts += len(batch) - len(batch_result["failed"])
                
                # Memory management: Force garbage collection between batches
                if batch_index < len(batches) - 1:  # Not the last batch
                    await asyncio.sleep(0.1)  # Brief pause between batches
        
        except Exception as e:
            logger.error(f"[{batch_id}] Critical error during batch processing: {e}")
            # Send failure progress
            if enable_progress:
                progress = ProgressUpdate(
                    batch_id=batch_id,
                    current_transcript=processed_transcripts,
                    total_transcripts=len(transcripts),
                    processed_chunks=total_chunks,
                    current_meeting_id="",
                    status="failed",
                    timestamp=datetime.now()
                )
                await self._send_progress_update(batch_id, progress)
            
            raise
        
        processing_time = time.time() - start_time
        
        # Send completion progress
        if enable_progress:
            progress = ProgressUpdate(
                batch_id=batch_id,
                current_transcript=len(transcripts),
                total_transcripts=len(transcripts),
                processed_chunks=total_chunks,
                current_meeting_id="",
                status="completed",
                timestamp=datetime.now()
            )
            await self._send_progress_update(batch_id, progress)
        
        # Clean up progress callback
        self.unregister_progress_callback(batch_id)
        
        success = len(all_failed_transcripts) < len(transcripts)
        
        logger.info(f"[{batch_id}] Batch processing completed: {processed_transcripts}/{len(transcripts)} transcripts, {total_chunks} chunks, {processing_time:.2f}s")
        
        return BatchIngestionResponse(
            success=success,
            message=f"Processed {processed_transcripts}/{len(transcripts)} transcripts successfully",
            batch_id=batch_id,
            total_transcripts=len(transcripts),
            processed_transcripts=processed_transcripts,
            total_chunks=total_chunks,
            processing_time_seconds=processing_time,
            failed_transcripts=all_failed_transcripts
        )
    
    async def validate_request_size(self, transcripts: List[MeetingTranscript]) -> Dict[str, Any]:
        """Validate if the request is within acceptable limits"""
        max_transcripts = int(os.getenv("MAX_TRANSCRIPTS_PER_BATCH", 1000))
        
        if len(transcripts) > max_transcripts:
            return {
                "valid": False,
                "error": f"Too many transcripts. Maximum allowed: {max_transcripts}, provided: {len(transcripts)}"
            }
        
        # Estimate memory usage (rough calculation)
        estimated_size_mb = 0
        for transcript in transcripts[:10]:  # Sample first 10 for estimation
            transcript_size = len(str(transcript.model_dump())) / (1024 * 1024)  # Convert to MB
            estimated_size_mb += transcript_size
        
        # Extrapolate for all transcripts
        total_estimated_mb = (estimated_size_mb / min(10, len(transcripts))) * len(transcripts)
        max_request_mb = int(os.getenv("MAX_REQUEST_SIZE_MB", 100))
        
        if total_estimated_mb > max_request_mb:
            return {
                "valid": False,
                "error": f"Request too large. Estimated: {total_estimated_mb:.2f}MB, Maximum: {max_request_mb}MB"
            }
        
        return {
            "valid": True,
            "estimated_size_mb": total_estimated_mb,
            "estimated_processing_time": len(transcripts) * 2  # Rough estimate: 2 seconds per transcript
        }
