import os
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI


# Load environment variables from backend/.env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# Create FastAPI app
app = FastAPI()


# Allow the React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Get OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")


# Create OpenAI client
client = OpenAI(api_key=api_key)


# Defines the structure of a question returned by the AI
class AIQuestion(BaseModel):
    question: str
    input_type: str
    options: Optional[list[str]] = None


# Temporary conversation memory
# We will replace this with a database later.
conversation_history = []


@app.get("/")
def root():
    return {"message": "Doctor AI backend is working!"}


@app.post("/api/chat")
def chat(message: str):

    # Save the user's message
    conversation_history.append({
        "role": "user",
        "content": message
    })


    # Instructions that control how Doctor AI behaves
    instructions = """
    You are Doctor AI, a health assessment assistant.

    Your job is to help users understand their symptoms and decide
    what information may be important to discuss with a healthcare
    professional.

    Follow these rules:

    1. Do not claim that you can provide a definitive diagnosis.

    2. Ask relevant follow-up questions when important information
       is missing.

    3. Consider symptoms together rather than treating each symptom
       independently.

    4. Clearly distinguish information reported by the user from
       assumptions or possibilities.

    5. Explain possible causes in understandable language.

    6. Communicate uncertainty clearly.

    7. Pay attention to symptoms that could indicate an urgent
       situation and recommend appropriate medical attention
       when warranted.

    8. Never invent medical history, test results, medications,
       symptoms, or other user information.

    9. Do not recommend prescription medications or tell users to
       change prescribed treatment.

    10. Be calm, respectful, and easy to understand.

    11. Ask only the most useful questions instead of overwhelming
        the user with a huge questionnaire.

    12. Your purpose is to assist the user, not replace a healthcare
        professional.

    When asking a follow-up question, choose the most appropriate
    input type from the following options:

    - text: Use when the user needs to describe something in their
      own words.

    - scale: Use for measurements such as pain severity from 0 to 10.

    - single_choice: Use when the user should choose one answer from
      a small set of options.

    When using single_choice, generate a short list of relevant
    options. Do not create unnecessary options.

    Always return the following JSON structure:

    {
      "question": "your question",
      "input_type": "text | scale | single_choice",
      "options": ["option 1", "option 2"]
    }

    For "text" and "scale", set options to null.

    For "scale", use a 0-10 scale unless another numerical scale
    is clearly more appropriate.

    Ask only 1-3 questions at a time.

    Keep your responses concise and avoid overwhelming the user
    with large explanations before enough information has been
    collected.
    """


    # Send the conversation history to the AI
    response = client.responses.create(
        model="gpt-5-mini",
        instructions=instructions,
        input=conversation_history,
        text={
            "format": {
                "type": "json_schema",
                "name": "ai_question",
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string"
                        },
                        "input_type": {
                            "type": "string",
                            "enum": [
                                "text",
                                "scale",
                                "single_choice"
                                "select_all"
                            ]
                        },
                        "options": {
                            "type": [
                                "array",
                                "null"
                            ],
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": [
                        "question",
                        "input_type",
                        "options"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )


    # Convert the AI's JSON text into a Python dictionary
    data = json.loads(response.output_text)


    # Save the AI response in the conversation history
    conversation_history.append({
        "role": "assistant",
        "content": response.output_text
    })


    # Send the structured question back to React
    return data