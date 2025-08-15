import React, { useState, useRef, useEffect } from 'react'
import { Mic, Square, Play, Pause } from 'lucide-react'

const AudioRecorder = ({ onAudioRecorded, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [recordedAudio, setRecordedAudio] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const streamRef = useRef(null)
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)
  const recordingIntervalRef = useRef(null)
  const levelIntervalRef = useRef(null)
  const audioRef = useRef(null)

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
        setRecordedAudio({ blob: audioBlob, url: URL.createObjectURL(audioBlob) })
        streamRef.current?.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingTime(0)
      setRecordedAudio(null)

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

  const playRecording = () => {
    if (!recordedAudio) return

    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }

    audioRef.current = new Audio(recordedAudio.url)
    audioRef.current.play()
    setIsPlaying(true)

    audioRef.current.onended = () => {
      setIsPlaying(false)
    }
  }

  const pausePlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }

  const sendRecording = () => {
    if (recordedAudio && onAudioRecorded) {
      onAudioRecorded(recordedAudio.blob, recordingTime)
      setRecordedAudio(null)
      setRecordingTime(0)
    }
  }

  const discardRecording = () => {
    if (recordedAudio) {
      URL.revokeObjectURL(recordedAudio.url)
      setRecordedAudio(null)
      setRecordingTime(0)
    }
    if (audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (recordedAudio) {
    return (
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">Recording ready</span>
          <span className="text-sm text-primary">{formatTime(recordingTime)}</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={isPlaying ? pausePlayback : playRecording}
            className="btn-secondary p-2"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          
          <button
            onClick={sendRecording}
            className="btn-primary px-4 py-2 text-sm"
            disabled={disabled}
          >
            Send
          </button>
          
          <button
            onClick={discardRecording}
            className="btn-secondary px-4 py-2 text-sm"
          >
            Discard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center space-y-2">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={disabled}
        className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
          isRecording 
            ? 'bg-red-500 hover:bg-red-600 animate-pulse-ring' 
            : 'bg-gradient-to-r from-primary to-purple-600 hover:from-purple-600 hover:to-primary shadow-lg hover:shadow-xl'
        }`}
        title={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording ? (
          <Square className="w-5 h-5 text-white" />
        ) : (
          <Mic className="w-5 h-5 text-white" />
        )}
        
        {isRecording && (
          <div className="absolute inset-0 rounded-full border-2 border-red-400 animate-pulse-ring"></div>
        )}
      </button>

      {isRecording && (
        <div className="text-center space-y-1">
          <div className="text-sm text-white font-medium">
            {formatTime(recordingTime)}
          </div>
          <div className="w-16 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-100"
              style={{ width: `${Math.min(audioLevel, 100)}%` }}
            />
          </div>
          <div className="text-xs text-gray-400">Recording...</div>
        </div>
      )}
    </div>
  )
}

export default AudioRecorder