import json
import re
from backend.src.voice_processing.record_transcription import ask_groq

def _parse_json_blob(text: str) -> dict:
    if not text:
        raise ValueError("empty response")
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if fence:
        t = fence.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        a = t.find("{")
        b = t.rfind("}")
        if a >= 0 and b > a:
            return json.loads(t[a : b + 1])
        raise


def analyze_job_description(jd_text: str) -> dict:
    prompt = """You are an expert recruiter. Read the job description and output ONLY valid JSON (no markdown, no commentary) with this exact shape:
{
  "role": "short job title",
  "skills": "comma-separated key skills",
  "experience": "expected years or seniority in one short phrase",
  "jd_summary": "2-4 sentence summary of the role and expectations",
  "questions": [
    {
      "question_id": 1,
      "question": "interview question text",
      "ideal_answer": "what a strong answer should cover",
      "topic": "short topic label",
      "difficulty": "Easy|Medium|Hard"
    }
  ]
}
Rules: Generate exactly 6 questions tailored to this JD. ideal_answer should be concrete and evaluable. question_id 1..6 in order.

Job description:
""" + jd_text[:12000]

    raw = ask_groq(prompt, max_completion_tokens=4096, model="llama-3.3-70b-versatile")
    try:
        data = _parse_json_blob(raw)
    except Exception:
        raw = ask_groq(prompt, max_completion_tokens=4096, model="mixtral-8x7b-32768")
        data = _parse_json_blob(raw)
    role = str(data.get("role", "Role")).strip()
    skills = str(data.get("skills", "")).strip()
    experience = str(data.get("experience", "")).strip()
    jd_summary = str(data.get("jd_summary", "")).strip()
    questions = data.get("questions") or []
    out_questions = []
    for i, q in enumerate(questions):
        out_questions.append({
            "question_id": int(q.get("question_id", i + 1)),
            "question": str(q.get("question", "")).strip(),
            "ideal_answer": str(q.get("ideal_answer", "")).strip(),
            "topic": str(q.get("topic", "")).strip(),
            "difficulty": str(q.get("difficulty", "Medium")).strip(),
        })
    if not out_questions:
        raise ValueError("no questions generated")
    jd_profile = {
        "role": role,
        "skills": skills,
        "experience": experience,
        "jd_summary": jd_summary,
    }
    return {"jd_profile": jd_profile, "questions": out_questions}
