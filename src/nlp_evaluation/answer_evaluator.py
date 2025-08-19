from transformers import pipeline
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
def evaluate_answer(response: str, ideal_answer: str):
    embeddings = model.encode([response, ideal_answer])
    score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    if score > 0.8: return "EXCELLENT"
    elif score > 0.6: return "GOOD"
    elif score > 0.4: return "SATISFACTORY"
    else: return "POOR"