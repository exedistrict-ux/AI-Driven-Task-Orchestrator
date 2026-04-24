# 🤖 AI-Driven Task Orchestrator

> **Personal Productivity & Event Assistant** — Google Antigravity Challenge 2026  
> Powered by **Google Gemini API** · Integrates with **Google Calendar**

---

## 📌 What It Does

**AI-Driven Task Orchestrator** is a smart, conversational CLI assistant that lets you manage your day in plain English. No commands to memorise — just tell it what you need.

| You say… | It does… |
|---|---|
| *"Add a high priority task to review the Q2 report"* | Saves task to local list |
| *"Show my tasks"* | Renders a rich formatted task table |
| *"Mark 'review the Q2 report' as done"* | Updates task status |
| *"Schedule a team standup tomorrow at 10 AM"* | Creates a Google Calendar event |
| *"What are my upcoming events?"* | Lists your Calendar events |
| *"Explain the Pomodoro technique"* | Answers via Gemini AI |

---

## 🏗️ Architecture

```
User Input (CLI)
      │
      ▼
  Gemini 1.5 Flash  ◄── understands natural language, returns structured JSON
      │
      ▼
  Action Router
  ├── ADD_TASK / LIST_TASKS / COMPLETE_TASK / DELETE_TASK
  │         └──► tasks.json  (local file, persists between sessions)
  ├── ADD_EVENT / LIST_EVENTS
  │         └──► Google Calendar API  (OAuth2)
  └── GENERAL_QUERY
            └──► Gemini answer printed to terminal
```

The app uses a **Gemini system prompt** to enforce structured JSON output, so the router always gets a reliable, type-safe intent object — no brittle keyword matching required.

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/AI-Driven-Task-Orchestrator.git
cd AI-Driven-Task-Orchestrator
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your key for free at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 5. (Optional) Set up Google Calendar

To enable Calendar integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Desktop App)
4. Download `credentials.json` and place it in the `credentials/` folder:

```
credentials/
  credentials.json   ← download from Google Cloud Console
  token.json         ← auto-generated on first run
```

> The app will open a browser window for you to authorise access on the first run.

### 6. Run the assistant

```bash
# With Google Calendar integration:
python app.py

# Without Calendar (task-only mode):
python app.py --no-calendar
```

---

## 💬 Example Session

```
🤖 Welcome
──────────────────────────────────────────────────
  AI-Driven Task Orchestrator
  Personal Productivity & Event Assistant — powered by Google Gemini

  Type your request in plain English, e.g.:
  • Add a high-priority task to review the quarterly report
  • Schedule a team meeting tomorrow at 3 PM
  • Show my tasks
  • What is machine learning?

  Type exit or quit to leave.
──────────────────────────────────────────────────

You: Add a high priority task to finish the slide deck
✔ Task added: finish the slide deck (Priority: high)

You: Add a task to send the weekly update email
✔ Task added: send the weekly update email (Priority: medium)

You: Show my tasks
╭──────────────────────────────────────────────╮
│               📋 Your Tasks                  │
├────┬────────────────────────┬──────────┬──────┤
│ #  │ Task                   │ Priority │Status│
├────┼────────────────────────┼──────────┼──────┤
│ 1  │ finish the slide deck  │  High    │⏳    │
│ 2  │ send weekly update...  │  Medium  │⏳    │
╰────┴────────────────────────┴──────────┴──────╯

You: Schedule a team standup tomorrow at 10 AM for 30 minutes
✔ Event created: team standup
   https://www.google.com/calendar/event?eid=...

You: exit
Goodbye! 👋
```

---

## 📁 Project Structure

```
AI-Driven-Task-Orchestrator/
├── app.py              ← Main application (GeminiClient, TaskManager,
│                         CalendarManager, ActionRouter, CLI loop)
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── .env.example        ← Template for environment variables
├── .gitignore          ← Excludes .env, token.json, __pycache__, etc.
├── tasks.json          ← Auto-created; stores your local tasks
└── credentials/
    ├── credentials.json  ← (You provide) OAuth client secret
    └── token.json        ← (Auto-generated) OAuth access token
```

---

## ⚙️ Configuration

| Variable | Where | Description |
|---|---|---|
| `GEMINI_API_KEY` | `.env` | Your Gemini API key (required) |
| `credentials.json` | `credentials/` | Google OAuth client secret (optional) |

---

## 🔒 Privacy & Security

- `tasks.json` is stored **locally only** — never uploaded anywhere.
- `credentials/token.json` is gitignored and stays on your machine.
- The `.env` file is gitignored — your API key is never committed.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `google-generativeai` | Gemini 1.5 Flash API (NLU + intent extraction) |
| `google-api-python-client` | Google Calendar REST API |
| `google-auth-oauthlib` | OAuth2 flow for Calendar |
| `rich` | Beautiful terminal tables, panels, spinners |
| `python-dotenv` | Loads `.env` into `os.environ` |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

*Built for the Google Antigravity Challenge 2026.*
