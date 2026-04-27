# 🗳️ VoteSmart: Election Education Assistant

> **Empowering Citizens through AI-Driven Democratic Literacy** — Google Antigravity  
> Powered by **Google Gemini API** · Built for the **Election Process Education** Challenge

---

## 📌 Overview

**VoteSmart** is a smart, dynamic assistant designed to demystify the election process and encourage democratic participation. Using the power of **Gemini 2.5 Flash-lite**, it provides non-partisan, logical guidance tailored to each user's unique context.

### Key Features
- **Deep Google Integration**: Powered by **Vertex AI** for robust reasoning, with **Firebase Firestore** logging for conversation analytics and **Google Cloud Logging** for system observability.
- **Logical Decision Making**: Evaluates user context (age, location, status) to provide personalized voting advice.
- **Dynamic Interaction**: Smart chat interface that understands complex queries about registration, eligibility, and polling.
- **WCAG AAA Accessibility**: Optimized for all users with ARIA labels, semantic HTML, keyboard navigation, and high-contrast styling.
- **Efficiency Optimized**: Leverages asynchronous execution patterns and intelligent multi-level caching.
- **Non-Partisan Guidance**: Strictly follows neutrality to focus purely on the *process* of democracy.

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/exedistrict-ux/AI-Driven-Task-Orchestrator.git
cd AI-Driven-Task-Orchestrator
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up Gemini API
Create a `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run tests
```bash
python test_app.py
```

---

## 🧪 Testing

The project includes a comprehensive test suite in `test_app.py` that uses the standard `unittest` library. It covers:
- **Assistant Initialization**: Verifies the AI component setup.
- **Mocked Responses**: Ensures the logic handles Gemini API responses correctly without incurring costs.
- **Error Handling**: Tests behavior when API keys are missing.

---

## 🏗️ Architecture

```mermaid
graph TD
    A[User Input] --> B[Gradio Web UI]
    B --> C[Gemini 2.5 Flash-lite]
    C --> D{Context Evaluator}
    D -->|Eligibility| E[Tailored Voting Guide]
    D -->|Process| F[Interactive FAQ]
    D -->|Action| G[Registration Steps]
```

The assistant uses a specialized **System Instruction** to ensure it remains a helpful, non-partisan educator while maintaining high conversational quality.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `google-genai` | Gemini API for intelligent reasoning |
| `gradio` | Web Interface with custom premium styling |
| `python-dotenv` | Secure environment management |

---

## 🔒 Commitment to Rules
- **Size**: Repository maintained well under 1MB.
- **Public**: Ready for public GitHub deployment.
- **Single Branch**: Optimized for main branch development.

---

*Built with ❤️ for the Google Antigravity.*
