import os
import json
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI


# ============================================================
# ENVIRONMENT
# ============================================================

# Load environment variables from backend/.env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# ============================================================
# DATABASE
# ============================================================

# SQLite database will be stored inside the backend folder.
DATABASE_PATH = BASE_DIR / "doctor_ai.db"


def get_db_connection():
    """
    Create a connection to the SQLite database.

    row_factory allows rows to be accessed like dictionaries.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """
    Create database tables if they do not already exist.
    """

    connection = get_db_connection()

    # Stores one row for every conversation.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Stores every message belonging to a conversation.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
        )
        """
    )

    connection.commit()
    connection.close()


# Create the database/tables when the backend starts.
initialize_database()


# ============================================================
# DATABASE HELPER FUNCTIONS
# ============================================================

def create_new_conversation(title="New conversation"):
    """
    Create a new conversation and return its ID.
    """

    conversation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    connection = get_db_connection()

    connection.execute(
        """
        INSERT INTO conversations (
            id,
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            title,
            now,
            now,
        ),
    )

    connection.commit()
    connection.close()

    return conversation_id


def generate_conversation_title(message: str):
    """
    Generate a short conversation title from the user's first message.
    """

    text = message.lower().strip()

    symptom_titles = [
        ("headache", "Headache"),
        ("migraine", "Migraine"),
        ("stomach", "Stomach pain"),
        ("abdominal pain", "Stomach pain"),
        ("nausea", "Nausea"),
        ("vomiting", "Vomiting"),
        ("cough", "Cough"),
        ("fever", "Fever"),
        ("sore throat", "Sore throat"),
        ("back pain", "Back pain"),
        ("chest pain", "Chest pain"),
        ("dizzy", "Dizziness"),
        ("dizziness", "Dizziness"),
        ("rash", "Rash"),
        ("fatigue", "Fatigue"),
        ("shortness of breath", "Breathing problem"),
        ("stomach ache", "Stomach pain"),
        ("diarrhea", "Diarrhea"),
        ("constipation", "Constipation"),
        ("ear pain", "Ear pain"),
        ("tooth pain", "Tooth pain"),
    ]

    for keyword, title in symptom_titles:
        if keyword in text:
            return title

    return "Health assessment"


def update_conversation_title(conversation_id, title):
    """
    Update the title of a conversation.
    """

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE conversations
        SET title = ?
        WHERE id = ?
        """,
        (
            title,
            conversation_id,
        ),
    )

    connection.commit()
    connection.close()


def conversation_exists(conversation_id):
    """
    Check whether a conversation exists.
    """

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,),
    ).fetchone()

    connection.close()

    return row is not None


def get_conversation_messages(conversation_id):
    """
    Load all messages belonging to one conversation
    in chronological order.
    """

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,),
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def save_message(conversation_id, role, content):
    """
    Save a message and update the conversation timestamp.
    """

    now = datetime.now(timezone.utc).isoformat()

    connection = get_db_connection()

    connection.execute(
        """
        INSERT INTO messages (
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
            now,
        ),
    )

    connection.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (
            now,
            conversation_id,
        ),
    )

    connection.commit()
    connection.close()


def get_conversation(conversation_id):
    """
    Get the metadata for one conversation.
    """

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()


# Allow the React frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# OPENAI
# ============================================================

# Get OpenAI API key.
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")


# Create OpenAI client.
client = OpenAI(api_key=api_key)


# ============================================================
# RESPONSE MODELS
# ============================================================

# Describes a possible explanation for the user's symptoms.
class Possibility(BaseModel):
    name: str
    status: str
    reason: str


# Describes the urgency of the situation.
class Urgency(BaseModel):
    level: str
    reason: str


# Describes the structured response returned by the AI.
class AIResponse(BaseModel):
    question: Optional[str] = None
    input_type: Optional[str] = None
    options: Optional[list[str]] = None
    assessment_complete: bool
    summary: Optional[str] = None
    possibilities: list[Possibility] = []
    urgency: Optional[Urgency] = None


# ============================================================
# BASIC ROUTE
# ============================================================

@app.get("/")
def root():
    return {"message": "Doctor AI backend is working!"}


# ============================================================
# CREATE NEW CONVERSATION
# ============================================================

@app.post("/api/conversations")
def create_conversation():
    """
    Create a brand-new conversation.
    """

    conversation_id = create_new_conversation()

    conversation = get_conversation(conversation_id)

    return conversation


# ============================================================
# GET CONVERSATION HISTORY
# ============================================================

@app.get("/api/conversations")
def get_conversations():
    """
    Return all saved conversations, newest first.

    This will eventually populate the Chat History
    section of the left sidebar.
    """

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ============================================================
# GET ONE CONVERSATION
# ============================================================

@app.get("/api/conversations/{conversation_id}")
def get_one_conversation(conversation_id: str):
    """
    Return one conversation and all of its messages.
    """

    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = get_conversation_messages(conversation_id)

    return {
        **conversation,
        "messages": messages,
    }


# ============================================================
# CHAT
# ============================================================

@app.post("/api/chat")
def chat(
    message: str,
    conversation_id: Optional[str] = None,
):

    # ========================================================
    # GET OR CREATE CONVERSATION
    # ========================================================

    # If no conversation ID was provided,
    # create a new conversation automatically.
    if conversation_id is None:
        conversation_id = create_new_conversation()

    # If an ID was provided, make sure it exists.
    elif not conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )


    # ========================================================
    # LOAD THIS CONVERSATION'S HISTORY
    # ========================================================

    conversation_history = get_conversation_messages(
        conversation_id
    )


    # ========================================================
    # GENERATE TITLE FOR FIRST MESSAGE
    # ========================================================

    # If this is the first message in the conversation,
    # generate a short title based on what the user described.
    if len(conversation_history) == 0:
        title = generate_conversation_title(message)

        update_conversation_title(
            conversation_id,
            title,
        )


    # ========================================================
    # SAVE USER MESSAGE
    # ========================================================

    conversation_history.append({
        "role": "user",
        "content": message,
    })

    save_message(
        conversation_id,
        "user",
        message,
    )


    # ========================================================
    # AI INSTRUCTIONS
    # ========================================================

    instructions = """
    You are Doctor AI, a health assessment assistant.

    Your job is to help users organize and understand their symptoms
    and determine what information may be important to discuss with
    a healthcare professional.

    You are NOT a doctor and must not claim to provide a definitive
    diagnosis.

    ============================================================
    GENERAL BEHAVIOR
    ============================================================

    1. Ask relevant follow-up questions when important information
       is missing.

    2. Consider symptoms together rather than treating each symptom
       independently.

    3. Clearly distinguish information reported by the user from
       assumptions or possibilities.

    4. Communicate uncertainty clearly.

    5. Never invent medical history, test results, medications,
       symptoms, or other user information.

    6. Be calm, respectful, concise, and easy to understand.

    7. Do not overwhelm the user with unnecessary questions.

    8. Ask only for information that could meaningfully affect the
       assessment.

    9. Your purpose is to help the user understand their symptoms
       and decide what information may be important to discuss with
       a healthcare professional.

    ============================================================
    CONVERSATION FLOW
    ============================================================

    The assessment should feel like a natural conversation rather
    than a long medical questionnaire.

    Ask questions progressively.

    Start with the most useful basic information about the main
    symptom, then use the user's previous answers to decide what
    information is useful to ask for next.

    Ask ONE focused question at a time.

    Do not ask a large list of questions all at once.

    Keep each question focused on ONE category of information.

    Do NOT combine unrelated categories into one question.

    For example, do not combine:
    - current symptoms
    - medical history
    - medications
    - emergency warning signs
    - diagnostic conclusions

    into one question.

    Instead, ask focused questions separately when relevant.

    ============================================================
    QUESTION PRIORITY
    ============================================================

    When deciding what to ask next, prioritize:

    1. Basic characteristics of the main symptom:
       duration, location, severity, frequency, or changes over time.

    2. Important associated symptoms.

    3. Relevant risk factors or medical history.

    4. Urgent warning signs that are relevant to the symptoms
       being discussed.

    Do not ask about information that is unlikely to affect the
    current assessment.

    Do not ask about every possible emergency warning sign at once.

    Only ask about warning signs that are reasonably relevant to
    the user's current symptoms.

    ============================================================
    INPUT TYPES
    ============================================================

    You may choose one of these input types:

    - text:
      Use when the user should describe something in their own words.

    - scale:
      Use for numerical ratings such as pain severity.
      Prefer a 0-10 scale when appropriate.

    - single_choice:
      Use when exactly ONE answer should normally apply.

    - select_all:
      Use when MULTIPLE answers can apply simultaneously.

    When using single_choice or select_all, generate a short,
    focused list of options specifically relevant to the question.

    Do not create unnecessary options.

    Examples:

    "Where is the pain located?"
    -> usually single_choice

    "Which symptoms are you experiencing?"
    -> usually select_all

    Do not use single_choice when multiple options could reasonably
    be true at the same time.

    Do not use select_all simply because it is available.

    Avoid unnecessary "Other" options unless the user could
    reasonably have an answer that is not represented.

    Avoid "None of the above" unless it is genuinely useful.

    ============================================================
    EVOLVING POSSIBILITIES
    ============================================================

    During the interview, maintain a SMALL list of the most relevant
    possible explanations based only on information the user has
    actually provided.

    This list is not a diagnosis.

    It is an evolving set of possibilities that helps the user see
    how the assessment is changing as more information is collected.

    When assessment_complete is false:

    - Provide approximately 2-4 of the most relevant possibilities.
    - Do not provide a huge list.
    - Update the possibilities as new evidence is provided.
    - Remove possibilities that become substantially less consistent.
    - Add a new possibility only when new information makes it
      meaningfully relevant.
    - Keep possibilities that remain reasonably plausible.
    - Do not present a possibility as impossible.
    - Use only these statuses:
      "more_consistent"
      "possible"
      "less_consistent"

    The "reason" should briefly explain why the current information
    affects that possibility.

    The possibilities should reflect the CURRENT information in the
    conversation, not generic lists of diseases.

    If there is not enough information to produce useful possibilities,
    return an empty array.

    ============================================================
    ASSESSMENT COMPLETION
    ============================================================

    You have two possible actions:

    1. Ask another follow-up question if important information
       is still missing.

    2. Stop questioning and provide a preliminary assessment when
       enough relevant information has been collected.

    Set "assessment_complete" to false when you need more information.

    Set "assessment_complete" to true when you have enough information
    to provide a useful preliminary assessment.

    Do NOT continue asking questions simply because additional
    questions could theoretically be asked.

    Once enough information has been collected, stop asking
    questions and provide the preliminary assessment.

    ============================================================
    WHEN ASSESSMENT IS INCOMPLETE
    ============================================================

    When assessment_complete is false:

    - Ask exactly ONE useful follow-up question.
    - Put that question in the "question" field.
    - Choose the most appropriate input_type.
    - Provide options only when using single_choice or select_all.
    - Set "summary" to null.
    - Provide approximately 2-4 relevant possibilities when there
      is enough information to make the list useful.
    - Set "urgency" to null unless there is an immediate safety
      concern that needs to be communicated.

    ============================================================
    WHEN ASSESSMENT IS COMPLETE
    ============================================================

    When assessment_complete is true:

    - Stop asking follow-up questions.
    - Put a concise explanation of the assessment in "summary".
    - Set "question" to null.
    - Set "input_type" to null.
    - Set "options" to null.
    - Provide approximately 2-4 relevant possible explanations.
    - Each possibility must have a name, status, and brief reason.
    - Provide an urgency assessment.

    The assessment is preliminary and must NEVER be presented as
    a definitive diagnosis.

    ============================================================
    POSSIBLE EXPLANATIONS
    ============================================================

    Each possibility must contain:

    - name
    - status
    - reason

    The status MUST be exactly one of:

    "more_consistent"
    "possible"
    "less_consistent"

    Use "more_consistent" when the reported information fits that
    possibility relatively well.

    Use "possible" when the available information does not strongly
    favor or disfavor it.

    Use "less_consistent" when some information makes it less
    consistent, but it cannot be definitively ruled out.

    Never use "impossible".

    Never claim that a condition has been completely ruled out based
    only on this conversation.

    Only include explanations that are reasonably relevant to the
    symptoms actually reported by the user.

    ============================================================
    SUMMARY
    ============================================================

    When the assessment is complete, the summary should:

    - briefly describe the main reported symptoms
    - mention the most important relevant details
    - state that this is a preliminary assessment
    - communicate important uncertainty
    - avoid unnecessary medical jargon

    Keep the summary concise.

    ============================================================
    URGENCY
    ============================================================

    When the assessment is complete, provide an urgency object.

    The urgency level MUST be exactly one of:

    "routine"
    "contact_clinician"
    "urgent"

    Use "routine" when:

    - No urgent warning signs were reported.
    - The symptoms described do not suggest an immediate need for
      professional evaluation based on the available information.
    - The user may reasonably monitor the symptoms and use
      appropriate general self-care information.

    IMPORTANT:

    Do NOT automatically recommend contacting a healthcare
    professional simply because the assessment is uncertain.

    Uncertainty is expected in a conversational health assessment
    and does NOT by itself require a medical visit.

    Use "contact_clinician" when:

    - The symptoms are persistent, recurring, unusually disruptive,
      or significant enough that non-urgent professional evaluation
      would be reasonable.
    - The user may benefit from an examination, testing, or other
      information that cannot reasonably be obtained through this
      conversation.
    - The symptoms are not clearly urgent but professional evaluation
      would reasonably add value.

    Use "urgent" when:

    - The reported information could indicate a medical emergency
      or another situation requiring prompt professional evaluation.

    Choose the urgency level based on the ACTUAL INFORMATION
    PROVIDED BY THE USER.

    Do NOT use "contact_clinician" as a generic disclaimer.

    Do NOT recommend a healthcare visit merely because you cannot
    provide certainty.

    Do NOT recommend emergency care unless the reported information
    provides a reasonable basis for doing so.

    The urgency reason should briefly explain why the selected
    level was chosen.

    ============================================================
    SAFETY
    ============================================================

    If the user reports symptoms that could indicate a medical
    emergency, clearly communicate that urgent professional
    evaluation may be appropriate.

    Do not minimize potentially serious symptoms.

    Do not claim the system can rule out serious conditions.

    Do not claim that the absence of a reported warning sign
    guarantees that a serious condition is impossible.

    Do not recommend prescription medications or tell the user
    to change prescribed treatment.

    ============================================================
    RESPONSE FORMAT
    ============================================================

    Always return exactly this JSON structure:

    {
      "question": "question or null",
      "input_type": "text | scale | single_choice | select_all | null",
      "options": ["option 1", "option 2"],
      "assessment_complete": false,
      "summary": "summary or null",
      "possibilities": [
        {
          "name": "Example condition",
          "status": "possible",
          "reason": "Brief explanation."
        }
      ],
      "urgency": {
        "level": "routine",
        "reason": "Brief explanation."
      }
    }

    When assessment_complete is false:

    - question must contain the next question
    - input_type must be one of:
      "text", "scale", "single_choice", "select_all"
    - possibilities may contain approximately 2-4 current possibilities
    - summary must be null

    When assessment_complete is true:

    - question must be null
    - input_type must be null
    - options must be null
    - summary must contain the assessment summary
    - possibilities must contain approximately 2-4 possibilities
    - urgency must contain an appropriate urgency level

    Keep responses concise.
    """


    # ========================================================
    # SEND CONVERSATION TO AI
    # ========================================================

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=conversation_history,
        text={
            "format": {
                "type": "json_schema",
                "name": "ai_assessment",
                "schema": {
                    "type": "object",

                    "properties": {

                        "question": {
                            "type": [
                                "string",
                                "null"
                            ]
                        },

                        "input_type": {
                            "type": [
                                "string",
                                "null"
                            ],
                            "enum": [
                                "text",
                                "scale",
                                "single_choice",
                                "select_all",
                                None
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
                        },

                        "summary": {
                            "type": [
                                "string",
                                "null"
                            ]
                        },

                        "possibilities": {
                            "type": "array",

                            "items": {
                                "type": "object",

                                "properties": {

                                    "name": {
                                        "type": "string"
                                    },

                                    "status": {
                                        "type": "string",
                                        "enum": [
                                            "more_consistent",
                                            "possible",
                                            "less_consistent"
                                        ]
                                    },

                                    "reason": {
                                        "type": "string"
                                    }
                                },

                                "required": [
                                    "name",
                                    "status",
                                    "reason"
                                ],

                                "additionalProperties": False
                            }
                        },

                        "urgency": {
                            "type": [
                                "object",
                                "null"
                            ],

                            "properties": {

                                "level": {
                                    "type": "string",
                                    "enum": [
                                        "routine",
                                        "contact_clinician",
                                        "urgent"
                                    ]
                                },

                                "reason": {
                                    "type": "string"
                                }
                            },

                            "required": [
                                "level",
                                "reason"
                            ],

                            "additionalProperties": False
                        }
                    },

                    "required": [
                        "question",
                        "input_type",
                        "options",
                        "assessment_complete",
                        "summary",
                        "possibilities",
                        "urgency"
                    ],

                    "additionalProperties": False
                }
            }
        }
    )


    # ========================================================
    # PROCESS AI RESPONSE
    # ========================================================

    # Convert the AI's JSON text into a Python dictionary.
    data = json.loads(response.output_text)


    # Make sure possibilities is always a list.
    if not isinstance(data.get("possibilities"), list):
        data["possibilities"] = []


    # Limit the number of possibilities shown.
    if len(data["possibilities"]) > 4:
        data["possibilities"] = data["possibilities"][:4]


    # Make sure the AI returned a valid input type.
    allowed_input_types = {
        "text",
        "scale",
        "single_choice",
        "select_all"
    }

    if (
        data["input_type"] is not None
        and data["input_type"] not in allowed_input_types
    ):
        data["input_type"] = "text"
        data["options"] = None


    # Make sure urgency has a valid level.
    if data.get("urgency") is not None:

        allowed_urgency_levels = {
            "routine",
            "contact_clinician",
            "urgent"
        }

        if data["urgency"].get("level") not in allowed_urgency_levels:

            data["urgency"] = {
                "level": "contact_clinician",
                "reason": (
                    "The assessment should be reviewed by a "
                    "healthcare professional."
                )
            }


    # Make sure incomplete assessments have no summary.
    if not data["assessment_complete"]:
        data["summary"] = None


    # Make sure completed assessments don't contain a question UI.
    if data["assessment_complete"]:
        data["question"] = None
        data["input_type"] = None
        data["options"] = None


    # ========================================================
    # SAVE AI RESPONSE
    # ========================================================

    # Save the user-visible AI message rather than the raw JSON.
    if data["assessment_complete"]:
        assistant_message = (
            "I've gathered enough information to provide a preliminary assessment."
        )
    else:
        assistant_message = data["question"] or ""

    save_message(
        conversation_id,
        "assistant",
        assistant_message,
    )


    # ========================================================
    # RETURN TO REACT
    # ========================================================

    data["conversation_id"] = conversation_id

    return data