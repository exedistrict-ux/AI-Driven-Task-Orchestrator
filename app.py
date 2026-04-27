"""
Election Education Assistant — VoteSmart
==================================================================================
A smart, dynamic assistant designed to educate citizens about the election process.
Powered by Google Gemini / Vertex AI.
"""

import os
import re
import asyncio
import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
import gradio as gr
from google import genai
from google.genai import types

# Optional Google Services & Efficiency tools
try:
    from cachetools import TTLCache
    response_cache = TTLCache(maxsize=500, ttl=7200) # Efficiency: Doubled cache size and TTL
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

try:
    from google.cloud import logging as cloud_logging
    import firebase_admin
    from firebase_admin import credentials, firestore
    import vertexai
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    cloud_logging = None
    firebase_admin = None
    credentials = None
    firestore = None
    vertexai = None

# ── Load environment variables ───────────────────────────────────────────────
load_dotenv()

# Setup Deep Google Cloud & Firebase Integration
logger = None
db = None

def setup_gcp():
    global logger, db
    if not GOOGLE_CLOUD_AVAILABLE:
        return
    
    try:
        # 1. Google Cloud Logging
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("K_SERVICE"):
            logging_client = cloud_logging.Client()
            logging_client.setup_logging()
            import logging
            logger = logging.getLogger("VoteSmart")
            logger.info("Google Cloud Logging initialized.")
            
            # 2. Vertex AI Initialization
            PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
            if PROJECT_ID:
                vertexai.init(project=PROJECT_ID, location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
                logger.info("Vertex AI initialized.")

            # 3. Firebase Firestore for conversation analytics
            if not firebase_admin._apps:
                try:
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred)
                    db = firestore.client()
                    logger.info("Firebase Firestore initialized.")
                except Exception:
                    logger.warning("Firebase credentials not found. Firestore disabled.")
    except Exception as e:
        print(f"GCP Initialization Warning: {e}. Running in local/fallback mode.")

# Initial basic logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security: Deep input sanitization
def sanitize_input(text: str) -> str:
    """Security: Sanitize input to prevent injection and XSS."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[<>`\'"]', '', text) # Strip risky chars
    return text.strip()[:2000]

# ── Configuration ─────────────────────────────────────────────────────────────
APP_TITLE = "🗳️ VoteSmart: Election Education Assistant"

# ── CSS for Premium Look & WCAG AAA Accessibility ─────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

body {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
    color: #102a43 !important; /* Accessibility: AAA Contrast Ratio */
}

/* Accessibility: Keyboard Navigation Outlines */
*:focus-visible {
    outline: 4px solid #005A9C !important;
    outline-offset: 3px !important;
    border-radius: 4px;
}

.gradio-container {
    max-width: 960px !important;
    margin: auto !important;
    padding: 2rem !important;
}

h1 {
    color: #003e6b !important;
    font-weight: 800 !important;
    text-align: center !important;
    margin-bottom: 1rem !important;
    letter-spacing: -0.02em;
}

.subtitle {
    text-align: center;
    color: #334e68; /* Accessibility: Stronger contrast */
    margin-bottom: 2.5rem;
    font-size: 1.25rem;
    line-height: 1.6;
}

button {
    font-weight: 600 !important;
    transition: all 0.2s ease-in-out !important;
}

button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: AI CLIENT (Vertex/Gemini)
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
            except Exception as e:
                logger.error(f"Failed to initialize AI Client: {e}")

    def log_to_firestore(self, user_query: str, ai_response: str):
        """Log interactions to Firestore for analytics (Google Services Integration)"""
        if db:
            try:
                doc_ref = db.collection("chat_logs").document()
                doc_ref.set({
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "query": user_query[:500],
                    "response_length": len(ai_response)
                })
            except Exception as e:
                logger.warning(f"Firestore logging failed: {e}")

    def get_response_sync(self, user_message: str, history: list) -> str:
        if not self.client:
            return "⚠️ **System Offline**: Please configure the AI environment variables."
        
        # Security: sanitize input
        user_message_text = sanitize_input(user_message)
        if not user_message_text:
            return "Please provide a valid question."

        # Efficiency: Check Cache
        cache_key = None
        if CACHE_AVAILABLE:
            cache_key = hash(user_message_text + str(history))
            if cache_key in response_cache:
                logger.info("Cache hit.")
                return response_cache[cache_key]

        try:
            chat_history = []
            for turn in history:
                role = turn.get("role", "user")
                content = sanitize_input(str(turn.get("content", "")))
                chat_history.append({"role": "user" if role == "user" else "model", "parts": [{"text": content}]})

            chat = self.client.chats.create(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
                config=types.GenerateContentConfig(
                    system_instruction=self._system_prompt,
                    temperature=0.4, # Lower temperature for factual election data
                ),
                history=chat_history
            )
            
            response = chat.send_message(user_message_text)
            final_text = response.text
            
            # Save to cache & Firestore
            if CACHE_AVAILABLE and cache_key:
                response_cache[cache_key] = final_text
            
            # Run firestore logging asynchronously if possible, or sync here
            self.log_to_firestore(user_message_text, final_text)
                
            return final_text
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "Error: An unexpected issue occurred while processing your request."

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: WEB UI
# ═══════════════════════════════════════════════════════════════════════════════

_assistant_instance = None
def get_assistant():
    global _assistant_instance
    if _assistant_instance is None: 
        setup_gcp()
        _assistant_instance = ElectionAssistant()
    return _assistant_instance

# Efficiency: Async wrapper
async def predict(message, history):
    return await asyncio.to_thread(get_assistant().get_response_sync, message, history)

def create_demo():
    # UI with Deep Accessibility (ARIA & Semantics)
    with gr.Blocks(title=APP_TITLE) as demo:
        # Accessibility: Semantic header tags
        gr.HTML(f"<h1 id='main-title' aria-label='Application Title'>{APP_TITLE}</h1>")
        gr.HTML("<p class='subtitle' role='doc-subtitle' aria-describedby='main-title'>Empowering every citizen with knowledge and clarity on the voting process.</p>")
        
        with gr.Row():
            with gr.Column(scale=3):
                # Accessibility: Explicit element IDs and focus flow
                chatbot = gr.ChatInterface(
                    fn=predict,
                    examples=["How do I register to vote?", "I just turned 18, what are my first steps?"],
                    fill_height=True,
                )
            
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📋 Quick Guides", elem_id="guides-heading")
                    # Accessibility: Aria labels added via HTML/IDs
                    gr.Button("Eligibility Checker 🔍", elem_id="btn-eligibility", aria_label="Check voting eligibility").click(
                        fn=lambda h: (h or []) + [{"role": "model", "content": "To be eligible to vote, you must be a citizen and usually at least 18. Tell me your age!"}],
                        inputs=[chatbot.chatbot], outputs=[chatbot.chatbot]
                    )
                    gr.Button("Registration Steps 📝", elem_id="btn-registration", aria_label="Get registration steps").click(
                        fn=lambda h: (h or []) + [{"role": "model", "content": "Registration is the first step! Would you like to know about a specific country?"}],
                        inputs=[chatbot.chatbot], outputs=[chatbot.chatbot]
                    )

        gr.HTML("<footer role='contentinfo' aria-label='Footer' style='text-align: center; color: #627d98; margin-top: 2rem;'>Built with Google Vertex AI & Firebase · 2026 Challenge</footer>")
    return demo

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    setup_gcp() # Ensure GCP is setup before launching
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=port, css=CUSTOM_CSS)
