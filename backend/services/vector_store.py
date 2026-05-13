import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import asyncio
import logging
from typing import List, Dict, Optional, Any
from models.schemas import Document, SearchResult
import tiktoken
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        # Use all-MiniLM-L6-v2 for optimal balance of speed and quality
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_model = None
        self.client = None
        self.collection = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Get environment (dev, staging, prod) for collection naming
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()
        valid_environments = ["dev", "staging", "prod"]
        if self.environment not in valid_environments:
            logger.warning(f"Invalid environment '{self.environment}', defaulting to 'dev'")
            self.environment = "dev"
            
        self.collection_name = f"documents_{self.environment}"
        
        # Configuration
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 500))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 50))
        self.max_chunks_per_document = int(os.getenv("MAX_CHUNKS_PER_DOCUMENT", 1000))
        
        # Initialize tokenizer for chunking
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        logger.info(f"VectorStore initialized for environment: {self.environment}")
        logger.info(f"Collection name: {self.collection_name}")
        
    async def initialize(self):
        """Initialize ChromaDB and embedding model"""
        try:
            # Initialize embedding model in thread pool
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                self.executor, 
                lambda: SentenceTransformer(self.embedding_model_name)
            )
            
            # Initialize ChromaDB client
            persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
            
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collection with environment-specific name
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",  # Use cosine similarity
                    "environment": self.environment,
                    "description": f"Documents for {self.environment} environment"
                }
            )
            
            logger.info(f"Vector store initialized successfully for {self.environment} environment")
            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Persist directory: {persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Cleanup executor
            if self.executor:
                self.executor.shutdown(wait=True)
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _create_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create overlapping chunks from text"""
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= self.chunk_size:
            return [{
                "text": text,
                "metadata": metadata,
                "token_count": len(tokens)
            }]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": len(chunks),
                "start_token": start,
                "end_token": end,
                "token_count": len(chunk_tokens),
                "environment": self.environment
            })
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata,
                "token_count": len(chunk_tokens)
            })
            
            start += self.chunk_size - self.chunk_overlap
        
        return chunks
    
    async def ingest_document(self, document: Document) -> int:
        """Ingest a document into the vector store"""
        try:
            logger.info(f"Ingesting document: {document.name} (ID: {document.document_id})")
            
            # Prepare base metadata
            base_metadata = {
                "document_id": document.document_id,
                "document_name": document.name,
                "category": document.category,
            }
            
            # Add custom metadata if provided
            if document.metadata:
                base_metadata.update(document.metadata)
            
            # Create chunks
            chunks = self._create_chunks(document.content, base_metadata)
            
            if len(chunks) > self.max_chunks_per_document:
                logger.warning(
                    f"Document {document.document_id} has {len(chunks)} chunks, "
                    f"exceeding max {self.max_chunks_per_document}. Truncating."
                )
                chunks = chunks[:self.max_chunks_per_document]
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor,
                lambda: self.embedding_model.encode(chunk_texts, show_progress_bar=False).tolist()
            )
            
            # Prepare data for ChromaDB
            ids = [f"{document.document_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [chunk["metadata"] for chunk in chunks]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully ingested {len(chunks)} chunks for document {document.document_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to ingest document {document.document_id}: {str(e)}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                self.executor,
                lambda: self.embedding_model.encode([query], show_progress_bar=False).tolist()[0]
            )
            
            # Prepare filters
            where_filter = {}
            if category:
                where_filter["category"] = category
            if document_id:
                where_filter["document_id"] = document_id
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None
            )
            
            # Format results
            search_results = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    metadata = results['metadatas'][0][i]
                    search_results.append(SearchResult(
                        document_id=metadata.get('document_id', 'unknown'),
                        document_name=metadata.get('document_name', 'Unknown'),
                        text=results['documents'][0][i],
                        category=metadata.get('category', 'general'),
                        similarity_score=1 - results['distances'][0][i],  # Convert distance to similarity
                        chunk_index=metadata.get('chunk_index', 0),
                        metadata=metadata
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks of a document"""
        try:
            # Get all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not results or not results['ids']:
                logger.warning(f"No chunks found for document {document_id}")
                return 0
            
            # Delete all chunks
            self.collection.delete(
                ids=results['ids']
            )
            
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            return len(results['ids'])
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            
            # Get unique documents
            all_items = self.collection.get()
            unique_documents = set()
            if all_items and all_items['metadatas']:
                for metadata in all_items['metadatas']:
                    if 'document_id' in metadata:
                        unique_documents.add(metadata['document_id'])
            
            return {
                "total_documents": len(unique_documents),
                "total_chunks": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "environment": self.environment
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "environment": self.environment
            }
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the collection"""
        try:
            all_items = self.collection.get()
            
            # Group by document
            documents_map = {}
            if all_items and all_items['metadatas']:
                for metadata in all_items['metadatas']:
                    doc_id = metadata.get('document_id')
                    if doc_id and doc_id not in documents_map:
                        documents_map[doc_id] = {
                            'id': doc_id,
                            'name': metadata.get('document_name', 'Unknown'),
                            'category': metadata.get('category', 'general'),
                            'chunks': 0,
                            'uploaded_at': metadata.get('uploaded_at', '')
                        }
                    if doc_id:
                        documents_map[doc_id]['chunks'] += 1
            
            return list(documents_map.values())
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    async def reset_collection(self):
        """Delete all documents from the collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "environment": self.environment,
                    "description": f"Documents for {self.environment} environment"
                }
            )
            logger.info(f"Collection {self.collection_name} has been reset")
        except Exception as e:
            logger.error(f"Failed to reset collection: {str(e)}")
            raise
