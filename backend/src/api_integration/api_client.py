import json
def get_question_set(ques_id: int):
    with open("backend/data/questions.json", "r") as f:
        return json.load(f)[ques_id]