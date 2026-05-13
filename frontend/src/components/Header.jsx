import React from 'react'
import { Activity, Database, Cpu } from 'lucide-react'
import './Header.css'

const Header = ({ activeTab, systemStatus }) => {
  const getPageTitle = () => {
    switch(activeTab) {
      case 'chat':
        return { title: 'Chat Interface', subtitle: 'Ask questions about your documents' }
      case 'knowledge-base':
        return { title: 'Knowledge Base', subtitle: 'Upload and manage your documents' }
      case 'rag-pipeline':
        return { title: 'RAG Pipeline', subtitle: 'Manage vector operations and data' }
      default:
        return { title: 'RAGKit', subtitle: 'Simple RAG Toolkit' }
    }
  }

  const { title, subtitle } = getPageTitle()

  return (
    <div className="header">
      <div className="header-content">
        <div className="header-title-section">
          <h1 className="header-title">{title}</h1>
          <p className="header-subtitle">{subtitle}</p>
        </div>
        
        {systemStatus && (
          <div className="header-status">
            <div className="status-badge">
              <Cpu size={14} />
              <span>{systemStatus.current_model || 'Mistral-7B'}</span>
            </div>
            <div className="status-badge">
              <Database size={14} />
              <span>{systemStatus.collection_stats?.total_documents || 0} docs</span>
            </div>
            <div className="status-badge success">
              <Activity size={14} />
              <span>{systemStatus.status || 'healthy'}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Header
