from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")

def evaluate_answer(response: str, ideal_answer: str, jd_profile=None):
    ctx = ""
    if jd_profile:
        role = jd_profile.get("role") or ""
        skills = jd_profile.get("skills") or ""
        ctx = f"Role: {role}. Skills: {skills}. "
    a = ctx + response
    b = ctx + ideal_answer
    embeddings = model.encode([a, b])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    if score > 0.8: return "EXCELLENT"
    elif score > 0.6: return "GOOD"
    elif score > 0.4: return "SATISFACTORY"
    else: return "POOR"