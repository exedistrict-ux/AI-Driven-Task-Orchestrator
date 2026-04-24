"""
Election Education Assistant — VoteSmart
==================================================================================
A smart, dynamic assistant designed to educate citizens about the election process.
Powered by Google Gemini API.
"""

import os
import json
import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
import gradio as gr
from google import genai
from google.genai import types

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
APP_TITLE = "🗳️ VoteSmart: Election Education Assistant"
THEME_COLOR = "#1a5f7a"  # Elegant electoral blue

# ── CSS for Premium Look ──────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

body {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
    padding-top: 2rem !important;
}

h1 {
    color: #1a5f7a !important;
    font-weight: 700 !important;
    text-align: center !important;
    margin-bottom: 0.5rem !important;
}

.subtitle {
    text-align: center;
    color: #4a5568;
    margin-bottom: 2rem;
    font-size: 1.1rem;
}

.card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    margin-bottom: 1rem;
}

.chat-window {
    border-radius: 12px !important;
    overflow: hidden !important;
}

footer {
    display: none !important;
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: GEMINI CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class ElectionAssistant:
    SYSTEM_PROMPT = """
You are "VoteSmart", a highly intelligent and encouraging Election Education Assistant.
Your goal is to educate users about the election process, voting rights, and democratic participation.

Rules:
1. Be non-partisan. Never favor any political party or candidate.
2. Provide accurate information based on general democratic principles.
3. If asked about a specific country's rules (like India or USA), adapt your context.
4. Use formatting (bolding, lists) to make information easy to digest.
5. Be proactive: if a user asks about registration, explain the common requirements.
6. For logical decision making: if a user describes their situation (e.g., "I'm 17", "I just moved"), provide tailored advice on what they should do next.

Context:
- Today's date: {today}
"""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self._system_prompt = self.SYSTEM_PROMPT.replace("{today}", datetime.date.today().isoformat())
            except Exception:
                self.client = None

    def get_response(self, user_message: str, history: list) -> str:
        if not self.client:
            return "⚠️ **API Key Missing**: Please set the `GEMINI_API_KEY` environment variable."
        
        try:
            # Helper to extract text from Gradio message content
            def extract_text(msg_content):
                if isinstance(msg_content, str):
                    return msg_content
                elif isinstance(msg_content, list):
                    parts = []
                    for p in msg_content:
                        if isinstance(p, dict) and "text" in p:
                            parts.append(p["text"])
                        elif isinstance(p, str):
                            parts.append(p)
                    return " ".join(parts)
                elif isinstance(msg_content, dict) and "text" in msg_content:
                    return msg_content["text"]
                return str(msg_content)

            # Convert Gradio 6.0 history format to Gemini format
            chat_history = []
            for turn in history:
                role = turn.get("role", "user")
                content = extract_text(turn.get("content", ""))
                gemini_role = "user" if role == "user" else "model"
                chat_history.append({"role": gemini_role, "parts": [{"text": content}]})

            chat = self.client.chats.create(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
                config=types.GenerateContentConfig(
                    system_instruction=self._system_prompt,
                    temperature=0.7,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
                history=chat_history
            )
            
            user_message_text = extract_text(user_message)
            response = chat.send_message(user_message_text)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: WEB UI
# ═══════════════════════════════════════════════════════════════════════════════

# Global assistant instance for the web server
_assistant_instance = None

def get_assistant():
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = ElectionAssistant()
    return _assistant_instance

def predict(message, history):
    return get_assistant().get_response(message, history)

def create_demo():
    # Building the UI
    with gr.Blocks() as demo:
        gr.Markdown(f"# {APP_TITLE}")
        gr.Markdown("<p class='subtitle'>Empowering every citizen with knowledge and clarity on the voting process.</p>")
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.ChatInterface(
                    fn=predict,
                    examples=[
                        "How do I register to vote?",
                        "What documents do I need for voting?",
                        "I just turned 18, what are my first steps?",
                        "Explain the importance of a secret ballot.",
                        "How can I check if I am on the electoral roll?"
                    ],
                    fill_height=True,
                )
            
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📋 Quick Guides")
                    gr.Button("Eligibility Checker 🔍").click(
                        fn=lambda h: (h or []) + [{"role": "model", "content": "To be eligible to vote in most democracies, you must be a citizen and usually at least 18 years old. Tell me your age and citizenship status for more details!"}],
                        inputs=[chatbot.chatbot],
                        outputs=[chatbot.chatbot]
                    )
                    gr.Button("Registration 📝").click(
                        fn=lambda h: (h or []) + [{"role": "model", "content": "Registration is the first step! In most places, you can register online or at a local election office. Would you like to know about a specific country?"}],
                        inputs=[chatbot.chatbot],
                        outputs=[chatbot.chatbot]
                    )
                    gr.Button("Voting Day Tips 🗳️").click(
                        fn=lambda h: (h or []) + [{"role": "model", "content": "1. Locate your polling station in advance. 2. Carry your ID. 3. Know the voting hours. Anything specific you want to know?"}],
                        inputs=[chatbot.chatbot],
                        outputs=[chatbot.chatbot]
                    )

        gr.Markdown("---")
        gr.Markdown("<p style='text-align: center; color: #718096; font-size: 0.8rem;'>Built with Google Gemini & Antigravity Framework · 2026 Challenge</p>")
    return demo

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0", 
        server_port=port,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="cyan")
    )
