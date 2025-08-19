from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.voice_processing.record_transcription import generate_speech
from src.nlp_evaluation.answer_evaluator import evaluate_answer
from src.nlp_evaluation.question_generator import generate_followup
from src.session.session_manager import run_interview, personalize_intro, answer_candidate_question

app = FastAPI()

config = load_config()


class StartInterviewRequest(BaseModel):
    candidate_name: str
    interview_set_name: str


class AskQuestionRequest(BaseModel):
    question: str
    candidate_response: str


class IntroRequest(BaseModel):
    candidate_name: str


class CandidateQuestionRequest(BaseModel):
    question: str


@app.post("/start_interview")
async def start_interview(req: StartInterviewRequest):
    result = run_interview(req.candidate_name, req.interview_set_name)
    return result


@app.post("/ask_question")
async def ask_question(req: AskQuestionRequest):
    # Evaluate the candidate response against the ideal answer of a matching question if available
    # For now, find the first question in the dataset that matches req.question text
    try:
        ideal_answer: Optional[str] = None
        # naive scan over the first 15 questions
        for i in range(15):
            item = get_question_set(i)
            if item.get("question") == req.question:
                ideal_answer = item.get("ideal_answer")
                break
        if ideal_answer is None:
            raise HTTPException(status_code=404, detail="Question not found in set")

        rating = evaluate_answer(req.candidate_response, ideal_answer)
        followup_question: Optional[str] = None
        if rating in ["POOR", "SATISFACTORY"]:
            followup_question = generate_followup(req.candidate_response)
        return {"rating": rating, "followup_question": followup_question}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intro")
async def intro(req: IntroRequest):
    text = personalize_intro(req.candidate_name)
    # Generate optional mp3
    mp3_path = generate_speech(text, "data/response.mp3")
    return {"text": text, "mp3_path": mp3_path}


@app.post("/candidate_question")
async def candidate_question(req: CandidateQuestionRequest):
    answer = answer_candidate_question(req.question)
    return {"answer": answer}

