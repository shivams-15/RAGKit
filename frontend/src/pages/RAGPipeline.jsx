import React, { useState, useEffect } from 'react'
import { Database, Search, Trash2, Upload, Eye, RefreshCw } from 'lucide-react'
import axios from 'axios'
import './RAGPipeline.css'

const RAGPipeline = () => {
  const [activeFunction, setActiveFunction] = useState('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [collectionStats, setCollectionStats] = useState(null)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    fetchCollectionStats()
  }, [])

  const fetchCollectionStats = async () => {
    try {
      const response = await axios.get('/api/stats')
      setCollectionStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    setMessage(null)
    
    try {
      const response = await axios.post('/api/search', {
        query: searchQuery,
        top_k: 10
      })
      
      setSearchResults(response.data.results || [])
      setMessage({
        type: 'success',
        text: `Found ${response.data.results?.length || 0} results`
      })
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Search failed: ${error.response?.data?.detail || error.message}`
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAll = async () => {
    if (!confirm('Are you sure you want to delete ALL documents? This cannot be undone.')) return
    
    setLoading(true)
    setMessage(null)
    
    try {
      await axios.post('/api/reset')
      setMessage({
        type: 'success',
        text: 'All documents deleted successfully'
      })
      setSearchResults([])
      fetchCollectionStats()
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Delete failed: ${error.response?.data?.detail || error.message}`
      })
    } finally {
      setLoading(false)
    }
  }

  const renderFunctionContent = () => {
    switch(activeFunction) {
      case 'search':
        return (
          <div className="function-content">
            <h3>Vector Search</h3>
            <p>Search through your document embeddings using semantic similarity</p>
            
            <div className="search-form">
              <div className="form-group">
                <label>Search Query</label>
                <textarea
                  placeholder="Enter your search query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  rows={3}
                />
              </div>
              
              <button className="btn-primary" onClick={handleSearch} disabled={loading}>
                <Search size={18} />
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className="search-results">
                <h4>Results ({searchResults.length})</h4>
                {searchResults.map((result, index) => (
                  <div key={index} className="result-item">
                    <div className="result-header">
                      <span className="result-doc">{result.document_name || result.meeting_id}</span>
                      <span className="result-score">{(result.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="result-text">{result.text}</div>
                    <div className="result-meta">
                      <span>Category: {result.category}</span>
                      <span>Chunk: {result.chunk_index}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
        
      case 'browser':
        return (
          <div className="function-content">
            <h3>Data Browser</h3>
            <p>View and explore your vectorized document chunks</p>
            
            <div className="stats-grid">
              <div className="stat-box">
                <div className="stat-label">Total Documents</div>
                <div className="stat-number">{collectionStats?.total_documents || 0}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Total Chunks</div>
                <div className="stat-number">{collectionStats?.total_chunks || 0}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Embedding Model</div>
                <div className="stat-text">{collectionStats?.embedding_model || 'all-MiniLM-L6-v2'}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Collection</div>
                <div className="stat-text">{collectionStats?.collection_name || 'N/A'}</div>
              </div>
            </div>

            <button className="btn-secondary" onClick={fetchCollectionStats}>
              <RefreshCw size={18} />
              Refresh Stats
            </button>
          </div>
        )
        
      case 'delete':
        return (
          <div className="function-content">
            <h3>Delete Operations</h3>
            <p>Remove documents from the vector database</p>
            
            <div className="danger-zone">
              <div className="danger-header">
                <Trash2 size={24} />
                <div>
                  <h4>Danger Zone</h4>
                  <p>Permanently delete all documents from the database</p>
                </div>
              </div>
              
              <button className="btn-danger" onClick={handleDeleteAll} disabled={loading}>
                <Trash2 size={18} />
                {loading ? 'Deleting...' : 'Delete All Documents'}
              </button>
            </div>
          </div>
        )
        
      default:
        return null
    }
  }

  return (
    <div className="rag-pipeline-page">
      <div className="pipeline-sidebar">
        <h3>Functions</h3>
        <div className="function-menu">
          <button
            className={`function-item ${activeFunction === 'search' ? 'active' : ''}`}
            onClick={() => setActiveFunction('search')}
          >
            <Search size={18} />
            <span>Search</span>
          </button>
          
          <button
            className={`function-item ${activeFunction === 'browser' ? 'active' : ''}`}
            onClick={() => setActiveFunction('browser')}
          >
            <Eye size={18} />
            <span>Data Browser</span>
          </button>
          
          <button
            className={`function-item ${activeFunction === 'delete' ? 'active' : ''}`}
            onClick={() => setActiveFunction('delete')}
          >
            <Trash2 size={18} />
            <span>Delete</span>
          </button>
        </div>
      </div>

      <div className="pipeline-content">
        {message && (
          <div className={`message-alert ${message.type}`}>
            {message.text}
          </div>
        )}
        
        {renderFunctionContent()}
      </div>
    </div>
  )
}

export default RAGPipeline
