# Samantha AI Personal Assistant

[![CI](https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/actions/workflows/ci.yml/badge.svg)](https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/actions/workflows/ci.yml)
[![Privacy Guard](https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/actions/workflows/privacy-guard.yml/badge.svg)](https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/actions/workflows/privacy-guard.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Samantha is a local-first personal AI assistant for macOS, Windows, and Linux.
It combines local or explicitly configured cloud models with tools, persistent
memory, scheduled operators, research, Office/media workflows, and a local API.
On macOS, the optional owner-verified voice listener supports “Hi Samantha,”
system speech, interruption, and approved application control.

## Platform support

| Capability | macOS | Windows | Linux / WSL2 |
|---|---:|---:|---:|
| CLI, local API, tools and automations | Yes | Yes | Yes |
| Local Ollama models | Yes | Yes | Yes |
| Native desktop application | Yes | Yes | Planned |
| Always-on owner-verified voice listener | Yes | In development | In development |
| Native application control | Yes | Partial | Partial |

Windows and Linux users can use chat, models, tools, the API, memory, and
automations today. Do not assume macOS-only voice or application-control
features are available on another platform.

## Install

Review an installer before piping it into a shell when possible.

macOS, Linux, or Ubuntu under WSL2:

```bash
curl -fsSL https://raw.githubusercontent.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/main/scripts/install/install.sh | bash
```

Native Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/main/deploy/windows/install.ps1 | iex
```

Then verify the installation:

```bash
samantha doctor
samantha --version
samantha chat
```

Detailed instructions and troubleshooting are in the
[installation guide](docs/getting-started/install.md).

## Privacy and security

- Local Ollama inference is the default; cloud providers are opt-in.
- Telemetry, analytics, and traces are disabled by default.
- Credentials, voiceprints, memories, databases, logs, and runtime state stay
  under the user's local Samantha data directory and are excluded from Git.
- Sensitive actions require confirmation.
- Activity diagnostics store minimized command identifiers, not transcripts.
- Network tools disclose only information intentionally sent to the selected
  external service.

Read [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md) before enabling
network or cloud features.

## Use Samantha

```bash
samantha
samantha chat
samantha ask "List my priorities"
samantha start
samantha status
samantha doctor
```

On a configured macOS voice installation, say:

> Hi Samantha

See [SAMANTHA_COMMANDS.md](SAMANTHA_COMMANDS.md) for the complete command and
voice reference.

## Main capabilities

- Local and configurable cloud inference engines
- Memory, priorities, profiles, daily briefings, and calendar tools
- Web research, knowledge curation, and HTTP/API requests
- Persistent operators, scheduled automations, and long-running tasks
- Documents, spreadsheets, presentations, posters, scripts, and media workflows
- Extensible tools, skills, channels, Python SDK, and local API
- Owner verification, interruption, and system speech on supported macOS setups

## Development

```bash
uv sync --extra desktop --extra office --extra dev --group dev --group desktop-native
uv run samantha --help
uv run ruff check src tests
uv run pytest -q -m "not slow"
```

Runtime data belongs outside the repository, under `~/.samantha` by default.
Never commit credentials, memory databases, voiceprints, recordings, or logs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security reports should follow [SECURITY.md](SECURITY.md).

## License

Apache License 2.0.
