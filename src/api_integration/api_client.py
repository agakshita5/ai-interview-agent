import json
def get_question_set(ques_id: int):
    with open("data/questions.json", "r") as f:
        return json.load(f)[ques_id]

for i in range(15):
    print(get_question_set(i)['topic'])