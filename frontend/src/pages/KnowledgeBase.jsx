import React, { useState, useEffect } from 'react'
import { Upload, FileText, Trash2, Loader, CheckCircle, AlertCircle } from 'lucide-react'
import axios from 'axios'
import './KnowledgeBase.css'

const KnowledgeBase = () => {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchDocuments()
    fetchStats()
  }, [])

  const fetchDocuments = async () => {
    try {
      const response = await axios.get('/api/documents')
      setDocuments(response.data.documents || [])
    } catch (error) {
      console.error('Failed to fetch documents:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files)
    if (files.length === 0) return

    setUploading(true)
    setUploadStatus(null)

    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      setUploadStatus({
        type: 'success',
        message: `Successfully uploaded ${files.length} document(s)`,
        details: response.data
      })

      fetchDocuments()
      fetchStats()
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `Upload failed: ${error.response?.data?.detail || error.message}`
      })
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    try {
      await axios.delete(`/api/documents/${docId}`)
      setUploadStatus({
        type: 'success',
        message: 'Document deleted successfully'
      })
      fetchDocuments()
      fetchStats()
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `Delete failed: ${error.response?.data?.detail || error.message}`
      })
    }
  }

  return (
    <div className="knowledge-base-page">
      <div className="kb-header">
        <div className="kb-stats">
          <div className="stat-card">
            <div className="stat-label">Total Documents</div>
            <div className="stat-value">{stats?.total_documents || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Chunks</div>
            <div className="stat-value">{stats?.total_chunks || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Storage Used</div>
            <div className="stat-value">{stats?.storage_mb || 0} MB</div>
          </div>
        </div>
      </div>

      <div className="kb-upload-section">
        <div className="upload-card">
          <div className="upload-icon">
            <Upload size={48} />
          </div>
          <h3>Upload Documents</h3>
          <p>Support for PDF, Word, JSON, TXT, and more</p>
          <label className="upload-button">
            <input
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.json,.csv,.md"
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            {uploading ? (
              <>
                <Loader className="spinner-icon" size={18} />
                Uploading...
              </>
            ) : (
              <>
                <Upload size={18} />
                Choose Files
              </>
            )}
          </label>
        </div>

        {uploadStatus && (
          <div className={`status-message ${uploadStatus.type}`}>
            {uploadStatus.type === 'success' ? (
              <CheckCircle size={20} />
            ) : (
              <AlertCircle size={20} />
            )}
            <div>
              <div className="status-title">{uploadStatus.message}</div>
              {uploadStatus.details && (
                <div className="status-details">
                  {uploadStatus.details.total_chunks} chunks created
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="kb-documents">
        <h3>Your Documents</h3>
        {documents.length === 0 ? (
          <div className="empty-state">
            <FileText size={48} />
            <p>No documents uploaded yet</p>
            <p className="empty-subtitle">Upload your first document to get started</p>
          </div>
        ) : (
          <div className="documents-grid">
            {documents.map((doc) => (
              <div key={doc.id} className="document-card">
                <div className="document-icon">
                  <FileText size={24} />
                </div>
                <div className="document-info">
                  <div className="document-name">{doc.name}</div>
                  <div className="document-meta">
                    <span>{doc.chunks} chunks</span>
                    <span>{doc.category || 'General'}</span>
                  </div>
                  <div className="document-date">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  className="delete-button"
                  onClick={() => handleDeleteDocument(doc.id)}
                  title="Delete document"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default KnowledgeBase
