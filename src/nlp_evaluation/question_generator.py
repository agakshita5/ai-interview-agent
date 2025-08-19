from transformers import pipeline
generator = pipeline("text-generation", model="distilgpt2")
def generate_followup(response: str):
    prompt = f"Response: {response}\nGenerate a follow-up question to clarify:"
    result = generator(prompt, max_length=50)[0]["generated_text"]
    return result.split("\n")[-1]