import React, { useState, useEffect, useRef } from 'react'
import { Send, Loader } from 'lucide-react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import './Chat.css'

const Chat = () => {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setLoading(true)

    // Add placeholder for streaming response
    const assistantMessageIndex = messages.length + 1
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: '', 
      streaming: true,
      sources: []
    }])

    try {
      const response = await fetch('/api/retrieve/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          top_k: 5
        })
      })

      if (!response.ok) {
        throw new Error('Streaming request failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ''
      let sources = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'sources') {
              sources = data.sources.slice(0, 3)
            } else if (data.type === 'token') {
              accumulatedText += data.content
              // Update the message in real-time
              setMessages(prev => {
                const newMessages = [...prev]
                newMessages[assistantMessageIndex] = {
                  role: 'assistant',
                  content: accumulatedText,
                  streaming: true,
                  sources: sources
                }
                return newMessages
              })
            } else if (data.type === 'done') {
              // Mark streaming as complete
              setMessages(prev => {
                const newMessages = [...prev]
                newMessages[assistantMessageIndex] = {
                  role: 'assistant',
                  content: accumulatedText,
                  streaming: false,
                  sources: sources
                }
                return newMessages
              })
            }
          }
        }
      }
    } catch (error) {
      // Fallback to non-streaming
      try {
        const response = await axios.post('/api/retrieve', {
          query: currentInput,
          top_k: 5
        })

        setMessages(prev => {
          const newMessages = [...prev]
          newMessages[assistantMessageIndex] = {
            role: 'assistant',
            content: response.data.answer,
            sources: response.data.results?.slice(0, 3)
          }
          return newMessages
        })
      } catch (fallbackError) {
        setMessages(prev => {
          const newMessages = [...prev]
          newMessages[assistantMessageIndex] = {
            role: 'assistant',
            content: `Error: ${fallbackError.response?.data?.detail || fallbackError.message}`,
            isError: true
          }
          return newMessages
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-header-icon">🛠️</div>
          <div>
            <div className="chat-header-title">RAGKit Assistant</div>
            <div className="chat-header-subtitle">Powered by TinyLlama • Real-Time Streaming</div>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <h3>Welcome to RAGKit 🛠️</h3>
              <p>Ask questions about your uploaded documents. I'll search through your knowledge base and provide accurate, streaming answers with markdown formatting.</p>
              <div className="chat-suggestions">
                <button onClick={() => setInput('What documents do I have?')}>
                  What documents do I have?
                </button>
                <button onClick={() => setInput('Summarize the key points')}>
                  Summarize the key points
                </button>
                <button onClick={() => setInput('Tell me about...')}>
                  Tell me about...
                </button>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role} ${message.isError ? 'error' : ''} ${message.streaming ? 'streaming' : ''}`}>
              <div className="message-content">
                {message.role === 'assistant' && !message.isError ? (
                  <>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                    {message.streaming && <span className="cursor">▊</span>}
                  </>
                ) : (
                  <>
                    {message.content}
                    {message.streaming && <span className="cursor">▊</span>}
                  </>
                )}
              </div>
              {message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <div className="sources-title">Sources:</div>
                  {message.sources.map((source, idx) => (
                    <div key={idx} className="source-item">
                      <span className="source-doc">{source.document_name || source.meeting_id}</span>
                      <span className="source-score">{(source.similarity_score * 100).toFixed(1)}% match</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-input"
              placeholder="Ask a question about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={1}
              disabled={loading}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat
