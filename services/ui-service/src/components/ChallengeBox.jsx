import React, { useState, useRef, useEffect } from 'react'
import { Mic, Square, Volume2, RefreshCw, X } from 'lucide-react'

const ChallengeBox = ({ token, language, initialChallenge, onNewChallenge, onClearChallenge }) => {
  const [challenge, setChallenge] = useState(initialChallenge || null)
  const [isLoading, setIsLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  const [evaluation, setEvaluation] = useState(null)

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)
  const recordingIntervalRef = useRef(null)
  const levelIntervalRef = useRef(null)

  // Update challenge when initialChallenge changes
  useEffect(() => {
    if (initialChallenge) {
      setChallenge(initialChallenge)
      setEvaluation(null)
    }
  }, [initialChallenge])

  const generateChallenge = async () => {
    if (!language) {
      alert('Please select a language first by chatting with the assistant')
      return
    }

    setIsLoading(true)
    setEvaluation(null)

    try {
      const response = await fetch(`/api/conversation/user/challenge/generate-sentence?language=${language}&difficulty=beginner`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to generate challenge')
      }

      const result = await response.json()

      if (result.success && result.sentence) {
        setChallenge({
          original: result.sentence.sentence,
          romanized: result.sentence.romanization || result.sentence.sentence,
          english: result.sentence.english_meaning || 'Practice pronunciation'
        })
        if (onNewChallenge) {
          onNewChallenge(result.sentence)
        }
      } else {
        throw new Error(result.error || 'Failed to generate sentence')
      }
    } catch (error) {
      console.error('Error generating challenge:', error)
      alert('Failed to generate challenge. Please try again.')
    } finally {
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

      // Set up audio analysis
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
        handleAudioSubmission(audioBlob)
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
      alert('Could not access microphone. Please check permissions and ensure you are using HTTPS.')
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

  const handleAudioSubmission = async (audioBlob) => {
    if (!challenge) return

    setIsLoading(true)

    try {
      // First, send to ASR service for transcription
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.wav')

      const asrResponse = await fetch('/api/audio/process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (!asrResponse.ok) {
        throw new Error('ASR processing failed')
      }

      const asrResult = await asrResponse.json()

      // TODO: Evaluate pronunciation against expected text
      // For now, just show the transcription
      setEvaluation({
        transcription: asrResult.transcription,
        accuracy: null,
        feedback: 'Transcription received. Pronunciation evaluation coming soon!'
      })

    } catch (error) {
      console.error('Error processing audio:', error)
      alert('Failed to process audio. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const speak = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language === 'Malayalam' ? 'ml-IN' :
                       language === 'Tamil' ? 'ta-IN' :
                       language === 'Hindi' ? 'hi-IN' : 'en-US'
      window.speechSynthesis.speak(utterance)
    }
  }

  return (
    <div className="glass-card mb-6 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white flex items-center space-x-2">
          <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
          <span>Pronunciation Practice</span>
        </h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={generateChallenge}
            disabled={isLoading || !language}
            className="btn-secondary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Generate new challenge"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          {onClearChallenge && (
            <button
              onClick={onClearChallenge}
              className="btn-secondary p-2"
              title="Close challenge"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {!language && (
        <div className="text-center py-8 text-gray-400">
          <p>Please select a language by chatting with the assistant first</p>
        </div>
      )}

      {language && !challenge && !isLoading && (
        <div className="text-center py-8">
          <button
            onClick={generateChallenge}
            className="btn-primary"
          >
            Generate Challenge Sentence
          </button>
        </div>
      )}

      {isLoading && (
        <div className="text-center py-8">
          <div className="flex items-center justify-center space-x-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
            <span className="text-sm text-gray-300">Loading...</span>
          </div>
        </div>
      )}

      {challenge && (
        <div className="space-y-4">
          {/* Challenge Sentence */}
          <div className="bg-gradient-to-r from-primary/20 to-purple-600/20 rounded-lg p-6 border border-primary/30">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <p className="text-xs text-gray-400 mb-1">Challenge Sentence</p>
                <p className="text-2xl font-semibold text-white mb-3">{challenge.original}</p>
              </div>
              <button
                onClick={() => speak(challenge.original)}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
                title="Listen to pronunciation"
              >
                <Volume2 className="w-5 h-5 text-white" />
              </button>
            </div>

            {/* Romanization */}
            {challenge.romanized !== challenge.original && (
              <div className="mb-3">
                <p className="text-xs text-gray-400 mb-1">Romanization</p>
                <p className="text-lg text-gray-300 font-mono">{challenge.romanized}</p>
              </div>
            )}

            {/* English Meaning */}
            <div>
              <p className="text-xs text-gray-400 mb-1">English Meaning</p>
              <p className="text-sm text-gray-300">{challenge.english}</p>
            </div>
          </div>

          {/* Recording Section */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={isLoading}
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
                    isRecording
                      ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                      : 'bg-gradient-to-r from-primary to-purple-600 hover:from-purple-600 hover:to-primary shadow-lg hover:shadow-xl'
                  }`}
                  title={isRecording ? 'Stop recording' : 'Start recording'}
                >
                  {isRecording ? (
                    <Square className="w-5 h-5 text-white" />
                  ) : (
                    <Mic className="w-5 h-5 text-white" />
                  )}
                </button>

                {isRecording ? (
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="text-sm text-red-500 font-medium">{formatTime(recordingTime)}</span>
                    </div>
                    <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-100"
                        style={{ width: `${Math.min(audioLevel, 100)}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <span className="text-sm text-gray-300">Click to record your pronunciation</span>
                )}
              </div>
            </div>
          </div>

          {/* Evaluation Results */}
          {evaluation && (
            <div className="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-lg p-4 border border-green-500/30">
              <h3 className="text-sm font-semibold text-white mb-2">Results</h3>
              <div className="space-y-2">
                <div>
                  <p className="text-xs text-gray-400">Your pronunciation:</p>
                  <p className="text-sm text-white">{evaluation.transcription}</p>
                </div>
                {evaluation.accuracy !== null && (
                  <div>
                    <p className="text-xs text-gray-400">Accuracy:</p>
                    <p className="text-sm text-white">{evaluation.accuracy}%</p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-gray-400">Feedback:</p>
                  <p className="text-sm text-gray-300">{evaluation.feedback}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ChallengeBox
