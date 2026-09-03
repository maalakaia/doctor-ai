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
    assessment_complete: bool


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

    - single_choice: Use when the user should select exactly one
      answer.

    - select_all: Use when multiple answers can apply at the same time.

    When choosing between single_choice and select_all, consider
    whether multiple answers could logically be true at once.

    For example:
    - "Where is the pain?" would usually use single_choice.
    - "Which symptoms are you experiencing?" would usually use
      select_all.

    When using single_choice or select_all, generate a short list
    of relevant options. Do not create unnecessary options.

    If several options could apply simultaneously, use select_all
    rather than single_choice.

    Before choosing between single_choice and select_all, consider
    whether multiple options can logically be true at the same time.

    When conducting an assessment, you have two possible actions:

    1. Ask another follow-up question if important information
       is still missing.

    2. End the questioning and provide a preliminary assessment
       when you have enough relevant information.

    Set "assessment_complete" to false when you need more information.

    Set "assessment_complete" to true when you have enough information
    to provide a useful preliminary assessment.

    Do not continue asking questions unnecessarily once you have
    enough information.

    When assessment_complete is true:

    - Give a concise summary of the symptoms reported.
    - Explain that the result is a preliminary assessment, not a
      definitive diagnosis.
    - Do not claim certainty.
    - Explain the most relevant possible explanations.
    - Mention important information that remains uncertain.
    - Clearly identify when professional medical evaluation may
      be appropriate.

    When assessment_complete is true, use "text" as the input_type
    and set options to null.

    Always return the following JSON structure:

    {
      "question": "your question or assessment summary",
      "input_type": "text | scale | single_choice | select_all",
      "options": ["option 1", "option 2"],
      "assessment_complete": false
    }

    The input_type MUST be exactly ONE of these four values:

    "text"
    "scale"
    "single_choice"
    "select_all"

    Never combine, concatenate, or modify these values.

    For "text" and "scale", set options to null.

    For "scale", use a 0-10 scale unless another numerical scale
    is clearly more appropriate.

    Ask only 1-3 questions at a time.

    Keep your responses concise and avoid overwhelming the user
    with large explanations before enough information has been
    collected.

    Do not provide a long list of possible diagnoses before enough
    information has been gathered.
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
                                "single_choice",
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
                        },
                        "assessment_complete": {
                            "type": "boolean"
                        }
                    },
                    "required": [
                        "question",
                        "input_type",
                        "options",
                        "assessment_complete"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )


    # Convert the AI's JSON text into a Python dictionary
    data = json.loads(response.output_text)


    # Make sure the AI returned a valid input type
    allowed_input_types = {
        "text",
        "scale",
        "single_choice",
        "select_all"
    }

    if data["input_type"] not in allowed_input_types:
        data["input_type"] = "text"
        data["options"] = None


    # Save the AI response in the conversation history
    conversation_history.append({
        "role": "assistant",
        "content": response.output_text
    })


    # Send the structured question back to React
    return data