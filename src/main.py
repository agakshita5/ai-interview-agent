from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import os
import base64
from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.session.session_manager import run_interview, personalize_intro
from src.voice_processing.record_transcription import transcribe_audio, generate_speech, ask_groq
from src.nlp_evaluation.answer_evaluator import evaluate_answer

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

class ProcessAudioRequest(BaseModel):
    roomId: str
    audioData: str  # base64 encoded audio

class StartInterviewRequest(BaseModel):
    roomId: str
    candidateName: str

@app.post("/agent/start-interview")
async def start_interview(req: StartInterviewRequest):
    # initialize interview for this room
    questions = [get_question_set(i) for i in range(15) if i < 15]
    
    room_sessions[req.roomId] = {
        "candidate_name": req.candidateName,
        "room_id": req.roomId,
        "questions": questions,
        "current_question_idx": 0,
        "responses": [],
        "state": "intro"  # intro, question, answer, done
    }
    
    # generate intro speech
    intro_text = personalize_intro(req.candidateName)
    intro_audio_path = generate_speech(intro_text, f"data/{req.roomId}_intro.wav")
    
    return {
        "status": "started",
        "audioUrl": f"/agent/get-audio/{req.roomId}_intro.wav",
        "nextState": "question"
    }

@app.post("/agent/process-audio")
async def process_audio(req: ProcessAudioRequest):
    # receive audio chunk from bot, transcribe, process, return TTS
    room_id = req.roomId
    
    if room_id not in room_sessions:
        raise HTTPException(status_code=404, detail="Room session not found")
    
    session = room_sessions[room_id]
    
    # save audio chunk temporarily
    audio_data = base64.b64decode(req.audioData)
    temp_audio_path = f"data/{room_id}_temp_audio.wav"
    
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_data)
    
    # transcribe audio
    candidate_text = transcribe_audio(temp_audio_path)
    
    if not candidate_text or len(candidate_text.strip()) == 0:
        return {
            "status": "no_speech",
            "audioUrl": None
        }
    
    print(f"[Python] Transcribed: {candidate_text}")
    
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

def askNextQuestion(room_id, session):
    # ask next question
    idx = session["current_question_idx"]
    questions = session["questions"]
    
    if idx >= len(questions):
        # interview done - generate conclusion and final report
        conclusion = config["conclusion_prompt"]
        audio_path = generate_speech(conclusion, f"data/{room_id}_conclusion.wav")
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
    audio_path = generate_speech(question_text, f"data/{room_id}_question_{idx}.wav")
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
        audio_path = generate_speech(followup_text, f"data/{room_id}_followup_{idx}.wav")
        # set state to followup - wait for followup response
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
    # serve generated audio files
    file_path = f"data/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Audio file not found")

def generateFinalReport(room_id, session):
    # calculate final decision
    if not session["responses"]:
        return
    
    ratings = [r["rating"] for r in session["responses"]]
    score_map = {"POOR": 1, "SATISFACTORY": 2, "GOOD": 3, "EXCELLENT": 4}
    avg_score = sum(score_map.get(r, 2) for r in ratings) / len(ratings)
    decision = "HIRE" if avg_score > 2.5 else "REJECT"
    
    from datetime import datetime
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
    
    # save report to file for viewing
    report_file = f"data/reports/{room_id}_report.json"
    os.makedirs("data/reports", exist_ok=True)
    import json
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"[Python] Final report saved: {report_file}")
    return report

@app.get("/agent/get-report/{roomId}")
async def get_report(roomId: str):
    # get final report for room
    report_file = f"data/reports/{roomId}_report.json"
    
    if not os.path.exists(report_file):
        # try to get from active session
        if roomId in room_sessions:
            report = generateFinalReport(roomId, room_sessions[roomId])
            if report:
                return report
        raise HTTPException(status_code=404, detail="Report not found")
    
    import json
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    return report

@app.get("/")
def root():
    return {"message": "Voice agent API running", "status": "ready"}