import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { MessageSquare, Database, Settings, FileText } from 'lucide-react'
import './Sidebar.css'

const Sidebar = ({ activeTab, setActiveTab }) => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { id: 'chat', label: 'Chat', icon: MessageSquare, path: '/chat' },
    { id: 'knowledge-base', label: 'Knowledge Base', icon: Database, path: '/knowledge-base' },
    { id: 'rag-pipeline', label: 'RAG Pipeline', icon: Settings, path: '/rag-pipeline' },
  ]

  const handleNavigation = (item) => {
    setActiveTab(item.id)
    navigate(item.path)
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <FileText size={20} />
          </div>
          <div className="logo-text">RAGKit</div>
        </div>
        <div className="logo-subtitle">RAG Toolkit</div>
      </div>

      <nav className="nav-menu">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          
          return (
            <div key={item.id} className="nav-item">
              <button
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => handleNavigation(item)}
              >
                <div className="nav-icon">
                  <Icon size={18} />
                </div>
                <span>{item.label}</span>
              </button>
            </div>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>System Online</span>
        </div>
      </div>
    </div>
  )
}

export default Sidebar
