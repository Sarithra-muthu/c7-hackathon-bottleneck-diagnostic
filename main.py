from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, ClientOptions
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
)
print("Using key starting with:", SUPABASE_KEY[:15])

CATEGORIES = """
1. Never started — comparing self to others instead of attempting anything
2. Tried once, gave up, no real task in mind
3. Knows exactly what they want, but deprioritizes it (time/effort, not ability)
4. Doesn't trust AI output enough to rely on it
5. Tried but got generic/unhelpful results and stopped
6. Fear of looking behind/slow in front of others
"""

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class DiagnoseRequest(BaseModel):
    user_text: str
    access_token: str

@app.post("/signup")
def signup(req: SignupRequest):
    result = supabase.auth.sign_up({"email": req.email, "password": req.password})
    user_id = result.user.id
    # Insert into person table
    supabase.rpc("create_person", {"p_id": user_id, "p_name": req.name}).execute()
    return {"message": "Signed up", "user_id": user_id}

@app.post("/login")
def login(req: LoginRequest):
    result = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
    return {
        "access_token": result.session.access_token,
        "user_id": result.user.id,
        "name": req.email
    }

def diagnose(user_text: str):
    prompt = f"""You are diagnosing someone's real bottleneck with using AI.

They wrote: "{user_text}"

Here are the only 6 categories you are allowed to choose from:
{CATEGORIES}

Pick exactly ONE category number that best fits what they wrote.
Then write ONE sentence speaking DIRECTLY to the person using "you" and "your" (never "they" or "their"), in this exact format, quoting or referencing their own words as evidence:
"It's not [surface complaint], it's [the real reason], and that's why [your likely next move] won't fix it."

Example: "It's not that you can't use AI, it's that you've never made it a priority over the thing you'd rather be doing, and that's why telling yourself you'll 'get to it later' won't work."

Respond in this exact format:
CATEGORY: <number>
SENTENCE: <the one sentence>
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    output = response.choices[0].message.content
    category, sentence = "", ""
    for line in output.split("\n"):
        if line.startswith("CATEGORY:"):
            category = line.replace("CATEGORY:", "").strip()
        if line.startswith("SENTENCE:"):
            sentence = line.replace("SENTENCE:", "").strip()
    return category, sentence

@app.post("/diagnose")
def diagnose_endpoint(req: DiagnoseRequest):
    # Verify the user via their access token
    user_response = supabase.auth.get_user(req.access_token)
    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = user_response.user.id

    category, sentence = diagnose(req.user_text)

    # Use a client scoped to this user's token so RLS applies correctly
    supabase.rpc("create_session", {
        "p_person_id": user_id,
        "p_user_text": req.user_text,
        "p_category": category,
        "p_sentence": sentence,
    }).execute()

    return {"category": category, "diagnosis": sentence}

@app.get("/my-sessions")
def get_my_sessions(access_token: str):
    user_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    user_supabase.postgrest.auth(access_token)
    result = user_supabase.table("session").select("*").execute()
    return result.data