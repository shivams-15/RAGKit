import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Chat from './pages/Chat'
import KnowledgeBase from './pages/KnowledgeBase'
import RAGPipeline from './pages/RAGPipeline'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('chat')
  const [systemStatus, setSystemStatus] = useState(null)

  useEffect(() => {
    // Fetch system health on mount
    fetchSystemHealth()
    
    // Poll every 30 seconds
    const interval = setInterval(fetchSystemHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchSystemHealth = async () => {
    try {
      const response = await fetch('/api/health')
      const data = await response.json()
      setSystemStatus(data)
    } catch (error) {
      console.error('Failed to fetch system health:', error)
    }
  }

  return (
    <Router>
      <div className="app">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <div className="main-content">
          <Header activeTab={activeTab} systemStatus={systemStatus} />
          <div className="content-area">
            <Routes>
              <Route path="/chat" element={<Chat />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
              <Route path="/rag-pipeline" element={<RAGPipeline />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  )
}

export default App
