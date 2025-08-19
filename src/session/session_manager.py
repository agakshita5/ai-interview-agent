from src.utils.config import load_config
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

def _load_ratings() -> List[Dict]:
    with open("data/ratings.json", "r") as f:
        return json.load(f)


def run_interview(candidate_name: str, interview_set_name: str) -> Dict:
    # For now, use the mock ratings dataset to simulate an interview summary
    ratings_data = _load_ratings()

    def score_to_bucket(score: float) -> str:
        if score >= 8.5:
            return "EXCELLENT"
        if score >= 7.0:
            return "GOOD"
        if score >= 5.0:
            return "SATISFACTORY"
        return "POOR"

    ratings = [score_to_bucket(item.get("score", 0.0)) for item in ratings_data]

    bucket_to_value = {"POOR": 1, "SATISFACTORY": 2, "GOOD": 3, "EXCELLENT": 4}
    numeric_scores = [bucket_to_value[r] for r in ratings]
    average = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0
    final_decision = "HIRE" if average > 2.5 else "REJECT"

    return {
        "candidate_name": candidate_name,
        "interview_set": interview_set_name,
        "ratings": ratings,
        "decision": final_decision,
    }