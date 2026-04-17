from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")

def evaluate_answer(response: str, ideal_answer: str, jd_profile=None):
    # Compare response vs ideal_answer 
    embeddings = model.encode([response, ideal_answer])
    score = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])

    # bonus weight if response mentions relevant skills
    if jd_profile:
        skills = (jd_profile.get("skills") or "").lower().split(",")
        resp_lower = response.lower()
        mentioned = sum(1 for s in skills if s.strip() and s.strip() in resp_lower)
        relevance_bonus = min(mentioned * 0.02, 0.1)  # up to +0.1
        score = min(score + relevance_bonus, 1.0)

    if score > 0.8: return "EXCELLENT"
    elif score > 0.6: return "GOOD"
    elif score > 0.4: return "SATISFACTORY"
    else: return "POOR"