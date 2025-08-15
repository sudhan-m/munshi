import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import AudioRecorder from './AudioRecorder'
import AudioSpectrum from './AudioSpectrum'
import { LogOut, User, Mic2, Send } from 'lucide-react'

const Chat = () => {
  const { user, logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [textInput, setTextInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentAudio, setCurrentAudio] = useState(null)
  const [currentAudioUrl, setCurrentAudioUrl] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const addMessage = (message) => {
    setMessages(prev => [...prev, { ...message, id: Date.now() }])
  }

  const handleTextSubmit = (e) => {
    e.preventDefault()
    if (!textInput.trim()) return

    addMessage({
      type: 'text',
      content: textInput,
      sender: 'user',
      timestamp: new Date().toISOString()
    })

    // Simulate AI response
    setIsLoading(true)
    setTimeout(() => {
      addMessage({
        type: 'text',
        content: `I received your message: "${textInput}". This is a demo response from Munshi AI.`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      })
      setIsLoading(false)
    }, 1500)

    setTextInput('')
  }

  const handleAudioMessage = async (audioBlob, duration) => {
    const audioUrl = URL.createObjectURL(audioBlob)
    addMessage({
      type: 'audio',
      content: audioUrl,
      sender: 'user',
      timestamp: new Date().toISOString(),
      duration: duration
    })

    setIsLoading(true)
    // Simulate AI processing
    setTimeout(() => {
      addMessage({
        type: 'text',
        content: 'I received your audio message. Processing speech and generating response...',
        sender: 'assistant',
        timestamp: new Date().toISOString()
      })
      setIsLoading(false)
    }, 2000)
  }

  const playAudio = (audioUrl) => {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
    }
    
    const audio = new Audio(audioUrl)
    setCurrentAudio(audio)
    setCurrentAudioUrl(audioUrl)
    
    audio.play().catch(error => {
      console.error('Error playing audio:', error)
    })
    
    audio.onended = () => {
      setCurrentAudio(null)
      setCurrentAudioUrl(null)
    }
    
    audio.onerror = () => {
      console.error('Audio playback error')
      setCurrentAudio(null)
      setCurrentAudioUrl(null)
    }
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="h-screen flex flex-col bg-dark-950">
      {/* Header */}
      <header className="glass border-b border-white/10 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-r from-primary to-purple-600 rounded-full">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white">Munshi AI</h1>
              <p className="text-sm text-gray-400">Voice Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm text-gray-300">
              <User className="w-4 h-4" />
              <span>{user?.email}</span>
            </div>
            <button
              onClick={logout}
              className="btn-secondary p-2"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-primary/20 to-purple-600/20 rounded-full mb-4">
              <Mic2 className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Welcome to Munshi AI</h3>
            <p className="text-gray-400 max-w-md mx-auto">
              Start a conversation by typing a message or recording your voice. 
              I'm here to help with your questions and tasks.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xs lg:max-w-md ${
              message.sender === 'user' 
                ? 'chat-bubble-user' 
                : 'chat-bubble-assistant'
            }`}>
              {message.type === 'text' ? (
                <p className="text-sm">{message.content}</p>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => playAudio(message.content)}
                      className="flex items-center space-x-2 bg-white/20 hover:bg-white/30 rounded-lg px-3 py-2 transition-colors"
                    >
                      <Mic2 className="w-4 h-4" />
                      <span className="text-sm">Play Audio</span>
                    </button>
                    {message.duration && (
                      <span className="text-xs text-gray-300">
                        {Math.round(message.duration)}s
                      </span>
                    )}
                  </div>
                  {currentAudio && currentAudioUrl === message.content && (
                    <AudioSpectrum audio={currentAudio} />
                  )}
                </div>
              )}
              <div className="text-xs opacity-70 mt-2">
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="chat-bubble-assistant">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm text-gray-300">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-white/10 p-4">
        <div className="flex items-end space-x-4">
          {/* Text Input */}
          <form onSubmit={handleTextSubmit} className="flex-1">
            <div className="flex space-x-2">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type your message..."
                className="input-field flex-1"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!textInput.trim() || isLoading}
                className="btn-primary px-4 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>

          {/* Audio Recorder */}
          <AudioRecorder onAudioRecorded={handleAudioMessage} disabled={isLoading} />
        </div>
      </div>
    </div>
  )
}

export default Chat