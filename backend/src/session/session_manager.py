from src.utils.config import load_config
from src.voice_processing.record_transcription import generate_speech, transcribe_audio as stt_transcribe_audio, ask_groq, record_audio, play_audio
from src.nlp_evaluation.answer_evaluator import evaluate_answer
from transformers import pipeline
import json
from typing import Dict, List
from sentence_transformers import SentenceTransformer
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
lang_model = SentenceTransformer("all-MiniLM-L6-v2")

company_info = {
  "culture": "We value innovation and collaboration.",
  "mission": "To build cutting-edge AI products.",
  "benefits": "We offer health insurance, flexible hours, and remote work options.",
  "projects": "We are currently working on AI for healthcare and fintech."
}
comp_info_desc = list(company_info.values())
embeddings_company = lang_model.encode(comp_info_desc)
def answer_candidate_question(question: str) -> str:
    embeddings_cand_ques = lang_model.encode(question)
    # compute cosine similarities
    similarities = lang_model.similarity(embeddings_company, embeddings_cand_ques)
    closest_score = max(similarities).item()
    closest_score_idx = similarities.argmax().item()
    if closest_score >= 0.25:
        confidence_note = "This is a strong match with company information."
    else:
        confidence_note = "This may not directly match company info, but please still give a natural response based on general company culture and values."
        
    groq_query = f"""
    Candidate response to "Do you have any questions for us?": {question}
    Closest company info: {comp_info_desc[closest_score_idx]}
    Note: {confidence_note}
    Answer in a conversational tone.
    Be concise and keep the response under 3 sentences.
    Give a **plain conversational answer**, no markdown, no formatting, no bullet points.
    """
    return ask_groq(groq_query)
    
def personalize_intro(candidate_name: str) -> str:
    config = load_config()
    return config["introduction_prompt"].format(candidate_name=candidate_name)

generator = pipeline("text-generation", model="distilgpt2")
def generate_followup(response: str):
    prompt = f"Response: {response}\nGenerate a follow-up question to clarify. Answer in a conversational tone.\nBe concise and keep the response under 3 sentences.\nGive a **plain conversational answer**, no markdown, no formatting, no bullet points."
    result = generator(prompt, max_length=50)[0]["generated_text"]
    return result.split("\n")[-1]

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
            ques_mp3_path = generate_speech(question_text, f"data/{session['session_id']}_question_{idx}.mp3")
            play_audio(ques_mp3_path)
            # response recorded
            response_audio_path = record_audio(output_file=f"data/{session['session_id']}_response_{idx}.wav")
            candidate_text = stt_transcribe_audio(response_audio_path)
            # evaluated answer & rating recorded
            rating = evaluate_answer(candidate_text, question_obj["ideal_answer"])
            # follow-up question if rating bad
            follow_up_text = None
            followup_candidate_text = None
            if rating in ["POOR", "SATISFACTORY"]:
                # follow_up_text = ask_groq(candidate_text) -> wrong followup
                follow_up_text = generate_followup(candidate_text)
                followup_mp3 = generate_speech(follow_up_text, f"data/{session['session_id']}_followup_{idx}.mp3")
                play_audio(followup_mp3)
                followup_audio_path = record_audio(output_file=f"data/{session['session_id']}_followup_response_{idx}.wav")
                followup_candidate_text = stt_transcribe_audio(followup_audio_path)
                rating = evaluate_answer(followup_candidate_text, question_obj["ideal_answer"])

            # response recorded
            session["responses"].append({
                "question_id": question_obj.get("question_id", idx + 1),
                "question": question_text,
                "candidate_response": candidate_text,
                "rating": rating,
                "follow_up": follow_up_text,
                "follow_up_response": followup_candidate_text
            })
        # Candidate Q&A
        post_iv_ques = "Do you have any questions for us?"
        post_iv_ques_mp3 = generate_speech(post_iv_ques, f"data/{session['session_id']}_post_iv_ques.mp3")
        play_audio(post_iv_ques_mp3)
        cand_ques_audio_path = record_audio(output_file=f"data/{session['session_id']}_candidate_question.wav")
        candidate_question = stt_transcribe_audio(cand_ques_audio_path)
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
        full_session_audio_path = record_audio(output_file=f"data/{session['session_id']}_full_session.wav")
        transcript.append(stt_transcribe_audio(full_session_audio_path))
        session["report"] = {"transcript": " ".join(transcript)}
    return session["report"]