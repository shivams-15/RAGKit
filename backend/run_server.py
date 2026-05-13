#!/usr/bin/env python3
"""
Production-ready server runner with proper configuration
"""
import uvicorn
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Run the server with proper configuration"""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "dev")
    
    # Server configuration
    config = {
        "app": "main:app",
        "host": host,
        "port": port,
        "log_level": "info",
        "access_log": True,
        "reload": environment == "dev",  # Only reload in dev environment
        "workers": 1,  # Use 1 worker for development, can be increased for production
    }
    
    # Add SSL configuration for production if certificates are provided
    if environment == "prod":
        ssl_keyfile = os.getenv("SSL_KEYFILE")
        ssl_certfile = os.getenv("SSL_CERTFILE")
        
        if ssl_keyfile and ssl_certfile:
            config.update({
                "ssl_keyfile": ssl_keyfile,
                "ssl_certfile": ssl_certfile,
                "ssl_version": 2,  # TLS 1.2
            })
    
    print(f"🚀 Starting Meeting Transcript RAG Server")
    print(f"📍 Environment: {environment}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔍 Health Check: http://{host}:{port}/health")
    print(f"🧠 LLM Model: {os.getenv('LLM_MODEL', 'o3-mini')}")
    print(f"🔄 Reasoning Effort: {os.getenv('LLM_REASONING_EFFORT', 'medium')}")
    print(f"📦 ChromaDB Collection: meeting_transcripts_{environment}")
    print("="*50)
    
    uvicorn.run(**config)

if __name__ == "__main__":
    main()