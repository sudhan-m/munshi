import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import AudioSpectrum from './AudioSpectrum'
import ChallengeBox from './ChallengeBox'
import { LogOut, User, Mic2, Send, Mic, Square } from 'lucide-react'

const Chat = () => {
  const { user, logout, token } = useAuth()
  const [messages, setMessages] = useState([])
  const [textInput, setTextInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentAudio, setCurrentAudio] = useState(null)
  const [currentAudioUrl, setCurrentAudioUrl] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  const [selectedLanguage, setSelectedLanguage] = useState(null)
  const [isLanguageSelected, setIsLanguageSelected] = useState(false)
  const [currentChallenge, setCurrentChallenge] = useState(null)

  const messagesEndRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)
  const recordingIntervalRef = useRef(null)
  const levelIntervalRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const supportedLanguages = ['English', 'Malayalam', 'Tamil', 'Hindi']

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Show welcome message on mount
  useEffect(() => {
    if (messages.length === 0) {
      setTimeout(() => {
        addMessage({
          type: 'text',
          content: `Hello ${user?.email?.split('@')[0] || 'there'}! 👋\n\nWelcome to Munshi, your AI language learning companion.\n\nWhich language would you like to practice today? I can help you with:\n• ${supportedLanguages.join('\n• ')}\n\nJust tell me which language you'd like to learn!`,
          sender: 'assistant',
          timestamp: new Date().toISOString()
        })
      }, 500)
    }
  }, []) // Updated: Force new build hash

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
      if (levelIntervalRef.current) {
        clearInterval(levelIntervalRef.current)
      }
    }
  }, [])

  const addMessage = (message) => {
    setMessages(prev => [...prev, { ...message, id: Date.now() }])
  }

  const detectLanguage = (text) => {
    const normalizedText = text.toLowerCase().trim()

    // Check for exact or partial matches
    for (const lang of supportedLanguages) {
      if (normalizedText.includes(lang.toLowerCase())) {
        return lang
      }
    }

    // Check for common variations
    if (normalizedText.includes('mal') || normalizedText.includes('malayalam')) return 'Malayalam'
    if (normalizedText.includes('tam') || normalizedText.includes('tamil')) return 'Tamil'
    if (normalizedText.includes('eng') || normalizedText.includes('english')) return 'English'
    if (normalizedText.includes('hin') || normalizedText.includes('hindi')) return 'Hindi'

    return null
  }

  const parsePracticeSentence = (text) => {
    console.log('Parsing text for practice sentence:', text)

    // Look for practice sentence patterns
    // Pattern 1: **"Sentence"** with quotes
    let boldQuoteMatch = text.match(/\*\*"([^"]+)"\*\*/)
    if (boldQuoteMatch) {
      const sentence = boldQuoteMatch[1]
      const romanMatch = text.match(/\(([^)]+)\)/)
      console.log('Found pattern 1 (with quotes):', sentence)
      return {
        original: sentence,
        romanized: romanMatch ? romanMatch[1] : sentence,
        english: 'Practice pronunciation'
      }
    }

    // Pattern 2: **Sentence** without quotes
    boldQuoteMatch = text.match(/\*\*([^*]+)\*\*/)
    if (boldQuoteMatch) {
      const sentence = boldQuoteMatch[1].trim()
      const romanMatch = text.match(/\(([^)]+)\)/)
      console.log('Found pattern 2 (without quotes):', sentence)
      return {
        original: sentence,
        romanized: romanMatch ? romanMatch[1] : sentence,
        english: 'Practice pronunciation'
      }
    }

    // Pattern 3: Try saying: "Sentence"
    const trySayingMatch = text.match(/[Tt]ry saying.*?["""]([^"""]+)["""]/s)
    if (trySayingMatch) {
      const sentence = trySayingMatch[1]
      const romanMatch = text.match(/\(([^)]+)\)/)
      console.log('Found pattern 3 (try saying):', sentence)
      return {
        original: sentence,
        romanized: romanMatch ? romanMatch[1] : sentence,
        english: 'Practice pronunciation'
      }
    }

    console.log('No practice sentence pattern found')
    return null
  }

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    if (!textInput.trim()) return

    const userMessage = textInput.trim()

    addMessage({
      type: 'text',
      content: userMessage,
      sender: 'user',
      timestamp: new Date().toISOString()
    })

    setTextInput('')
    setIsLoading(true)

    // Check if user hasn't selected a language yet
    if (!isLanguageSelected) {
      const detectedLang = detectLanguage(userMessage)

      if (detectedLang) {
        setSelectedLanguage(detectedLang)
        setIsLanguageSelected(true)

        setTimeout(() => {
          addMessage({
            type: 'text',
            content: `Great! I'll help you learn ${detectedLang}. 🎉\n\nLet's get started! You can:\n• Type messages to practice conversation\n• Ask me to generate practice sentences\n• Use the challenge box to practice pronunciation\n\nWhat would you like to do?`,
            sender: 'assistant',
            timestamp: new Date().toISOString()
          })
          setIsLoading(false)
        }, 800)
      } else {
        setTimeout(() => {
          addMessage({
            type: 'text',
            content: `I'm not sure which language you meant. 🤔\n\nPlease choose from one of these supported languages:\n${supportedLanguages.map(lang => `• ${lang}`).join('\n')}\n\nJust type the name of the language you'd like to learn!`,
            sender: 'assistant',
            timestamp: new Date().toISOString()
          })
          setIsLoading(false)
        }, 800)
      }
      return
    }

    // If language is already selected, handle normal conversation
    try {
      const response = await fetch('/api/conversation/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: user?.email,
          message: userMessage,
          language: selectedLanguage
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const result = await response.json()

      if (result.success && result.response) {
        // Try to parse as JSON first
        let messageContent = result.response
        let isPractice = false

        try {
          const jsonResponse = JSON.parse(result.response)
          console.log('Parsed JSON response:', jsonResponse)
          if (jsonResponse.type === 'practice' && jsonResponse.sentence) {
            // Create practice challenge directly
            isPractice = true
            const challengeData = {
              original: jsonResponse.sentence,
              romanized: jsonResponse.romanized || jsonResponse.sentence,
              english: jsonResponse.translation || 'Practice pronunciation'
            }

            console.log('Setting challenge:', challengeData)
            console.log('isLanguageSelected:', isLanguageSelected, 'selectedLanguage:', selectedLanguage)

            addMessage({
              type: 'practice',
              content: jsonResponse.sentence,
              romanized: jsonResponse.romanized || jsonResponse.sentence,
              translation: jsonResponse.translation || 'Practice pronunciation',
              sender: 'assistant',
              timestamp: new Date().toISOString()
            })

            // Set as current challenge
            setCurrentChallenge(challengeData)
            setIsLoading(false)
            return
          }
        } catch (e) {
          console.log('JSON parse error or not a practice message:', e)
          // Not JSON, treat as regular text
        }

        addMessage({
          type: 'text',
          content: messageContent,
          sender: 'assistant',
          timestamp: new Date().toISOString()
        })
      } else {
        throw new Error(result.error || 'Unknown error')
      }

      setIsLoading(false)
    } catch (error) {
      console.error('Error sending message:', error)
      addMessage({
        type: 'text',
        content: 'Sorry, I encountered an error. Please try again.',
        sender: 'assistant',
        timestamp: new Date().toISOString()
      })
      setIsLoading(false)
    }
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

    try {
      // Send audio to ASR service
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.wav')

      const response = await fetch('/api/audio/process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (!response.ok) {
        throw new Error('ASR processing failed')
      }

      const result = await response.json()

      // Add transcribed text message
      if (result.transcription) {
        addMessage({
          type: 'text',
          content: `Transcription: "${result.transcription}"`,
          sender: 'assistant',
          timestamp: new Date().toISOString()
        })
      }

      setIsLoading(false)
    } catch (error) {
      console.error('Error processing audio:', error)
      addMessage({
        type: 'text',
        content: 'Sorry, I could not process your audio. Please try again.',
        sender: 'assistant',
        timestamp: new Date().toISOString()
      })
      setIsLoading(false)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      })

      streamRef.current = stream
      audioChunksRef.current = []

      // Set up audio analysis for level monitoring
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      analyserRef.current.fftSize = 256

      // Set up media recorder
      mediaRecorderRef.current = new MediaRecorder(stream)
      mediaRecorderRef.current.ondataavailable = (event) => audioChunksRef.current.push(event.data)
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        handleAudioMessage(audioBlob, recordingTime)
        streamRef.current?.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingTime(0)

      // Start timer and level monitoring
      recordingIntervalRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000)
      startAudioLevelMonitoring()

    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Could not access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(recordingIntervalRef.current)
      clearInterval(levelIntervalRef.current)
      setAudioLevel(0)
      setRecordingTime(0)
    }
  }

  const startAudioLevelMonitoring = () => {
    if (!analyserRef.current) return

    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    levelIntervalRef.current = setInterval(() => {
      analyserRef.current.getByteFrequencyData(dataArray)
      const average = dataArray.reduce((a, b) => a + b) / bufferLength
      const percentage = (average / 255) * 100
      setAudioLevel(percentage)
    }, 100)
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
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

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      {/* Header */}
      <header className="glass border-b border-white/10 p-4 sticky top-0 z-10 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-r from-primary to-purple-600 rounded-full">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white">Munshi AI</h1>
              <p className="text-sm text-gray-400">
                {selectedLanguage ? `Learning ${selectedLanguage}` : 'Language Learning Assistant'}
              </p>
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

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-4 space-y-4">
          {/* Messages Area */}
          <div className="space-y-4">
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
              ) : message.type === 'practice' ? (
                <div className="space-y-2">
                  <div className="text-lg font-semibold">{message.content}</div>
                  <div className="text-sm text-gray-300">🔤 {message.romanized}</div>
                  <div className="text-xs text-gray-400">{message.translation}</div>
                </div>
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
                {formatTimestamp(message.timestamp)}
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
        </div>
      </div>

      {/* Challenge Box - Fixed at bottom */}
      {isLanguageSelected && currentChallenge && (
        <div className="border-t border-white/10 bg-slate-900/90 backdrop-blur-xl">
          <div className="max-w-5xl mx-auto p-4">
            <ChallengeBox
              token={token}
              language={selectedLanguage}
              initialChallenge={currentChallenge}
              onClearChallenge={() => setCurrentChallenge(null)}
              onNewChallenge={(sentence) => {
                setCurrentChallenge(sentence)
              }}
            />
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-white/10 p-4 bg-slate-900/50 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto">
        <form onSubmit={handleTextSubmit} className="flex items-center space-x-2">
          {/* Text Input */}
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Type your message..."
            className="input-field flex-1"
            disabled={isLoading}
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!textInput.trim() || isLoading || isRecording}
            className="btn-primary px-4 py-3 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        </div>
      </div>
    </div>
  )
}

export default Chat