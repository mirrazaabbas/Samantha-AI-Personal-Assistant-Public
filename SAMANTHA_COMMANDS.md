# Samantha command reference

Use `samantha --help` for live help and `samantha COMMAND --help` for every option supported by a command.

## Main commands

| Command | Purpose |
|---|---|
| `samantha` | Start Samantha's interactive assistant |
| `samantha ask "REQUEST"` | Execute one request |
| `samantha chat` | Start a multi-turn chat session |
| `samantha start` / `stop` / `restart` / `status` | Control the background server |
| `samantha serve` | Run the API server in the foreground |
| `samantha doctor` / `quickstart` / `init` | Diagnose or configure Samantha |
| `samantha config` | Inspect or update configuration |
| `samantha scan` / `auth` / `vault` | Security, authentication, and secrets |
| `samantha model` / `host` / `bench` / `eval` | Models and evaluation |
| `samantha agents` / `operators` / `scheduler` | Agents and automations |
| `samantha workflow` / `tool` / `registry` / `skill` | Capabilities and workflows |
| `samantha memory` | Manage Samantha's memory |
| `samantha research` / `deep-research-setup` | Research and local data |
| `samantha digest` | Display and play the morning briefing |
| `samantha connect` / `add` | Data sources and MCP servers |
| `samantha channel` / `channels` / `gateway` | Messaging integrations |
| `samantha tunnel` | Manage Cloudflare tunnels |
| `samantha compose` / `optimize` | Compose and optimize configurations |
| `samantha telemetry` / `feedback` | Telemetry and trace feedback |
| `samantha mine` / `pearl` | Pearl mining and node tools |
| `samantha self-update` | Update the underlying framework |

## Voice commands

Wake Samantha with **“Hi Samantha”**, then speak naturally. Examples:

- “Open Excel”, “Open Chrome”, “Open Safari”, “Open Notes”, or “Open Calendar”.
- “List my priorities.”
- “Remember finish the proposal as a priority.”
- “Complete priority finish the proposal.”
- “Search the internet for the latest information about …”
- “Run my daily briefing.”
- “Show my upcoming calendar events.”
- “Create a Word document about …”
- “Create an Excel dashboard from …”
- “Create a presentation about …”
- “Design a poster for …”
- “Write a video script about …”
- “Create a storyboard for …”
- “Edit these video clips into …”
- “Start a long-running task to …”
- “Show the status of my automations.”
- “Samantha, stop.”

Sensitive actions—including deleting, sending, publishing, purchasing, paying, installing software, changing passwords, and system-control operations—require explicit owner-voice confirmation.

## Detailed help

```bash
samantha --help
samantha COMMAND --help
```

The installed `samantha` command and repository-local `.venv/bin/samantha`
command provide the same interface.
