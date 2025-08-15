import React, { useEffect, useRef, useState } from 'react'

const AudioSpectrum = ({ audio, className = '' }) => {
  const canvasRef = useRef(null)
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)
  const sourceRef = useRef(null)
  const animationRef = useRef(null)
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!audio) return

    const setupAudioAnalysis = async () => {
      try {
        console.log('Setting up audio analysis for:', audio.src)
        setError(null)
        
        // Don't recreate if already exists
        if (!audioContextRef.current) {
          // Create audio context
          audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
          console.log('Created new AudioContext')
        }
        
        // Resume context if suspended (required by some browsers)
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume()
          console.log('Resumed AudioContext')
        }
        
        // Don't recreate analyser if it exists
        if (!analyserRef.current) {
          analyserRef.current = audioContextRef.current.createAnalyser()
          analyserRef.current.fftSize = 256 // Increased for better resolution
          analyserRef.current.smoothingTimeConstant = 0.3 // Less smoothing for more responsive
          console.log('Created analyser with fftSize:', analyserRef.current.fftSize)
        }
        
        // Create source only once per audio element
        if (!sourceRef.current) {
          try {
            sourceRef.current = audioContextRef.current.createMediaElementSource(audio)
            sourceRef.current.connect(analyserRef.current)
            analyserRef.current.connect(audioContextRef.current.destination)
            console.log('Connected audio source to analyser')
          } catch (sourceError) {
            // If source already exists for this element, that's okay
            console.log('Source connection error (may be already connected):', sourceError.message)
          }
        }
        
        setIsActive(true)
        startVisualization()
        console.log('Audio analysis setup complete')
      } catch (error) {
        console.error('Error setting up audio analysis:', error)
        setError(error.message)
      }
    }

    const handlePlay = () => {
      console.log('Audio play event triggered')
      setupAudioAnalysis()
    }

    const handlePause = () => {
      setIsActive(false)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }

    const handleEnded = () => {
      setIsActive(false)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      // Clear canvas
      const canvas = canvasRef.current
      if (canvas) {
        const ctx = canvas.getContext('2d')
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      }
    }

    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('ended', handleEnded)
      
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      
      // Clean up refs when component unmounts or audio changes
      sourceRef.current = null
      analyserRef.current = null
      
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
      }
    }
  }, [audio])

  const startVisualization = () => {
    const canvas = canvasRef.current
    if (!canvas || !analyserRef.current) {
      console.log('Canvas or analyser not ready:', { canvas: !!canvas, analyser: !!analyserRef.current })
      return
    }

    console.log('Starting visualization with canvas:', canvas.width, 'x', canvas.height)
    const ctx = canvas.getContext('2d')
    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    console.log('Buffer length:', bufferLength)

    const draw = () => {
      if (!isActive) {
        console.log('Visualization stopped - not active')
        return
      }

      analyserRef.current.getByteFrequencyData(dataArray)

      // Log data for debugging (only first few values)
      const sampleData = Array.from(dataArray.slice(0, 8))
      if (sampleData.some(val => val > 0)) {
        console.log('Audio data sample:', sampleData)
      }

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Calculate bar dimensions
      const barCount = 32 // Number of bars to display
      const barWidth = canvas.width / barCount
      const barSpacing = 1

      // Draw spectrum bars
      let drawnBars = 0
      let maxValue = 0
      const hasData = dataArray.some(val => val > 0)
      
      // If no real data, show a test pattern
      if (!hasData) {
        // Draw test bars to verify canvas is working
        for (let i = 0; i < barCount; i++) {
          const testHeight = (Math.sin(Date.now() * 0.01 + i * 0.5) + 1) * 15 + 5
          ctx.fillStyle = '#4ade80' // Green for test pattern
          ctx.fillRect(
            i * barWidth + barSpacing / 2,
            canvas.height - testHeight,
            barWidth - barSpacing,
            testHeight
          )
        }
      } else {
        // Draw real frequency data
        for (let i = 0; i < barCount; i++) {
          const dataIndex = Math.floor((i / barCount) * bufferLength)
          const value = dataArray[dataIndex]
          maxValue = Math.max(maxValue, value)
          const barHeight = Math.max(2, (value / 255) * canvas.height) // Minimum height of 2px

          if (barHeight > 1) { // Only count bars with visible height
            drawnBars++
          }

          // Create gradient
          const gradient = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight)
          gradient.addColorStop(0, '#8b5cf6') // Primary color
          gradient.addColorStop(0.5, '#a855f7') // Purple
          gradient.addColorStop(1, '#06b6d4') // Secondary color

          ctx.fillStyle = gradient
          ctx.fillRect(
            i * barWidth + barSpacing / 2,
            canvas.height - barHeight,
            barWidth - barSpacing,
            barHeight
          )
        }
      }

      // Debug log every few frames
      if (Math.random() < 0.05) { // 5% of frames
        console.log('Drawing frame - hasData:', hasData, 'maxValue:', maxValue, 'drawnBars:', drawnBars)
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()
  }

  return (
    <div className={`bg-dark-800/50 rounded-lg p-3 ${className}`}>
      <div className="flex items-center space-x-2 mb-2">
        <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : error ? 'bg-red-500' : 'bg-gray-500'}`}></div>
        <span className="text-xs text-gray-400">
          {error ? 'Audio Error' : isActive ? 'Audio Spectrum' : 'Audio Ready'}
        </span>
      </div>
      {error ? (
        <div className="text-xs text-red-400 p-2 bg-red-500/10 rounded">
          {error}
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          width={200}
          height={60}
          className="w-full h-15 rounded border border-gray-600"
          style={{ 
            background: 'rgba(15, 23, 42, 0.5)',
            minHeight: '60px',
            display: 'block'
          }}
        />
      )}
    </div>
  )
}

export default AudioSpectrum