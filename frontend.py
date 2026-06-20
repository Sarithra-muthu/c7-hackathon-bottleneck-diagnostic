import gradio as gr
import requests

API_URL = "https://c7-hackathon-bottleneck-diagnostic.onrender.com"

# Keep track of the logged-in user's token in memory during the session
session_state = {"access_token": None, "user_id": None}

def signup(email, password, name):
    response = requests.post(f"{API_URL}/signup", json={
        "email": email, "password": password, "name": name
    })
    if response.status_code == 200:
        return "Signed up! Now log in below."
    return f"Signup failed: {response.text}"

def login(email, password):
    response = requests.post(f"{API_URL}/login", json={
        "email": email, "password": password
    })
    if response.status_code == 200:
        data = response.json()
        session_state["access_token"] = data["access_token"]
        session_state["user_id"] = data["user_id"]
        return "Logged in! You can now use the diagnostic below."
    return f"Login failed: {response.text}"

def diagnose(user_text):
    if not session_state["access_token"]:
        return "Please log in first."
    response = requests.post(f"{API_URL}/diagnose", json={
        "user_text": user_text,
        "access_token": session_state["access_token"]
    })
    if response.status_code == 200:
        return response.json()["diagnosis"]
    return f"Error: {response.text}"

with gr.Blocks(title="AI Bottleneck Diagnostic") as demo:
    gr.Markdown("# AI Bottleneck Diagnostic")

    with gr.Tab("Sign Up"):
        su_email = gr.Textbox(label="Email")
        su_password = gr.Textbox(label="Password", type="password")
        su_name = gr.Textbox(label="Name")
        su_button = gr.Button("Sign Up")
        su_output = gr.Textbox(label="Status")
        su_button.click(signup, inputs=[su_email, su_password, su_name], outputs=su_output)

    with gr.Tab("Log In"):
        li_email = gr.Textbox(label="Email")
        li_password = gr.Textbox(label="Password", type="password")
        li_button = gr.Button("Log In")
        li_output = gr.Textbox(label="Status")
        li_button.click(login, inputs=[li_email, li_password], outputs=li_output)

    with gr.Tab("Diagnose"):
        gr.Markdown("Tell me where you feel stuck with AI — something you wanted it to help with, what happened (or why you never tried), and what's stopped you from going back to it.")
        diag_input = gr.Textbox(label="Your stuck-story", lines=5)
        diag_button = gr.Button("Diagnose Me")
        diag_output = gr.Textbox(label="Your Diagnosis")
        diag_button.click(diagnose, inputs=diag_input, outputs=diag_output)

demo.launch()