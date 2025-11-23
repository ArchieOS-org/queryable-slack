/**
 * Vector Database Chatbot - React Web App
 * 
 * Mobile-first, elegant, minimal design inspired by Steve Jobs.
 * Uses Context7 best practices for React development.
 */

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Detect API URL based on environment
// For Vercel deployment, use the same domain
// For local development, use localhost:8000
const getApiUrl = () => {
  // Check if we're in production (Vercel)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  // Check if we're on Vercel domain
  const hostname = window.location.hostname
  if (hostname.includes('vercel.app') || hostname.includes('vercel.com')) {
    return `https://${hostname}/api`
  }
  
  // Check if accessing via IP address (local network)
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    return `http://${hostname}:8000`
  }
  
  // Default to localhost for desktop development
  return 'http://localhost:8000'
}

const API_URL = getApiUrl()

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [queryNum, setQueryNum] = useState(0)
  const [apiStatus, setApiStatus] = useState('checking') // 'checking', 'online', 'offline'
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Check API health on mount
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        // Use a shorter timeout for health checks
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 3000) // 3 second timeout
        
        const response = await fetch(`${API_URL}/health`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
          signal: controller.signal,
          mode: 'cors', // Explicitly set CORS mode
        })
        
        clearTimeout(timeoutId)
        
        if (response.ok) {
          setApiStatus('online')
        } else {
          setApiStatus('offline')
        }
      } catch (error) {
        console.error('API health check failed:', error)
        // Don't set offline immediately - might be a temporary network issue
        // Only set offline if it's a clear connection error
        if (error.name === 'AbortError' || error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          setApiStatus('offline')
        }
      }
    }
    
    // Initial check
    checkApiHealth()
    // Check every 5 seconds (more frequent)
    const interval = setInterval(checkApiHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)
    setQueryNum(prev => prev + 1)

    // Add user message immediately
    const newUserMessage = {
      id: Date.now(),
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newUserMessage])

    try {
      // Check if API is reachable first
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout for long queries
      
      const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage,
          use_thinking: true,
          use_hybrid: false
          // use_refinement removed - query understanding now handled by system prompt
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = `HTTP error! status: ${response.status}`
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.detail || errorMessage
        } catch {
          errorMessage = errorText || errorMessage
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      
      // Add assistant response
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.response,
        refined_query: data.refined_query,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMessage])
      setApiStatus('online') // Mark as online on successful request
    } catch (error) {
      console.error('Error:', error)
      let errorMessage = error.message
      
      // Provide helpful error messages
      if (error.name === 'AbortError') {
        errorMessage = 'Request timed out. The query may be taking too long. Please try again.'
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError') || error.message.includes('Network request failed')) {
        errorMessage = `Cannot connect to API at ${API_URL}. Make sure the FastAPI backend is running. Start it with: python -m uvicorn web_api:app --reload --port 8000`
        setApiStatus('offline')
      } else if (error.message.includes('CORS')) {
        errorMessage = 'CORS error. Check backend CORS configuration.'
      }
      
      const errorMsg = {
        id: Date.now() + 1,
        type: 'error',
        content: `Error: ${errorMessage}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleClear = () => {
    setMessages([])
    setQueryNum(0)
    inputRef.current?.focus()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#ffffff', fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif' }}>
      {/* Header */}
      <header style={{ flexShrink: 0, borderBottom: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}>
        <div style={{ maxWidth: '896px', margin: '0 auto', padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ 
                width: '8px', 
                height: '8px', 
                backgroundColor: apiStatus === 'online' ? '#10b981' : apiStatus === 'offline' ? '#ef4444' : '#f59e0b', 
                borderRadius: '50%',
                animation: apiStatus === 'checking' ? 'pulse 2s ease-in-out infinite' : 'none'
              }}></div>
              <h1 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>Vector DB Chatbot</h1>
              {apiStatus === 'offline' && (
                <span style={{ fontSize: '12px', color: '#ef4444', marginLeft: '8px' }}>API Offline</span>
              )}
            </div>
            <button
              onClick={handleClear}
              style={{ fontSize: '14px', color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
              onMouseOver={(e) => e.target.style.color = '#374151'}
              onMouseOut={(e) => e.target.style.color = '#6b7280'}
            >
              Clear
            </button>
          </div>
        </div>
      </header>

      {/* Messages area */}
      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <div style={{ maxWidth: '896px', margin: '0 auto', padding: '24px 16px' }}>
          {messages.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center', padding: '16px' }}>
              <div style={{ width: '64px', height: '64px', backgroundColor: '#f3f4f6', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>
                <svg style={{ width: '32px', height: '32px', color: '#9ca3af' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>Start a conversation</h2>
              <p style={{ color: '#6b7280', fontSize: '14px', maxWidth: '384px', marginBottom: '16px' }}>
                Ask questions about your vector database. Each query is a fresh call with thinking mode enabled.
              </p>
              {apiStatus === 'offline' && (
                <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '12px', maxWidth: '400px', marginTop: '16px' }}>
                  <p style={{ color: '#991b1b', fontSize: '14px', margin: 0 }}>
                    <strong>API is offline.</strong> Make sure the FastAPI backend is running:
                  </p>
                  <code style={{ display: 'block', marginTop: '8px', padding: '8px', backgroundColor: '#ffffff', borderRadius: '4px', fontSize: '12px', color: '#111827' }}>
                    python -m uvicorn web_api:app --reload --port 8000
                  </code>
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isLoading && (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <div style={{ flexShrink: 0, width: '32px', height: '32px', backgroundColor: '#f3f4f6', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ width: '8px', height: '8px', backgroundColor: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.5s ease-in-out infinite' }}></div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ backgroundColor: '#f9fafb', borderRadius: '16px', borderTopLeftRadius: '4px', padding: '12px 16px' }}>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <div style={{ width: '8px', height: '8px', backgroundColor: '#d1d5db', borderRadius: '50%', animation: 'bounce 1.4s ease-in-out infinite' }}></div>
                        <div style={{ width: '8px', height: '8px', backgroundColor: '#d1d5db', borderRadius: '50%', animation: 'bounce 1.4s ease-in-out infinite', animationDelay: '0.2s' }}></div>
                        <div style={{ width: '8px', height: '8px', backgroundColor: '#d1d5db', borderRadius: '50%', animation: 'bounce 1.4s ease-in-out infinite', animationDelay: '0.4s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input area */}
      <footer style={{ flexShrink: 0, borderTop: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}>
        <div style={{ maxWidth: '896px', margin: '0 auto', padding: '16px' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'flex-end', gap: '12px' }}>
            <div style={{ flex: 1 }}>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={apiStatus === 'offline' ? 'API offline - start backend first...' : 'Ask a question...'}
                disabled={isLoading || apiStatus === 'offline'}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  backgroundColor: apiStatus === 'offline' ? '#f3f4f6' : '#f9fafb',
                  border: '1px solid #e5e7eb',
                  borderRadius: '16px',
                  fontSize: '16px',
                  outline: 'none',
                  transition: 'all 0.2s',
                  opacity: (isLoading || apiStatus === 'offline') ? 0.5 : 1,
                  cursor: (isLoading || apiStatus === 'offline') ? 'not-allowed' : 'text'
                }}
                onFocus={(e) => {
                  if (apiStatus !== 'offline') {
                    e.target.style.borderColor = '#3b82f6'
                    e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)'
                  }
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#e5e7eb'
                  e.target.style.boxShadow = 'none'
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && apiStatus !== 'offline') {
                    e.preventDefault()
                    handleSubmit(e)
                  }
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading || apiStatus === 'offline'}
              style={{
                flexShrink: 0,
                width: '48px',
                height: '48px',
                backgroundColor: '#3b82f6',
                color: '#ffffff',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: 'none',
                cursor: (!input.trim() || isLoading || apiStatus === 'offline') ? 'not-allowed' : 'pointer',
                opacity: (!input.trim() || isLoading || apiStatus === 'offline') ? 0.5 : 1,
                transition: 'all 0.2s',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
              }}
              onMouseOver={(e) => {
                if (!isLoading && input.trim() && apiStatus !== 'offline') {
                  e.target.style.backgroundColor = '#2563eb'
                  e.target.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)'
                }
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = '#3b82f6'
                e.target.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)'
              }}
            >
              {isLoading ? (
                <div style={{ width: '20px', height: '20px', border: '2px solid #ffffff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
              ) : (
                <svg style={{ width: '20px', height: '20px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </form>
        </div>
      </footer>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.type === 'user'
  const isError = message.type === 'error'

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', flexDirection: isUser ? 'row-reverse' : 'row' }}>
      {/* Avatar */}
      <div style={{
        flexShrink: 0,
        width: '32px',
        height: '32px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isUser ? '#3b82f6' : isError ? '#fee2e2' : '#f3f4f6'
      }}>
        {isUser ? (
          <svg style={{ width: '20px', height: '20px', color: '#ffffff' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : isError ? (
          <svg style={{ width: '20px', height: '20px', color: '#ef4444' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg style={{ width: '20px', height: '20px', color: '#4b5563' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        )}
      </div>

      {/* Message content */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
        <div style={{
          borderRadius: '16px',
          padding: '12px 16px',
          backgroundColor: isUser ? '#3b82f6' : isError ? '#fef2f2' : '#f9fafb',
          color: isUser ? '#ffffff' : isError ? '#991b1b' : '#111827',
          borderTopLeftRadius: isUser ? '16px' : '4px',
          borderTopRightRadius: isUser ? '4px' : '16px',
          border: isError ? '1px solid #fecaca' : 'none',
          fontSize: '14px',
          lineHeight: '1.5'
        }}>
          {isUser ? (
            <p style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{message.content}</p>
          ) : isError ? (
            <div>
              <p style={{ margin: 0, marginBottom: '8px', fontWeight: '600' }}>{message.content}</p>
              {message.content.includes('Cannot connect') && (
                <div style={{ marginTop: '8px', padding: '8px', backgroundColor: '#ffffff', borderRadius: '4px', fontSize: '12px' }}>
                  <p style={{ margin: 0, marginBottom: '4px' }}>To start the backend:</p>
                  <code style={{ display: 'block', padding: '4px', backgroundColor: '#f3f4f6', borderRadius: '2px' }}>
                    python -m uvicorn web_api:app --reload --port 8000
                  </code>
                </div>
              )}
            </div>
          ) : (
            <div>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p style={{ marginBottom: '12px', marginTop: 0 }}>{children}</p>,
                  h1: ({ children }) => <h1 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', marginTop: '16px' }}>{children}</h1>,
                  h2: ({ children }) => <h2 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px', marginTop: '12px' }}>{children}</h2>,
                  h3: ({ children }) => <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px', marginTop: '8px' }}>{children}</h3>,
                  ul: ({ children }) => <ul style={{ listStyleType: 'disc', paddingLeft: '20px', marginBottom: '12px' }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ listStyleType: 'decimal', paddingLeft: '20px', marginBottom: '12px' }}>{children}</ol>,
                  li: ({ children }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
                  code: ({ children }) => <code style={{ backgroundColor: '#e5e7eb', padding: '2px 6px', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace' }}>{children}</code>,
                  pre: ({ children }) => <pre style={{ backgroundColor: '#e5e7eb', padding: '12px', borderRadius: '8px', overflowX: 'auto', marginBottom: '12px', fontSize: '12px' }}>{children}</pre>,
                  blockquote: ({ children }) => <blockquote style={{ borderLeft: '4px solid #d1d5db', paddingLeft: '12px', fontStyle: 'italic', margin: '12px 0' }}>{children}</blockquote>,
                  strong: ({ children }) => <strong style={{ fontWeight: '600' }}>{children}</strong>,
                  em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        {message.refined_query && message.refined_query !== message.content && (
          <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px', paddingLeft: '4px', paddingRight: '4px' }}>
            Refined: {message.refined_query}
          </p>
        )}
      </div>
    </div>
  )
}

export default App
