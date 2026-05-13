from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import uvicorn
from services.vector_store import VectorStoreService
from services.llm_service_hf import LLMService
from services.document_processor import DocumentProcessor
from models.schemas import (
    Document,
    SearchRequest,
    SearchResponse,
    RetrievalRequest,
    RetrievalResponse,
    DeleteRequest,
    DeleteResponse,
    StatsResponse,
    UploadResponse,
    DocumentListResponse
)
import logging
import os
import time
import json
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
vector_store_service = None
llm_service = None
document_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global vector_store_service, llm_service, document_processor
    
    # Startup
    environment = os.getenv("ENVIRONMENT", "dev")
    logger.info(f"Starting up services for environment: {environment}")
    
    vector_store_service = VectorStoreService()
    llm_service = LLMService()
    document_processor = DocumentProcessor()
    
    # Initialize ChromaDB
    await vector_store_service.initialize()
    
    # Initialize LLM (this may take time for HF models)
    await llm_service.initialize()
    
    # Test LLM connection
    llm_connected = await llm_service.test_connection()
    model_info = llm_service.get_model_info()
    logger.info(f"LLM connection test: {'✓' if llm_connected else '✗'}")
    logger.info(f"Model: {model_info['model_name']}, Device: {model_info['device']}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    if vector_store_service:
        await vector_store_service.cleanup()
    if llm_service:
        await llm_service.cleanup()

app = FastAPI(
    title="RAGKit API",
    description="Simple Document RAG Pipeline with Real-Time Streaming - Lightweight Open-Source RAG Toolkit",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_vector_store() -> VectorStoreService:
    """Dependency to get vector store service"""
    if vector_store_service is None:
        raise HTTPException(status_code=503, detail="Vector store service not initialized")
    return vector_store_service

def get_llm_service() -> LLMService:
    """Dependency to get LLM service"""
    if llm_service is None:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    return llm_service

def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor service"""
    if document_processor is None:
        raise HTTPException(status_code=503, detail="Document processor service not initialized")
    return document_processor

@app.get("/")
async def root():
    """Health check endpoint"""
    environment = os.getenv("ENVIRONMENT", "dev")
    model_info = llm_service.get_model_info() if llm_service else {}
    
    return {
        "name": "RAGKit API",
        "message": "Simple Document RAG Pipeline with Real-Time Streaming",
        "version": "2.0.0",
        "environment": environment,
        "model": model_info.get("model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
        "current_model": model_info.get("current_model", "unknown"),
        "device": model_info.get("device", "cpu"),
        "features": ["streaming", "markdown", "multi-format", "semantic-search"]
    }

@app.get("/api/health")
async def health_check():
    """Health check with service status"""
    environment = os.getenv("ENVIRONMENT", "dev")
    stats = await vector_store_service.get_collection_stats() if vector_store_service else {}
    model_info = llm_service.get_model_info() if llm_service else {}
    
    return {
        "status": "healthy",
        "environment": environment,
        "vector_store": "initialized" if vector_store_service else "not initialized",
        "llm_service": "initialized" if llm_service else "not initialized",
        "model": model_info.get("model_name", "unknown"),
        "current_model": model_info.get("current_model", "unknown"),
        "device": model_info.get("device", "cpu"),
        "collection_stats": stats
    }

@app.post("/api/upload", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    category: Optional[str] = Form(None),
    vector_store: VectorStoreService = Depends(get_vector_store),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """Upload and process documents"""
    try:
        start_time = time.time()
        
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        total_chunks = 0
        last_document_id = None
        
        for file in files:
            # Read file content
            content = await file.read()
            
            # Process file
            doc_data = await processor.process_file(content, file.filename, category)
            
            # Create Document object
            document = Document(**doc_data)
            
            # Ingest into vector store
            chunks_count = await vector_store.ingest_document(document)
            total_chunks += chunks_count
            last_document_id = document.document_id
        
        processing_time = time.time() - start_time
        
        return UploadResponse(
            success=True,
            message=f"Successfully uploaded {len(files)} document(s)",
            document_id=last_document_id,
            total_chunks=total_chunks,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """List all documents in the knowledge base"""
    try:
        documents = await vector_store.list_documents()
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Search for similar document chunks"""
    try:
        results = await vector_store.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            document_id=request.document_id
        )
        
        return SearchResponse(
            success=True,
            results=results,
            total_results=len(results),
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/retrieve", response_model=RetrievalResponse)
async def retrieve_and_generate(
    request: RetrievalRequest,
    vector_store: VectorStoreService = Depends(get_vector_store),
    llm: LLMService = Depends(get_llm_service)
):
    """Retrieve relevant chunks and generate an answer"""
    try:
        # Search for relevant chunks
        results = await vector_store.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            document_id=request.document_id
        )
        
        # Convert SearchResult to dict for LLM
        results_dict = [r.model_dump() for r in results]
        
        # Generate answer using LLM
        answer = await llm.generate_answer(request.query, results_dict)
        
        return RetrievalResponse(
            success=True,
            answer=answer,
            results=results,
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/retrieve/stream")
async def retrieve_and_generate_stream(
    request: RetrievalRequest,
    vector_store: VectorStoreService = Depends(get_vector_store),
    llm: LLMService = Depends(get_llm_service)
):
    """Retrieve relevant chunks and generate an answer with streaming"""
    try:
        # Search for relevant chunks
        results = await vector_store.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            document_id=request.document_id
        )
        
        # Convert SearchResult to dict for LLM
        results_dict = [r.model_dump() for r in results]
        
        async def generate_stream():
            # First, send the sources
            sources_data = {
                "type": "sources",
                "sources": [r.model_dump() for r in results]
            }
            yield f"data: {json.dumps(sources_data)}\n\n"
            
            # Then stream the answer
            async for token in llm.generate_answer_stream(request.query, results_dict):
                chunk_data = {
                    "type": "token",
                    "content": token
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # Finally, send completion signal
            done_data = {"type": "done"}
            yield f"data: {json.dumps(done_data)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Delete a document and all its chunks"""
    try:
        deleted_chunks = await vector_store.delete_document(document_id)
        
        return DeleteResponse(
            success=True,
            message=f"Successfully deleted document {document_id}",
            deleted_chunks=deleted_chunks
        )
        
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Get collection statistics"""
    try:
        stats = await vector_store.get_collection_stats()
        
        # Calculate approximate storage size (rough estimate)
        storage_mb = (stats['total_chunks'] * 500 * 0.001)  # Assume ~500 bytes per chunk
        
        return StatsResponse(
            total_documents=stats['total_documents'],
            total_chunks=stats['total_chunks'],
            collection_name=stats['collection_name'],
            embedding_model=stats['embedding_model'],
            storage_mb=round(storage_mb, 2)
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def reset_collection(
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Delete all documents from the collection"""
    try:
        await vector_store.reset_collection()
        return {"success": True, "message": "Collection reset successfully"}
    except Exception as e:
        logger.error(f"Reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
