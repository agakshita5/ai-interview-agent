import py_compile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.voice_processing.record_transcription import generate_speech, play_audio
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

yaml_file = load_config()

# question set -> list
ques_set=[]
for i in range(15):
    ques_set.append(get_question_set(i)['question'])

# pydantic model
class InterviewInput(BaseModel):
    candidate_name: str
    candidate_answer: str

@app.get("/")
def first_point():
    return {"got":"you"}
    # return {"groq_key": os.getenv("GROQ_API_KEY")}
#    - "/start_session"  → start an interview
@app.post("/start_session")
async def start_session(data: InterviewInput):
    return {"intro_prompt": yaml_file['introduction_prompt'].format(candidate_name = data.candidate_name),"question_set":ques_set}
#    - "/ask_question"   → get next interview question
@app.get("/ask_question/{ques_id}")
async def ask_question(ques_id: int):
    if ques_id < 0 or ques_id >= len(ques_set):
        raise HTTPException(status_code=404, detail="Question not found")
    return {"question":ques_set[ques_id]}
#    - "/submit_answer"  → candidate’s voice/text answer (evaluate it)
@app.post("/submit_answer/{ques_id}")
async def submit_answer(ques_id: int, data: InterviewInput):
    audio_file = generate_speech(data.candidate_answer, "data/response.mp3")
    return {"audio_file": audio_file, "question_id": ques_id, "answer": data.candidate_answer}
#    - "/end_session"    → close interview
@app.get("/end_session")
async def end_session():
    return {"outro_prompt": yaml_file['conclusion_prompt']}
    
# 5. Later: add endpoints for voice STT, TTS, API integration
# -------------------------------------------------
