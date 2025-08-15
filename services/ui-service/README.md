# Munshi UI Service

Modern React-based frontend for Munshi AI voice assistant with clean chat interface, authentication, and real-time audio recording.

## ✨ Features

- **🔐 Authentication** - Simple sign up/sign in with JWT tokens
- **💬 Chat Interface** - Clean conversation UI with text and voice messages  
- **🎤 Audio Recording** - One-click recording with real-time level visualization
- **🎵 Audio Playback** - Play messages with power spectrum visualization
- **📱 Responsive** - Works on desktop and mobile
- **🎨 Modern UI** - Glass morphism design with smooth animations

## 🚀 Quick Start

```bash
./dev.sh    # Starts both frontend (3000) and backend (8002)
```

## 🛠️ Development

**Prerequisites:** Node.js 18+, Python 3.11+

```bash
# Frontend only
npm install && npm run dev

# Backend only  
pip install -r requirements.txt && python server.py

# Production build
npm run build
```

## 🐳 Docker

```bash
docker build -t munshi-ui .
docker run -p 8002:8002 munshi-ui
```

## 📁 Structure

```
src/
├── components/         # React components
├── contexts/          # State management
├── App.jsx           # Main app
├── main.jsx          # Entry point
└── index.css         # Styles
```

## 🔌 API Endpoints

- `POST /api/auth/login` - Authentication
- `POST /api/auth/register` - Registration
- `GET /api/auth/verify` - Token verification
- `POST /api/audio/process` - Audio processing

## 🌐 Browser Support

Chrome/Edge, Firefox, Safari (iOS 14.5+)