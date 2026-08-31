import os

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")

client = OpenAI(api_key=api_key)


@app.get("/")
def root():
    return {"message": "Doctor AI backend is working!"}


@app.post("/chat")
def chat(message: str):
    response = client.responses.create(
        model="gpt-5-mini",
        input=message
    )

    return {
        "response": response.output_text
    }