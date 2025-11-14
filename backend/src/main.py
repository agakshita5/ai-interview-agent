from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import os
import base64
import json
from datetime import datetime
from backend.src.utils.config import load_config
from backend.src.api_integration.api_client import get_question_set
from backend.src.session.session_manager import personalize_intro
from backend.src.voice_processing.record_transcription import transcribe_audio, generate_speech, ask_groq
from backend.src.nlp_evaluation.answer_evaluator import evaluate_answer

app = FastAPI()

# allow requests from Node.js server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = load_config()

# store interview sessions: # key: session_id, value: session->dict(cnm, ivnm, ques[dict{'question_id', 'question', 'ideal_answer', 'topic', 'difficulty'}], curr_idx, aw_idx, response[], report)
sessions: Dict[str, Dict[str, Any]] = {}

# store active room sessions
room_sessions: Dict[str, Dict[str, Any]] = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
PROJECT_ROOT = os.path.dirname(BASE_DIR) # backend
DATA_DIR = os.path.join(PROJECT_ROOT, "data") # backend/data
REPORT_DIR = os.path.join(DATA_DIR, "reports") # backend/data/reports
MAIN_PROJECT_ROOT = os.path.dirname(PROJECT_ROOT) # prj

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

class ProcessAudioRequest(BaseModel):
    roomId: str
    audioData: str  # base64 encoded audio

class StartInterviewRequest(BaseModel):
    roomId: str
    candidateName: str

class NextQuestionRequest(BaseModel):
    roomId: str

FRONTEND_DIR = os.path.join(MAIN_PROJECT_ROOT, "frontend")
app.mount("/public", StaticFiles(directory=os.path.join(FRONTEND_DIR, "public")), name="public")
templates = Jinja2Templates(directory=os.path.join(FRONTEND_DIR, "views"))

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    room_id = str(uuid.uuid4())
    return templates.TemplateResponse("room.html", {"request": request, "room_id": room_id})

@app.post("/agent/start-interview")
async def start_interview(req: StartInterviewRequest):
    # initialize interview for this room
    questions = [get_question_set(i) for i in range(2) if i < 2]
    
    room_sessions[req.roomId] = {
        "candidate_name": req.candidateName,
        "room_id": req.roomId,
        "questions": questions,
        "current_question_idx": 0,
        "responses": [],
        "state": "intro"  # intro, question, answer, done
    }
    
    # generate intro speech
    try:
        intro_text = personalize_intro(req.candidateName)
        intro_audio_path = generate_speech(intro_text, os.path.join(DATA_DIR, f"{req.roomId}_intro.wav"))
        if not intro_audio_path:
            raise HTTPException(status_code=500, detail="Failed to generate intro audio")
        else:
            return {
                "status": "started",
                "audioUrl": f"/agent/get-audio/{req.roomId}_intro.wav",
                "nextState": "question"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/process-audio")
async def process_audio(req: ProcessAudioRequest):
    # receive audio chunk from bot, transcribe, process, return TTS
    room_id = req.roomId
    
    if room_id not in room_sessions:
        raise HTTPException(status_code=404, detail="Room session not found")
    
    session = room_sessions[room_id]
    
    audio_data = base64.b64decode(req.audioData)
    temp_audio_path = os.path.join(DATA_DIR, f"{room_id}_temp_audio.wav")
    
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_data)
    
    # transcribe audio
    candidate_text = transcribe_audio(temp_audio_path)
    
    if not candidate_text or len(candidate_text.strip()) == 0:
        return {
            "status": "no_speech",
            "audioUrl": None
        }
    
    # process based on interview state
    state = session["state"]
    
    if state == "intro":
        # after intro, ask first question
        return askNextQuestion(room_id, session)
    
    elif state == "question":
        # process answer
        return processAnswer(room_id, session, candidate_text)
    
    elif state == "followup":
        # process followup response
        return processFollowupAnswer(room_id, session, candidate_text)
    
    elif state == "done":
        return {"status": "done", "audioUrl": None}
    
    return {"status": "processed", "audioUrl": None}

@app.post('/agent/next-question')
async def next_question(req: NextQuestionRequest):
    roomId = req.roomId
    if roomId not in room_sessions:
        raise HTTPException(status_code=404, detail="Room session not found")
    session = room_sessions[roomId]
    session["state"] = "question"
    return askNextQuestion(roomId, session)

def askNextQuestion(room_id, session):
    # ask next question
    idx = session["current_question_idx"]
    questions = session["questions"]
    
    if idx >= len(questions):
        # interview done -> generate conclusion and final report
        conclusion = config["conclusion_prompt"]
        audio_path = generate_speech(conclusion, os.path.join(DATA_DIR, f"{room_id}_conclusion.wav"))
        session["state"] = "done"
        
        # generate final report
        generateFinalReport(room_id, session)
        
        return {
            "status": "conclusion",
            "audioUrl": f"/agent/get-audio/{room_id}_conclusion.wav",
            "reportReady": True
        }
    
    question = questions[idx]
    question_text = question["question"]
    
    # generate question speech
    audio_path = generate_speech(question_text, os.path.join(DATA_DIR, f"{room_id}_question_{idx}.wav"))
    session["state"] = "question"
    
    return {
        "status": "question",
        "audioUrl": f"/agent/get-audio/{room_id}_question_{idx}.wav",
        "questionId": idx
    }

def processAnswer(room_id, session, candidate_text):
    # evaluate answer
    idx = session["current_question_idx"]
    question = session["questions"][idx]
    
    rating = evaluate_answer(candidate_text, question["ideal_answer"])
    
    # save response
    session["responses"].append({
        "question_id": question.get("question_id", idx + 1),
        "question": question["question"],
        "answer": candidate_text,
        "rating": rating,
        "ideal_answer": question.get("ideal_answer", "")
    })
    
    # check if followup needed
    if rating in ["POOR", "SATISFACTORY"]:
        # generate followup
        followup_text = f"Can you elaborate on that? {ask_groq(f'Generate a followup question based on: {candidate_text}')}"
        followup_path = os.path.join(DATA_DIR, f"{room_id}_followup_{idx}.wav")
        audio_path = generate_speech(followup_text, followup_path)
        
        # update last response with followup question
        if session["responses"]:
            session["responses"][-1]["followup_text"] = followup_text
        
        # set state to followup -> wait for followup response
        session["state"] = "followup"
        return {
            "status": "followup",
            "audioUrl": f"/agent/get-audio/{room_id}_followup_{idx}.wav",
            "rating": rating
        }
    else:
        # move to next question
        session["current_question_idx"] += 1
        session["state"] = "question"
        return askNextQuestion(room_id, session)

def processFollowupAnswer(room_id, session, candidate_text):
    # evaluate followup answer
    idx = session["current_question_idx"]
    question = session["questions"][idx]
    
    # update last response with followup answer
    if session["responses"]:
        session["responses"][-1]["followup_answer"] = candidate_text
    
    # re-evaluate with followup answer
    rating = evaluate_answer(candidate_text, question["ideal_answer"])
    
    # update rating if improved
    if session["responses"]:
        old_rating = session["responses"][-1]["rating"]
        score_map = {"POOR": 1, "SATISFACTORY": 2, "GOOD": 3, "EXCELLENT": 4}
        if score_map.get(rating, 2) > score_map.get(old_rating, 1):
            session["responses"][-1]["rating"] = rating
    
    # move to next question
    session["current_question_idx"] += 1
    session["state"] = "question"
    return askNextQuestion(room_id, session)

@app.get("/agent/get-audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="Audio file not found")

def generateFinalReport(room_id, session):
    if not session["responses"]:
        return
    
    ratings = [r["rating"] for r in session["responses"]]
    score_map = {"POOR": 1, "SATISFACTORY": 2, "GOOD": 3, "EXCELLENT": 4}
    avg_score = sum(score_map.get(r, 2) for r in ratings) / len(ratings)
    decision = "HIRE" if avg_score > 2.5 else "REJECT"
    
    report = {
        "room_id": room_id,
        "candidate_name": session["candidate_name"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "responses": session["responses"],
        "average_score": round(avg_score, 2),
        "decision": decision,
        "total_questions": len(session["questions"]),
        "answered_questions": len(session["responses"])
    }
    
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"{room_id}_report.json")
    import json
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

@app.get("/agent/get-report/{roomId}")
async def get_report(roomId: str):
    report_path = os.path.join(REPORT_DIR, f"{roomId}_report.json")

    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            return json.load(f)

    if roomId in room_sessions:
        session = room_sessions[roomId]
        if session.get("responses"):
            return generateFinalReport(roomId, session)
        else:
            return {"status": "in_progress", "message": "Interview is still in progress."}

    raise HTTPException(status_code=404, detail="Report not found")

@app.get("/report/{room_id}", response_class=HTMLResponse)
def report_page(request: Request, room_id: str):
    return templates.TemplateResponse("report.html", {"request": request, "room_id": room_id})

@app.get("/check")
def root():
    return {"message": "Voice agent API running", "status": "ready"}