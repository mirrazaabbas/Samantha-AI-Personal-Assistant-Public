# Samantha AI Personal Assistant

Samantha is a local-first, voice-first personal AI assistant for macOS. She wakes when the enrolled owner says **“Hi Samantha”**, understands natural speech, executes approved tasks, runs persistent automations, searches the internet when requested, manages memory and priorities, creates Office and media content, and speaks using the selected macOS system voice.

Repository: [Samantha-AI-Personal-Assistant](https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public)

## Privacy and security

- Local model inference is the default.
- Owner-only voice verification rejects other speakers.
- Telemetry, analytics, and traces are disabled by default.
- Sensitive actions require explicit owner confirmation.
- Activity logs store anonymous command identifiers instead of transcripts.
- Credentials, voiceprints, memory, databases, logs, and runtime state are excluded from Git.
- This public repository contains source code only. Each user's private runtime
  data remains under `~/.samantha` on their own device and is ignored by Git.
- Internet features disclose only the queries or data intentionally sent to the selected external service.

## Start Samantha

The login service starts Samantha automatically. No Terminal command is needed for normal voice use:

> Hi Samantha

For direct command-line use:

```bash
samantha
samantha chat
samantha ask "List my priorities"
samantha start
samantha status
samantha doctor
```

See [SAMANTHA_COMMANDS.md](SAMANTHA_COMMANDS.md) for the full command and voice reference.
Read [PRIVACY.md](PRIVACY.md) before enabling cloud engines or network tools.

## Main capabilities

- Continuous wake phrase and owner verification
- Speech interruption with “Samantha, stop”
- Local memory, priorities, profile, and daily briefing
- Calendar, web research, and knowledge curation
- Persistent agents, operators, scheduled tasks, and long-running projects
- Word documents, spreadsheets, presentations, posters, scripts, and video workflows
- Approved macOS application control
- Startup health checks, retries, recovery, private diagnostics, and safe timeouts
- Python SDK, local API server, extensible tools, skills, channels, and workflows

## Development

```bash
uv sync --extra desktop --extra office --extra dev --group dev --group desktop-native
uv run samantha --help
uv run ruff check src tests
uv run pytest -q -m "not slow"
```

The Python package is `samantha`, the native extension is `samantha_rust`, the environment prefix is `SAMANTHA_`, and private runtime data is stored under `~/.samantha`.

## License

Apache License 2.0. Historical authorship remains available in Git history.
