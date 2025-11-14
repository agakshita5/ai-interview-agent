---
title: AI Voice Interview Agent
emoji: 🎤
colorFrom: cyan
colorTo: blue
sdk: docker
app_file: backend/src/main.py
pinned: false
---

# AI Voice Interview Agent

This is a FastAPI-based voice interview agent deployed on Hugging Face Spaces.
It supports:
- Real-time audio questions
- Candidate audio answers
- Automatic scoring & report generation
- FastAPI backend + HTML/JS frontend

Run locally:

```bash
uvicorn backend.src.main:app --reload
