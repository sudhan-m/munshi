import React, { useState, useEffect, useRef } from 'react'
import { Send, Mic, Square, Play, Pause, Volume2, RotateCcw, Sparkles, Award } from 'lucide-react'
import AudioRecorder from './AudioRecorder'

const ChatInterface = () => {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLanguage, setSelectedLanguage] = useState('English')
  const [userId] = useState('demo_user') // In production, get from auth context
  const [showPronunciationMode, setShowPronunciationMode] = useState(false)
  const [currentPractice, setCurrentPractice] = useState(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  
  const messagesEndRef = useRef(null)
  const conversationServiceUrl = 'http://localhost:8007'
  const audioServiceUrl = 'http://localhost:8003'

  const languages = ['English', 'Tamil', 'Malayalam']

  useEffect(() => {
    // Welcome message
    setMessages([{
      id: 1,
      role: 'assistant',
      content: 'Hello! I\'m Munshi, your AI language learning companion. How can I help you practice today?',
      timestamp: new Date(),
      type: 'welcome'
    }])
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const sendMessage = async () => {
    if (!inputMessage.trim()) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await fetch(`${conversationServiceUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          message: inputMessage,
          language: selectedLanguage
        })
      })

      if (response.ok) {
        const result = await response.json()
        if (result.success) {
          const assistantMessage = {
            id: Date.now() + 1,
            role: 'assistant',
            content: result.response,
            timestamp: new Date()
          }
          setMessages(prev => [...prev, assistantMessage])
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting right now. Please try again.',
        timestamp: new Date(),
        type: 'error'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const generatePracticeSentence = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${conversationServiceUrl}/user/${userId}/generate-sentence?language=${selectedLanguage}&difficulty=beginner`)
      
      if (response.ok) {
        const result = await response.json()
        if (result.success) {
          setCurrentPractice(result.sentence_data)
          setShowPronunciationMode(true)
          
          const practiceMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Here's a sentence to practice: "${result.sentence_data.original}"`,
            timestamp: new Date(),
            type: 'practice',
            practiceData: result.sentence_data
          }
          setMessages(prev => [...prev, practiceMessage])
        }
      }
    } catch (error) {
      console.error('Error generating sentence:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAudioRecorded = async (audioBlob) => {
    if (!currentPractice) return

    setIsEvaluating(true)
    
    try {
      // First upload audio to audio service
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.wav')
      formData.append('user_id', userId)

      const uploadResponse = await fetch(`${audioServiceUrl}/audio/upload`, {
        method: 'POST',
        body: formData
      })

      if (uploadResponse.ok) {
        const uploadResult = await uploadResponse.json()
        const audioFileId = uploadResult.id

        // Now evaluate pronunciation
        const evalResponse = await fetch(`${conversationServiceUrl}/evaluate-pronunciation`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            audio_file_id: audioFileId,
            intended_text: currentPractice.original,
            language: selectedLanguage
          })
        })

        if (evalResponse.ok) {
          const evalResult = await evalResponse.json()
          if (evalResult.success) {
            const evaluationMessage = {
              id: Date.now(),
              role: 'assistant',
              content: evalResult.llm_response,
              timestamp: new Date(),
              type: 'evaluation',
              evaluationData: evalResult.evaluation_results
            }
            setMessages(prev => [...prev, evaluationMessage])
          }
        }
      }
    } catch (error) {
      console.error('Error evaluating pronunciation:', error)
      const errorMessage = {
        id: Date.now(),
        role: 'assistant',
        content: 'Sorry, I had trouble evaluating your pronunciation. Please try again.',
        timestamp: new Date(),
        type: 'error'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsEvaluating(false)
    }
  }

  const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user'
    const isSystem = message.type === 'welcome' || message.type === 'error'
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser 
            ? 'bg-gradient-to-r from-primary to-purple-600 text-white' 
            : isSystem
            ? 'bg-gray-800 text-gray-300 border border-gray-700'
            : 'glass-card text-white'
        }`}>
          {/* Message content */}
          <div className="text-sm leading-relaxed">
            {message.content}
          </div>
          
          {/* Practice sentence display */}
          {message.type === 'practice' && message.practiceData && (
            <div className="mt-3 p-3 bg-gray-800/50 rounded-lg">
              <div className="text-lg font-medium text-center mb-2">
                {message.practiceData.original}
              </div>
              {message.practiceData.romanized !== message.practiceData.original && (
                <div className="text-gray-400 text-center text-sm">
                  🔤 {message.practiceData.romanized}
                </div>
              )}
              <div className="flex justify-center mt-2">
                <button className="btn-secondary p-2" title="Play pronunciation guide">
                  <Volume2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          {/* Evaluation results */}
          {message.type === 'evaluation' && message.evaluationData && (
            <div className="mt-3 space-y-3">
              <div className="flex items-center justify-center space-x-4">
                <div className="text-center">
                  <div className={`text-2xl font-bold ${
                    message.evaluationData.metrics.accuracy_percentage >= 90 ? 'text-green-400' :
                    message.evaluationData.metrics.accuracy_percentage >= 70 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {message.evaluationData.metrics.accuracy_percentage}%
                  </div>
                  <div className="text-xs text-gray-400">Accuracy</div>
                </div>
                <Award className="w-6 h-6 text-yellow-500" />
              </div>
              
              {message.evaluationData.pronunciation_errors.length > 0 && (
                <div className="text-xs bg-gray-800/50 rounded p-2">
                  <div className="font-medium text-orange-400 mb-1">Areas to improve:</div>
                  {message.evaluationData.pronunciation_errors.slice(0, 3).map((error, idx) => (
                    <div key={idx} className="text-gray-300">
                      • {error.expected_word} → {error.actual_word}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* Timestamp */}
          <div className="text-xs opacity-60 mt-2">
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900">
      {/* Header */}
      <div className="glass-card p-4 border-b border-gray-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-primary to-purple-600 rounded-full flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Munshi</h1>
              <p className="text-sm text-gray-400">AI Language Learning Companion</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {languages.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
            
            <button
              onClick={generatePracticeSentence}
              disabled={isLoading}
              className="btn-secondary px-4 py-2 text-sm"
              title="Generate practice sentence"
            >
              <Mic className="w-4 h-4 mr-2" />
              Practice
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-scrollbar">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="glass-card rounded-2xl px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-gray-400 text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Pronunciation Practice Mode */}
      {showPronunciationMode && currentPractice && (
        <div className="glass-card p-4 border-t border-gray-700/50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Pronunciation Practice</h3>
            <button
              onClick={() => setShowPronunciationMode(false)}
              className="btn-secondary p-2"
              title="Close practice mode"
            >
              <Square className="w-4 h-4" />
            </button>
          </div>
          
          <div className="text-center space-y-3">
            <div className="text-xl text-white font-medium">
              {currentPractice.original}
            </div>
            {currentPractice.romanized !== currentPractice.original && (
              <div className="text-gray-400">
                🔤 {currentPractice.romanized}
              </div>
            )}
            
            <div className="flex justify-center">
              <AudioRecorder 
                onAudioRecorded={handleAudioRecorded}
                disabled={isEvaluating}
              />
            </div>
            
            {isEvaluating && (
              <div className="text-center text-gray-400">
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                  <span>Evaluating your pronunciation...</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="glass-card p-4 border-t border-gray-700/50">
        <div className="flex items-center space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message or ask for help..."
              disabled={isLoading}
              className="w-full bg-gray-800 border border-gray-700 rounded-full px-4 py-3 text-white placeholder-gray-400 focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
            />
          </div>
          
          <button
            onClick={sendMessage}
            disabled={isLoading || !inputMessage.trim()}
            className="btn-primary p-3 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
            title="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex justify-center mt-3">
          <div className="text-xs text-gray-500">
            💡 Try saying "I want to practice [language]" or "Help me with pronunciation"
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface