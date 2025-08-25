from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import os
from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.voice_processing.record_transcription import generate_speech, transcribe_audio as stt_transcribe_audio, ask_groq
from src.nlp_evaluation.answer_evaluator import evaluate_answer
from src.nlp_evaluation.question_generator import generate_followup
from src.session.session_manager import run_interview, personalize_intro, answer_candidate_question

app = FastAPI()

config = load_config()

class StartAgentRequest(BaseModel):
    candidate_name: str
    interview_set_name: str

class AskQuestionRequest(BaseModel):
    session_id: str

class IntroRequest(BaseModel):
    candidate_name: str

class CandidateQuestionRequest(BaseModel):
    question: str

sessions: Dict[str, Dict[str, Any]] = {}

@app.post("/agent/start")
async def start_agent(req: StartAgentRequest):
    session_id = str(uuid.uuid4())
    questions: List[Dict[str, Any]] = []
    for i in range(15):
        try:
            questions.append(get_question_set(i))
        except Exception:
            break

    sessions[session_id] = {
        "candidate_name": req.candidate_name,
        "interview_set_name": req.interview_set_name,
        "questions": questions,
        "current_idx": 0,  # next question to ask
        "awaiting_answer_index": None,  # index of last asked question
        "responses": [],  # list of {question_id, text, rating, followup?}
        "report": None,
    }

    intro_text = personalize_intro(req.candidate_name)
    mp3_path = generate_speech(intro_text, f"data/{session_id}_intro.mp3")
    return {"session_id": session_id, "intro_text": intro_text, "intro_mp3": mp3_path}

@app.post("/agent/ask")
async def ask_question(req: AskQuestionRequest):
    session_id = req.session_id
    if session_id not in sessions:
        return JSONResponse({"error": "Invalid session"}, status_code=400)

    session = sessions[session_id]
    idx = session.get("current_idx", 0)
    questions = session.get("questions", [])
    if idx >= len(questions):
        return JSONResponse({"error": "No more questions"}, status_code=404)

    question_obj = questions[idx]
    question_text: str = question_obj.get("question", "")

    # Mark awaiting answer and advance pointer
    session["awaiting_answer_index"] = idx
    session["current_idx"] = idx + 1

    mp3_path = generate_speech(question_text, f"data/{session_id}_question_{idx}.mp3")
    return {"question_text": question_text, "mp3_path": mp3_path, "question_id": question_obj.get("question_id", idx + 1)}

@app.post("/agent/respond")
async def respond(session_id: str, audio: UploadFile = File(...)):
    if session_id not in sessions:
        return JSONResponse({"error": "Invalid session"}, status_code=400)

    session = sessions[session_id]
    awaiting_idx = session.get("awaiting_answer_index")
    if awaiting_idx is None:
        return JSONResponse({"error": "No question awaiting an answer"}, status_code=400)

    os.makedirs("data", exist_ok=True)
    audio_path = os.path.join("data", f"{session_id}_response_{awaiting_idx}.wav")
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    candidate_text = stt_transcribe_audio(audio_path)

    # Evaluate against the ideal answer of the asked question
    question_obj = session["questions"][awaiting_idx]
    ideal_answer = question_obj.get("ideal_answer", "")
    rating = evaluate_answer(candidate_text, ideal_answer)

    follow_up_text: Optional[str] = None
    followup_mp3: Optional[str] = None
    if rating in ["POOR", "SATISFACTORY"]:
        follow_up_text = ask_groq(candidate_text)
        followup_mp3 = generate_speech(follow_up_text, f"data/{session_id}_followup_{awaiting_idx}.mp3")

    # Store response record
    session["responses"].append({
        "question_id": question_obj.get("question_id", awaiting_idx + 1),
        "question": question_obj.get("question", ""),
        "candidate_text": candidate_text,
        "rating": rating,
        "follow_up": follow_up_text,
    })

    # Clear awaiting index until next ask
    session["awaiting_answer_index"] = None

    return {
        "session_id": session_id,
        "transcription": candidate_text,
        "rating": rating,
        "followup_question": follow_up_text,
        "followup_mp3": followup_mp3,
    }
   

@app.get("/report/{session_id}")
async def get_report(session_id: str):
    if session_id not in sessions:
        return JSONResponse({"error": "Invalid session"}, status_code=400)

    # Example: Generate evaluation summary later
    # sessions[session_id]["report"] = "Candidate did well in communication skills..."

    return {"session_id": session_id, "report": sessions[session_id].get("report", "Report not generated yet.")}


