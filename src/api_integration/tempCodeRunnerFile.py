import json
def get_question_set(interview_id: int):
    with open("data/questions.json", "r") as f:
        return json.load(f)[interview_id-1]

print(get_question_set(2))