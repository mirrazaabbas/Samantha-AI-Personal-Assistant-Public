"""Startup banner — Samantha wordmark + tagline."""

from __future__ import annotations

_WORDMARK = (
    " ____                                  _   _           ",
    "/ ___|  __ _ _ __ ___   __ _ _ __   | |_| |__   __ _ ",
    "\\___ \\ / _` | '_ ` _ \\ / _` | '_ \\  | __| '_ \\ / _` |",
    " ___) | (_| | | | | | | (_| | | | | | |_| | | | (_| |",
    "|____/ \\__,_|_| |_| |_|\\__,_|_| |_|  \\__|_| |_|\\__,_|",
)

_TAGLINE = "Private voice-first personal AI"


def print_banner(quiet: bool = False) -> None:
    """Print the Samantha startup banner. No-op when quiet."""
    if quiet:
        return
    try:
        from rich.console import Console

        console = Console()
        for line in _WORDMARK:
            console.print(line, style="bold bright_blue", highlight=False, markup=False)
        console.print(f"      {_TAGLINE}", style="cyan", highlight=False, markup=False)
        console.print()
    except ImportError:
        for line in _WORDMARK:
            print(line)
        print(f"      {_TAGLINE}")
        print()
