# RAGKit 🛠️

**Simple Document RAG Pipeline with Real-Time Streaming**

A lightweight, production-ready RAG (Retrieval-Augmented Generation) toolkit for document intelligence. Upload any document (PDF, Word, JSON, CSV, etc.) and chat with your data using open-source AI models.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)

---

## 🌟 Features

### Core Capabilities
- ✅ **Multi-Format Document Support**: PDF, DOCX, JSON, TXT, Markdown, CSV
- ✅ **Real-Time Streaming**: ChatGPT-like streaming responses with live token generation
- ✅ **Markdown Rendering**: Beautiful, formatted AI responses with code blocks, lists, and emphasis
- ✅ **Semantic Search**: Vector-based similarity search powered by ChromaDB
- ✅ **Smart Chunking**: Intelligent text chunking with configurable overlap
- ✅ **Open-Source AI**: 100% open-source using Hugging Face models (TinyLlama 1.1B by default)
- ✅ **Professional UI**: Modern React interface with minimal dark theme

### Three Main Sections
1. **💬 Chat**: Interactive Q&A with your documents featuring:
   - Real-time streaming responses with blinking cursor
   - Markdown-formatted answers
   - Source citations with relevance scores
   - Chat history

2. **📚 Knowledge Base**: Document management interface with:
   - Drag-and-drop file upload
   - Document grid with metadata
   - Statistics dashboard (total docs, chunks, storage)
   - Individual document deletion

3. **⚙️ RAG Pipeline**: Advanced operations including:
   - Semantic search with similarity scores
   - Data browser for exploring vector database
   - Collection statistics
   - Danger zone for database reset

---

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: Modern async Python web framework
- **ChromaDB**: High-performance vector database for embeddings
- **Hugging Face Transformers**: Open-source LLMs with streaming support
  - Default: TinyLlama-1.1B-Chat (2GB, fast on CPU)
  - Supports: Mistral-7B, Llama-2, Phi-2, and more
- **Sentence Transformers**: Document embeddings (all-MiniLM-L6-v2)
- **Document Processors**: PyPDF2 (PDF), python-docx (Word), native JSON/TXT/CSV
- **TextIteratorStreamer**: Real-time token streaming

### Frontend Stack
- **React 18**: Modern UI with hooks
- **Vite**: Lightning-fast build tool and dev server
- **React Router DOM v6**: Client-side routing
- **React Markdown**: Beautiful markdown rendering
- **Axios**: HTTP client for API calls
- **Lucide React**: Modern icon library
- **CSS Variables**: Professional dark theme

### Vector Pipeline
```
Document Upload → Text Extraction → Chunking (500 tokens, 50 overlap) 
→ Embedding (384-dim) → ChromaDB Storage → Semantic Search → LLM Generation
```

---

## 📋 Prerequisites

- **Python**: 3.9 or higher
- **Node.js**: 16 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: ~5GB (model cache + documents)
- **GPU**: Optional (CUDA for faster inference)

## 🚀 Quick Start

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\\Scripts\\Activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   copy .env.example .env
   # Edit .env file with your settings
   ```

5. **Start the server**:
   ```bash
   python main.py
   # Or use uvicorn: uvicorn main:app --reload
   ```

   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

   The UI will be available at `http://localhost:3000`

## 📚 Usage Guide

### Uploading Documents

1. Navigate to **Knowledge Base** tab
2. Click **Choose Files** or drag and drop
3. Supported formats: PDF, DOCX, TXT, JSON, MD, CSV
4. Documents are automatically chunked and vectorized

### Chatting with Documents

1. Navigate to **Chat** tab
2. Type your question in the input box
3. The AI will search your documents and provide answers
4. Sources are shown below each response

### RAG Pipeline Operations

1. **Search**: Perform semantic search across documents
2. **Data Browser**: View collection statistics
3. **Delete**: Remove all documents (use with caution)

## ⚙️ Configuration

### Model Options

The default model is `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (optimized for speed). You can change this in `.env`:

**Lightweight options** (for limited resources - CPU friendly):
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` - **Default**, very fast, 2GB, works great on CPU
- `microsoft/phi-2` - Good balance, 2.7B parameters, 5GB

**Recommended options** (better quality - GPU recommended):
- `mistralai/Mistral-7B-Instruct-v0.2` - Excellent quality, 15GB
- `meta-llama/Llama-2-7b-chat-hf` - Good alternative, 13GB (requires HF token)

**Note**: First-time model loading will download several GB of data and may take 5-10 minutes.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `dev` | Deployment environment |
| `HF_MODEL` | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | Hugging Face model to use |
| `MAX_NEW_TOKENS` | `512` | Max tokens for LLM responses (~400 words) |
| `LLM_TEMPERATURE` | `0.7` | Creativity of responses (0-1) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer for embeddings |
| `CHUNK_SIZE` | `500` | Token size for document chunks |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage directory |

## 🎨 UI Customization

The frontend uses CSS variables for theming. Modify colors in `frontend/src/index.css`:

```css
:root {
  --accent-blue: #3b82f6;
  --accent-green: #10b981;
  --bg-primary: #0a0f1c;
  /* ... more variables */
}
```

## 📊 API Endpoints

### Document Management
- `POST /api/upload` - Upload documents (multipart/form-data)
  - Accepts: PDF, DOCX, TXT, JSON, MD, CSV
  - Optional category parameter
- `GET /api/documents` - List all documents with metadata
- `DELETE /api/documents/{id}` - Delete a specific document
- `GET /api/stats` - Collection statistics (docs, chunks, storage)

### Search & Retrieval
- `POST /api/search` - Semantic search with similarity scores
  - Parameters: query, top_k, category (optional), document_id (optional)
- `POST /api/retrieve` - Search + AI answer generation (non-streaming)
  - Returns: answer, results, query
- `POST /api/retrieve/stream` - **Streaming AI responses** (real-time)
  - Returns: Server-Sent Events (SSE) stream with tokens
  - Events: sources, token, done

### Utilities
- `GET /` - API info and health check
- `GET /api/health` - System health with model info
- `POST /api/reset` - Reset entire collection (⚠️ destructive)

## 🛠️ Development

### Building for Production

**Frontend**:
```bash
cd frontend
npm run build
# Output in frontend/dist
```

**Backend**:
```bash
# Use gunicorn for production
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔧 Troubleshooting

### Model Loading Issues
- **Out of memory**: Use TinyLlama (default) or reduce MAX_NEW_TOKENS
- **Slow loading**: First download takes 5-10 min; subsequent loads are instant
- **CUDA errors**: System will automatically fall back to CPU

### Performance
- **Slow responses**: 
  - TinyLlama on CPU: ~5-10 seconds (acceptable)
  - Mistral-7B on CPU: 30-60 seconds (use GPU or switch to TinyLlama)
  - Reduce MAX_NEW_TOKENS for faster responses
- **Streaming not working**: Check browser console for SSE errors

### Document Processing
- **PDF errors**: Install `PyPDF2`: `pip install PyPDF2`
- **DOCX errors**: Install `python-docx`: `pip install python-docx`
- **Large files**: Files >10MB may take longer to process

### Frontend Issues
- **Port 3000 busy**: Change port in `vite.config.js` server section
- **API connection errors**: Ensure backend is running on port 8000
- **CORS errors**: Check CORS middleware in `backend/main.py`

## 🚀 Performance Tips

1. **Use GPU**: Install CUDA-enabled PyTorch for 10-100x faster inference
2. **Adjust chunk size**: Smaller chunks = faster search, less context
3. **Reduce top_k**: Fewer results = faster responses
4. **Use TinyLlama**: 5-10x faster than Mistral-7B on CPU
5. *TinyLlama Team** - Fast, lightweight chat model
- **Mistral AI** - Mistral-7B model
- **Hugging Face** - Model hub and transformers library
- **Chroma** - High-performance vector database
- **FastAPI** - Modern async Python framework
- **React Team** - Frontend framework
- **Vite** - Lightning-fast build tool

---

## 📞 Support

- **Issues**: Open an issue on GitHub
- **Documentation**: See inline code comments
- **Community**: Contributions and feedback welcome!

**Made with ❤️ for the open-source community**

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional document formats (PPT, HTML, etc.)
- More embedding models
- Advanced RAG techniques (reranking, hybrid search)
- User authentication
- Document versioning

## 🙏 Acknowledgments

- **Mistral AI** - Mistral-7B model
- **Hugging Face** - Model hub and transformers library
- **Chroma** - Vector database
- **FastAPI** - Backend framework
- **React** - Frontend framework
