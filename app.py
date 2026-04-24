"""
AI-Driven-Task-Orchestrator — Personal Productivity & Event Assistant
======================================================================
Uses Google Gemini API to understand natural-language input and route
actions to a local task manager or Google Calendar.

Author  : AI-Driven-Task-Orchestrator / Google Antigravity Challenge
Python  : 3.9+
Run     : python app.py  [--no-calendar]
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box
import google.generativeai as genai

# ── Load environment variables from .env ─────────────────────────────────────
load_dotenv()

GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ── File paths ────────────────────────────────────────────────────────────────
TASKS_FILE = Path("tasks.json")            # Local task store
CREDS_FILE = Path("credentials/credentials.json")  # OAuth client secret
TOKEN_FILE = Path("credentials/token.json")         # Auto-generated OAuth token

# ── Rich console (used throughout) ───────────────────────────────────────────
console = Console()

# ── Google Calendar scopes ────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: GEMINI CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class GeminiClient:
    """
    Wraps google-generativeai to send structured prompts and parse
    JSON responses that describe the user's intent.
    """

    # System prompt that instructs Gemini to always return a JSON object.
    SYSTEM_PROMPT = """
You are a smart personal productivity assistant.
Your job is to understand the user's message and return a STRICTLY valid JSON
object (no markdown fences, no extra text) describing what they want to do.

Possible intents:
  ADD_TASK       – user wants to add a task / to-do item
  LIST_TASKS     – user wants to see their tasks
  COMPLETE_TASK  – user wants to mark a task as complete / done / finished
  DELETE_TASK    – user wants to delete / remove a task
  ADD_EVENT      – user wants to create a calendar event / reminder / meeting
  LIST_EVENTS    – user wants to see upcoming calendar events
  GENERAL_QUERY  – anything else (answer conversationally in "response" field)

JSON schema to use for each intent:

ADD_TASK:
  { "intent": "ADD_TASK", "task": "<task description>", "priority": "high|medium|low" }

LIST_TASKS:
  { "intent": "LIST_TASKS" }

COMPLETE_TASK:
  { "intent": "COMPLETE_TASK", "task": "<task name or partial match>" }

DELETE_TASK:
  { "intent": "DELETE_TASK", "task": "<task name or partial match>" }

ADD_EVENT:
  { "intent": "ADD_EVENT", "title": "<event title>",
    "datetime": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": <int>,
    "description": "<optional description>" }

LIST_EVENTS:
  { "intent": "LIST_EVENTS" }

GENERAL_QUERY:
  { "intent": "GENERAL_QUERY", "response": "<your helpful answer>" }

Rules:
- Always return ONLY the JSON object.
- For ADD_EVENT, infer a reasonable date/time if the user says "tomorrow", "next Monday", etc.
  Today's date is {today}.
- Default duration_minutes to 60 if not specified.
- Default priority to "medium" for ADD_TASK if not specified.
"""

    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            console.print(
                "[bold red]ERROR:[/] GEMINI_API_KEY is not set.\n"
                "Create a [bold].env[/] file with:\n"
                "  GEMINI_API_KEY=your_key_here",
                style="red",
            )
            sys.exit(1)

        genai.configure(api_key=GEMINI_API_KEY)
        # Use Gemini 1.5 Flash — fast and free-tier friendly
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=self._build_system_prompt(),
        )
        self.chat = self.model.start_chat(history=[])

    def _build_system_prompt(self) -> str:
        """Inject today's date into the system prompt so Gemini can resolve
        relative time references like 'tomorrow' or 'next Friday'."""
        today = datetime.date.today().isoformat()
        return self.SYSTEM_PROMPT.format(today=today)

    def parse_intent(self, user_message: str) -> dict:
        """
        Send user_message to Gemini and return a parsed intent dictionary.
        Falls back to GENERAL_QUERY on any JSON parsing error.
        """
        try:
            response = self.chat.send_message(user_message)
            raw = response.text.strip()

            # Strip markdown code fences in case Gemini wraps JSON anyway
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError:
            # Gemini gave a non-JSON reply — treat as general response
            return {"intent": "GENERAL_QUERY", "response": response.text.strip()}
        except Exception as exc:
            console.print(f"[red]Gemini error:[/] {exc}")
            return {"intent": "GENERAL_QUERY", "response": "Sorry, I encountered an error."}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TASK MANAGER (local JSON store)
# ═══════════════════════════════════════════════════════════════════════════════

class TaskManager:
    """
    Manages a simple JSON-based to-do list stored in tasks.json.
    Each task is a dict: { id, title, priority, done, created_at }
    """

    def __init__(self) -> None:
        self.tasks: list[dict] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load tasks from disk (creates file if absent)."""
        if TASKS_FILE.exists():
            try:
                self.tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.tasks = []
        else:
            self.tasks = []

    def _save(self) -> None:
        """Persist tasks to disk."""
        TASKS_FILE.write_text(
            json.dumps(self.tasks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── CRUD operations ───────────────────────────────────────────────────────

    def add(self, title: str, priority: str = "medium") -> dict:
        """Add a new task and return it."""
        task = {
            "id": len(self.tasks) + 1,
            "title": title,
            "priority": priority.lower(),
            "done": False,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self.tasks.append(task)
        self._save()
        return task

    def complete(self, name: str) -> dict | None:
        """Mark the first task whose title contains `name` as done."""
        for task in self.tasks:
            if name.lower() in task["title"].lower() and not task["done"]:
                task["done"] = True
                self._save()
                return task
        return None

    def delete(self, name: str) -> dict | None:
        """Remove the first task whose title contains `name`."""
        for i, task in enumerate(self.tasks):
            if name.lower() in task["title"].lower():
                removed = self.tasks.pop(i)
                self._save()
                return removed
        return None

    def list_all(self) -> list[dict]:
        """Return all tasks."""
        return self.tasks

    def pending(self) -> list[dict]:
        """Return only incomplete tasks."""
        return [t for t in self.tasks if not t["done"]]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: GOOGLE CALENDAR MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CalendarManager:
    """
    Handles OAuth2 authentication and event management for Google Calendar.
    On first run, opens a browser for the user to authorise access.
    Subsequent runs use the cached token.json.
    """

    def __init__(self) -> None:
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate using OAuth2 and build the Calendar service."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = None

            # Load existing token if available
            if TOKEN_FILE.exists():
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

            # Refresh or re-authenticate if token is missing or expired
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not CREDS_FILE.exists():
                        raise FileNotFoundError(
                            f"credentials.json not found at {CREDS_FILE}.\n"
                            "Download it from Google Cloud Console → APIs & Services → Credentials."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDS_FILE), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Cache the token for future runs
                TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

            self.service = build("calendar", "v3", credentials=creds)
            console.print("[green]✔ Google Calendar connected.[/]")

        except Exception as exc:
            console.print(
                f"[yellow]⚠ Calendar unavailable:[/] {exc}\n"
                "Run with [bold]--no-calendar[/] to use task-only mode."
            )
            self.service = None

    def add_event(
        self,
        title: str,
        start_dt: str,
        duration_minutes: int = 60,
        description: str = "",
    ) -> dict | None:
        """
        Create a Google Calendar event.

        Args:
            title           : Event title/summary
            start_dt        : ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
            duration_minutes: Event duration in minutes (default 60)
            description     : Optional description

        Returns:
            The created event dict or None on failure.
        """
        if not self.service:
            return None

        try:
            start = datetime.datetime.fromisoformat(start_dt)
            end = start + datetime.timedelta(minutes=duration_minutes)

            event_body = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            }

            event = (
                self.service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )
            return event

        except Exception as exc:
            console.print(f"[red]Calendar error:[/] {exc}")
            return None

    def list_events(self, max_results: int = 10) -> list[dict]:
        """
        List upcoming calendar events.

        Returns:
            List of event dicts sorted by start time.
        """
        if not self.service:
            return []

        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return result.get("items", [])

        except Exception as exc:
            console.print(f"[red]Calendar error:[/] {exc}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: DISPLAY HELPERS (Rich terminal UI)
# ═══════════════════════════════════════════════════════════════════════════════

# Priority colour mapping for the task table
PRIORITY_COLOURS = {"high": "red", "medium": "yellow", "low": "cyan"}


def display_tasks(tasks: list[dict]) -> None:
    """Render a formatted table of tasks using Rich."""
    if not tasks:
        console.print("[dim]No tasks found.[/]")
        return

    table = Table(
        title="📋 Your Tasks",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Task", min_width=30)
    table.add_column("Priority", justify="center", width=10)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Created", width=20)

    for task in tasks:
        priority = task.get("priority", "medium")
        colour = PRIORITY_COLOURS.get(priority, "white")
        status = "✅ Done" if task["done"] else "⏳ Pending"
        table.add_row(
            str(task["id"]),
            task["title"],
            f"[{colour}]{priority.capitalize()}[/]",
            status,
            task.get("created_at", "—"),
        )

    console.print(table)


def display_events(events: list[dict]) -> None:
    """Render a formatted table of upcoming Google Calendar events."""
    if not events:
        console.print("[dim]No upcoming events found.[/]")
        return

    table = Table(
        title="📅 Upcoming Events",
        box=box.ROUNDED,
        header_style="bold blue",
        show_lines=True,
    )
    table.add_column("Event", min_width=30)
    table.add_column("Start", width=25)
    table.add_column("Link", min_width=20)

    for event in events:
        start = event.get("start", {})
        start_str = start.get("dateTime", start.get("date", "—"))
        # Format ISO datetime for readability
        try:
            dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            start_str = dt.strftime("%d %b %Y  %H:%M")
        except ValueError:
            pass

        link = event.get("htmlLink", "—")
        table.add_row(event.get("summary", "Untitled"), start_str, link)

    console.print(table)


def display_welcome() -> None:
    """Print the application welcome banner."""
    banner = (
        "[bold cyan]AI-Driven Task Orchestrator[/]\n"
        "[dim]Personal Productivity & Event Assistant — powered by Google Gemini[/]\n\n"
        "Type your request in plain English, e.g.:\n"
        "  • [italic]Add a high-priority task to review the quarterly report[/]\n"
        "  • [italic]Schedule a team meeting tomorrow at 3 PM[/]\n"
        "  • [italic]Show my tasks[/]\n"
        "  • [italic]What is machine learning?[/]\n\n"
        "Type [bold]exit[/] or [bold]quit[/] to leave."
    )
    console.print(Panel(banner, title="🤖 Welcome", border_style="cyan", padding=(1, 2)))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: ACTION ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class ActionRouter:
    """
    Dispatches Gemini-parsed intents to the appropriate manager
    (TaskManager or CalendarManager) and formats the response.
    """

    def __init__(self, task_mgr: TaskManager, cal_mgr: CalendarManager | None) -> None:
        self.tasks = task_mgr
        self.calendar = cal_mgr

    def route(self, intent_data: dict) -> None:
        """Inspect `intent_data["intent"]` and call the matching handler."""
        intent = intent_data.get("intent", "GENERAL_QUERY")
        handler = getattr(self, f"_handle_{intent.lower()}", self._handle_unknown)
        handler(intent_data)

    # ── Intent handlers ───────────────────────────────────────────────────────

    def _handle_add_task(self, data: dict) -> None:
        task = self.tasks.add(data.get("task", "Unnamed task"), data.get("priority", "medium"))
        console.print(
            f"[green]✔ Task added:[/] [bold]{task['title']}[/] "
            f"(Priority: {task['priority']})"
        )

    def _handle_list_tasks(self, _: dict) -> None:
        display_tasks(self.tasks.list_all())

    def _handle_complete_task(self, data: dict) -> None:
        task = self.tasks.complete(data.get("task", ""))
        if task:
            console.print(f"[green]✔ Marked complete:[/] [bold]{task['title']}[/]")
        else:
            console.print("[yellow]⚠ No matching pending task found.[/]")

    def _handle_delete_task(self, data: dict) -> None:
        task = self.tasks.delete(data.get("task", ""))
        if task:
            console.print(f"[green]✔ Deleted task:[/] [bold]{task['title']}[/]")
        else:
            console.print("[yellow]⚠ No matching task found to delete.[/]")

    def _handle_add_event(self, data: dict) -> None:
        if not self.calendar:
            console.print(
                "[yellow]⚠ Google Calendar is not connected.[/] "
                "Remove --no-calendar and set up credentials to enable this."
            )
            return

        event = self.calendar.add_event(
            title=data.get("title", "New Event"),
            start_dt=data.get("datetime", datetime.datetime.now().isoformat()),
            duration_minutes=data.get("duration_minutes", 60),
            description=data.get("description", ""),
        )
        if event:
            console.print(
                f"[green]✔ Event created:[/] [bold]{event.get('summary')}[/]\n"
                f"   [dim]{event.get('htmlLink', '')}[/]"
            )
        else:
            console.print("[red]✘ Failed to create event.[/]")

    def _handle_list_events(self, _: dict) -> None:
        if not self.calendar:
            console.print(
                "[yellow]⚠ Google Calendar is not connected.[/] "
                "Remove --no-calendar to enable."
            )
            return
        events = self.calendar.list_events()
        display_events(events)

    def _handle_general_query(self, data: dict) -> None:
        response = data.get("response", "I'm not sure how to help with that.")
        console.print(Panel(response, title="🤖 Gemini", border_style="blue", padding=(0, 1)))

    def _handle_unknown(self, data: dict) -> None:
        console.print(f"[yellow]Unknown intent:[/] {data.get('intent')}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-Driven Personal Productivity & Event Assistant"
    )
    parser.add_argument(
        "--no-calendar",
        action="store_true",
        help="Disable Google Calendar integration (task-only mode).",
    )
    return parser.parse_args()


def main() -> None:
    """Main application loop."""
    args = parse_args()

    display_welcome()

    # Initialise components
    console.print("\n[dim]Initialising Gemini client…[/]")
    gemini = GeminiClient()

    console.print("[dim]Loading tasks…[/]")
    task_mgr = TaskManager()

    cal_mgr = None
    if not args.no_calendar:
        console.print("[dim]Connecting to Google Calendar…[/]")
        cal_mgr = CalendarManager()
    else:
        console.print("[yellow]Calendar integration disabled (--no-calendar).[/]")

    router = ActionRouter(task_mgr, cal_mgr)

    console.print("\n[bold green]Ready![/] Type your request below.\n")

    # ── Conversation loop ─────────────────────────────────────────────────────
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/]").strip()
        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C / Ctrl+D gracefully
            console.print("\n[dim]Goodbye! 👋[/]")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "bye"}:
            console.print("[dim]Goodbye! 👋[/]")
            break

        # Let Gemini understand the intent
        with console.status("[dim]Thinking…[/]", spinner="dots"):
            intent_data = gemini.parse_intent(user_input)

        # Route the intent to the right action
        router.route(intent_data)
        console.print()  # Visual spacing between turns


if __name__ == "__main__":
    main()
