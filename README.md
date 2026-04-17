# AI Voice Interview Agent

An AI-powered mock interview platform that conducts voice-based interviews and provides instant feedback.

## Features

- **Job Description Analysis**: Upload job descriptions to extract key skills
- **Voice-Based Interviews**: AI-generated interview questions with text-to-speech
- **Real-time Transcription**: Candidate responses captured and transcribed
- **Intelligent Evaluation**: Answers evaluated against ideal responses
- **Follow-up Questions**: Adaptive follow-ups for weak answers
- **Instant Reports**: Comprehensive scoring and hire/reject recommendations

## Tech Stack

**Frontend**: React 19, React Router

**Backend**: FastAPI, Groq API, OpenAI Whisper, Piper TTS

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.src.main:app --reload
```

### Frontend
```bash
cd react_frontend
npm install
npm start
```

## Project Structure

```
├── react_frontend/          # React frontend
│   └── src/
│       ├── pages/
│       │   ├── Upload.jsx   # Job description upload
│       │   ├── Interview.jsx # Voice interview
│       │   └── Results.jsx  # Interview results
│       ├── App.jsx
│       └── api.js
└── backend/                 # FastAPI backend
    └── src/
        ├── main.py          # API endpoints
        ├── jd_analysis.py   # Question generation
        ├── jd_extract.py    # File parsing
        ├── nlp_evaluation/  # Answer evaluation
        ├── voice_processing/# Whisper & TTS
        └── session/         # Session management
```
