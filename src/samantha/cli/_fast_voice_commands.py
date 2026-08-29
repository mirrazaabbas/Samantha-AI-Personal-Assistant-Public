"""Fast, deterministic voice commands for Samantha."""

from __future__ import annotations

import re
from datetime import datetime

from samantha.tools.macos_control import MacOSControlTool
from samantha.tools.user_profile_manage import UserProfileManageTool

_OPEN_APP = re.compile(
    r"^(?:(?:hey|hi|hello)\s+)?(?:samantha[,\s]+)?"
    r"(?:please\s+)?(?:open|launch|start)\s+(.+?)[.!?]?$",
    re.IGNORECASE,
)

_LIST_PRIORITIES = re.compile(
    r"^(?:(?:hey|hi|hello)\s+)?(?:samantha[,\s]+)?(?:please\s+)?"
    r"(?:list|show|read|what are)\s+(?:all\s+)?my\s+priorities[.!?]?$",
    re.IGNORECASE,
)
_ADD_PRIORITY = re.compile(
    r"^(?:(?:hey|hi|hello)\s+)?(?:samantha[,\s]+)?(?:please\s+)?"
    r"(?:(?:add|remember)\s+(.+?)\s+as\s+(?:a\s+)?priority|"
    r"make\s+(.+?)\s+(?:a\s+)?priority)[.!?]?$",
    re.IGNORECASE,
)
_COMPLETE_PRIORITY = re.compile(
    r"^(?:(?:hey|hi|hello)\s+)?(?:samantha[,\s]+)?(?:please\s+)?"
    r"(?:complete|finish|remove)\s+(?:the\s+)?priority\s+(.+?)[.!?]?$",
    re.IGNORECASE,
)
_CURRENT_TIME = re.compile(
    r"(?:(?:can|could) you\s+)?(?:(?:tell|give) me\s+)?(?:the\s+)?"
    r"(?:current\s+)?time|what(?:'s| is)\s+(?:the\s+)?(?:current\s+)?"
    r"time(?:\s+now)?",
    re.IGNORECASE,
)
_CURRENT_DATE = re.compile(
    r"(?:(?:can|could) you\s+)?(?:(?:tell|give) me\s+)?(?:the\s+)?"
    r"(?:current\s+)?date|what(?:'s| is)\s+(?:today'?s|the current)\s+date",
    re.IGNORECASE,
)

_APP_ALIASES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "notes": "Notes",
    "apple notes": "Notes",
    "finder": "Finder",
    "calendar": "Calendar",
    "terminal": "Terminal",
    "settings": "System Settings",
    "system settings": "System Settings",
    "music": "Music",
    "apple music": "Music",
    "messages": "Messages",
    "facetime": "FaceTime",
    "mail": "Mail",
    "preview": "Preview",
    "excel": "Microsoft Excel",
    "extel": "Microsoft Excel",
    "exel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
}


def _format_local_time(now: datetime) -> str:
    """Format a spoken time without platform-specific strftime flags."""
    return f"{now.strftime('%I').lstrip('0') or '0'}:{now.strftime('%M %p')}"


def _format_local_date(now: datetime) -> str:
    """Format a spoken date portably on Windows, macOS, and Linux."""
    return f"{now.strftime('%A, %B')} {now.day}, {now.year}"


def handle_fast_voice_command(text: str) -> str | None:
    """Execute supported low-risk voice commands without calling an LLM."""

    command = text.strip()
    command = re.sub(
        r"^(?:okay|ok|alright|right)[,\s]+",
        "",
        command,
        flags=re.IGNORECASE,
    ).strip()
    # Normalize common Samantha transcriptions only at the start of commands.
    command = re.sub(
        r"^(?:(?:hey|hi|hello)\s+)?(?:samantha|samanta|samanth|sam\s+antha)[,\s]+",
        "",
        command,
        flags=re.IGNORECASE,
    ).strip()
    normalized_command = command.strip(" .!?")
    now = datetime.now().astimezone()
    if _CURRENT_TIME.fullmatch(normalized_command):
        return f"The current time is {_format_local_time(now)}, Sir."
    if _CURRENT_DATE.fullmatch(normalized_command):
        return f"Today is {_format_local_date(now)}, Sir."

    if _LIST_PRIORITIES.fullmatch(command):
        result = UserProfileManageTool().execute(action="read")
        priorities = [
            line.split("Priority:", 1)[1].strip()
            for line in result.content.splitlines()
            if "Priority:" in line
        ]
        if not priorities:
            return "You have no saved priorities, Sir."
        return "Your priorities are: " + "; ".join(priorities) + "."

    add_match = _ADD_PRIORITY.fullmatch(command)
    if add_match:
        priority = next(group for group in add_match.groups() if group).strip()
        result = UserProfileManageTool().execute(
            action="add", entry=f"Priority: {priority}"
        )
        if result.success:
            return f"Priority saved: {priority}, Sir."
        return "I couldn't save that priority, Sir."

    complete_match = _COMPLETE_PRIORITY.fullmatch(command)
    if complete_match:
        priority = complete_match.group(1).strip()
        result = UserProfileManageTool().execute(action="remove", entry=priority)
        if result.success:
            return f"Priority completed: {priority}, Sir."
        return f"I couldn't find the priority {priority}, Sir."

    match = _OPEN_APP.fullmatch(command)
    if not match:
        return None

    spoken_app = match.group(1).strip()

    # Normalize common Whisper variations.
    normalized_app = re.sub(r"[^a-z0-9 ]+", "", spoken_app.lower())

    if normalized_app.startswith("the "):
        normalized_app = normalized_app[4:].strip()

    chrome_variants = {
        "chrome",
        "google chrome",
        "chrome google chrome",
        "google chrome chrome",
        "chrome browser",
        "google chrome browser",
    }

    if normalized_app in chrome_variants:
        app = "Google Chrome"
    else:
        app = _APP_ALIASES.get(normalized_app)

    # Only approved low-risk applications use the instant path.
    if app is None:
        return None

    result = MacOSControlTool().execute(
        action="open_app",
        app=app,
    )

    if result.success:
        return f"Opened {app}, Sir."

    return f"I couldn't open {app}, Sir."


__all__ = ["handle_fast_voice_command"]
