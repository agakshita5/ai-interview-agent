from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import uuid
from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.session.session_manager import run_interview

app = FastAPI()

config = load_config()

sessions: Dict[str, Dict[str, Any]] = {} # key: session_id, value: session->dict(cnm, ivnm, ques[dict{'question_id', 'question', 'ideal_answer', 'topic', 'difficulty'}], curr_idx, aw_idx, response[], report)

class RunAgentRequest(BaseModel):
    candidate_name: str
    interview_set_name: str

class RunAgentResponse(BaseModel):
    session_id: str
    report: Dict[str, Any]

@app.post("/agent/run", response_model=RunAgentResponse)
async def run_agent(req: RunAgentRequest):
    session_id = str(uuid.uuid4())
    
    questions = [get_question_set(i) for i in range(1) if get_question_set(i)]

    sessions[session_id] = {
        "candidate_name": req.candidate_name,
        "interview_set_name": req.interview_set_name,
        "questions": questions,
        "responses": [],
        "report": None,
        "session_id": session_id,
    }

    report = run_interview(sessions[session_id], mode="AGENT")
    sessions[session_id]["report"] = report

    return RunAgentResponse(session_id=session_id, report=report)

@app.get("/")
def root():
    return {"message": "running interview agent"}