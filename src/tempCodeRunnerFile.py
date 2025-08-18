from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def first_example():
    return {"hello": "FastAPI"}