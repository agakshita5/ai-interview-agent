from src.utils.config import load_config
from src.api_integration.api_client import get_question_set
from src.voice_processing.record_transcription import generate_speech, transcribe_audio as stt_transcribe_audio, ask_groq, record_audio, play_audio
from src.nlp_evaluation.answer_evaluator import evaluate_answer
import json
from typing import Dict, List

def personalize_intro(candidate_name: str) -> str:
    config = load_config()
    return config["introduction_prompt"].format(candidate_name=candidate_name)

company_info = {"culture": "We value innovation and collaboration."}

def answer_candidate_question(question: str) -> str:
    lower_question = question.lower()
    for key, answer in company_info.items():
        if key in lower_question:
            return answer
    return "Can you clarify your question?"


def run_interview(session: dict, mode: str = "AGENT"):
    config = load_config()
    if mode == "AGENT":
        # Pre-interview
        intro_text = personalize_intro(session["candidate_name"])
        intro_mp3 = generate_speech(intro_text, f"data/{session['session_id']}_intro.mp3")
        play_audio(intro_mp3)
        # Live interview
        for idx, question_obj in enumerate(session["questions"]):
            # question asked
            question_text = question_obj["question"]
            mp3_path = generate_speech(question_text, f"data/{session['session_id']}_question_{idx}.mp3")
            play_audio(mp3_path)
            # response recorded
            audio_path = record_audio(f"data/{session['session_id']}_response_{idx}.wav")
            candidate_text = stt_transcribe_audio(audio_path)
            # evaluated answer & rating recorded
            rating = evaluate_answer(candidate_text, question_obj["ideal_answer"])
            # follow-up question if rating bad
            follow_up_text = None
            if rating in ["POOR", "SATISFACTORY"]:
                follow_up_text = ask_groq(candidate_text)
                followup_mp3 = generate_speech(follow_up_text, f"data/{session['session_id']}_followup_{idx}.mp3")
                play_audio(followup_mp3)
                audio_path = record_audio(f"data/{session['session_id']}_followup_response_{idx}.wav")
                candidate_text = stt_transcribe_audio(audio_path)
                rating = evaluate_answer(candidate_text, question_obj["ideal_answer"])

            # response recorded
            session["responses"].append({
                "question_id": question_obj.get("question_id", idx + 1),
                "question": question_text,
                "candidate_text": candidate_text,
                "rating": rating,
                "follow_up": follow_up_text,
            })
        # Candidate Q&A
        print("Do you have any questions for us?")
        audio_path = record_audio(f"data/{session['session_id']}_candidate_question.wav")
        candidate_question = stt_transcribe_audio(audio_path)
        answer = answer_candidate_question(candidate_question)
        answer_mp3 = generate_speech(answer, f"data/{session['session_id']}_candidate_answer.mp3")
        play_audio(answer_mp3)
        # Conclusion
        conclusion_text = config["conclusion_prompt"]
        conclusion_mp3 = generate_speech(conclusion_text, f"data/{session['session_id']}_conclusion.mp3")
        play_audio(conclusion_mp3)
        # Final feedback
        ratings = [r["rating"] for r in session["responses"]]
        score_map = {"POOR": 1, "SATISFACTORY": 2, "GOOD": 3, "EXCELLENT": 4}
        avg_score = sum(score_map[r] for r in ratings) / len(ratings)
        decision = "HIRE" if avg_score > 2.5 else "REJECT"
        session["report"] = {
            "candidate_name": session["candidate_name"],
            "responses": session["responses"],
            "average_score": avg_score,
            "decision": decision,
        }
    elif mode == "TRANSCRIBER":
        transcript = []
        print("Transcriber Mode: Recording entire session...")
        audio_path = record_audio(f"data/{session['session_id']}_full_session.wav", duration=300)
        transcript.append(stt_transcribe_audio(audio_path))
        session["report"] = {"transcript": " ".join(transcript)}
    return session["report"]