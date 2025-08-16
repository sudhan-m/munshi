# UI Service - Frontend Interface

Modern React-based frontend for the Munshi AI language learning platform, providing an intuitive conversational interface for language learning and pronunciation practice.

## 🎯 Overview

The UI Service serves as the primary user interface for the Munshi platform, featuring:
- **Conversational Chat Interface**: Real-time chat experience with AI
- **Audio Recording & Playback**: Browser-based audio capture for pronunciation practice
- **Authentication Integration**: Seamless login and registration flows
- **Responsive Design**: Mobile-friendly interface with modern animations
- **Real-time Features**: Typing indicators and smooth interactions

## ✨ Features

- **🔐 Authentication** - JWT-based authentication with Auth Service integration
- **💬 Chat Interface** - Conversational UI for language learning with AI
- **🎤 Audio Recording** - WebRTC audio capture for pronunciation practice
- **🎵 Audio Playback** - Audio message playback with spectrum visualization
- **📱 Responsive Design** - Mobile-first responsive interface
- **🎨 Modern UI** - Tailwind CSS with custom animations and glass morphism
- **🌐 Multi-language Support** - Support for English, Tamil, and Malayalam learning

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

## 🔌 API Integration

### Service Communication
- **Conversation Service** (Port 8007): Main chat and pronunciation evaluation
- **Auth Service** (Port 8001): User authentication and token management
- **Audio Service** (Port 8003): Audio file upload and storage

### Key API Endpoints Used
- `POST /api/conversation/chat` - Send chat messages
- `POST /api/conversation/evaluate-pronunciation` - Pronunciation evaluation
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `POST /api/audio/upload` - Audio file upload

## 🌐 Browser Support

Chrome/Edge, Firefox, Safari (iOS 14.5+)