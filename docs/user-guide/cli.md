# CLI Reference

Samantha provides a command-line interface through the `samantha` command. Built on [Click](https://click.palletsprojects.com/), it offers subcommands for querying models, managing memory, running benchmarks, and serving an OpenAI-compatible API.

## Global Options

```bash
samantha --version   # Print the Samantha version
samantha --help      # Show top-level help with all subcommands
```

## `samantha init`

Detect local hardware (CPU, GPU, RAM) and generate a configuration file at `~/.samantha/config.toml`.

```bash
samantha init           # Interactive — refuses to overwrite existing config
samantha init --force   # Overwrite existing config without prompting
```

| Option    | Description                                   |
|-----------|-----------------------------------------------|
| `--force` | Overwrite existing configuration without prompting |

The `init` command auto-detects:

- **Platform** (Linux, macOS, Windows)
- **CPU** brand and core count
- **RAM** in GB
- **GPU** vendor, model, VRAM, and count (via `nvidia-smi`, `rocm-smi`, or `system_profiler`)

Based on the detected hardware, it recommends an appropriate inference engine and writes a pre-configured TOML file.

**Example output:**

```
Detecting hardware...
  Platform : linux
  CPU      : AMD Ryzen 9 7950X (32 cores)
  RAM      : 64 GB
  GPU      : NVIDIA RTX 4090 (24.0 GB VRAM, x1)

Config written successfully.
```

---

## `samantha ask`

Send a query to the inference engine (directly or through an agent) and print the response.

```bash
samantha ask "What is the capital of France?"
```

### Options

| Option                        | Type    | Default    | Description                                           |
|-------------------------------|---------|------------|-------------------------------------------------------|
| `-m`, `--model MODEL`         | string  | auto       | Model to use for inference                             |
| `-e`, `--engine ENGINE`       | string  | auto       | Engine backend (ollama, vllm, llamacpp, etc.)          |
| `-t`, `--temperature TEMP`    | float   | `0.7`      | Sampling temperature                                   |
| `--max-tokens N`              | int     | `1024`     | Maximum tokens to generate                             |
| `--json`                      | flag    | off        | Output raw JSON result instead of plain text           |
| `--no-stream`                 | flag    | off        | Disable streaming (synchronous mode)                   |
| `--no-context`                | flag    | off        | Disable memory context injection                       |
| `-a`, `--agent AGENT`         | string  | none       | Agent to use (`simple`, `orchestrator`)                |
| `--tools TOOLS`               | string  | none       | Comma-separated tool names to enable                   |
| `-i`, `--image PATH`          | path    | none       | Image file for a vision model (e.g. `gemma3:4b`); repeatable |
| `-S`, `--screen`              | flag    | off        | Capture the current screen and send it to the vision model  |

### Direct Mode vs Agent Mode

**Direct mode** (default) sends the query straight to the inference engine:

```bash
samantha ask "Explain quantum computing"
```

**Agent mode** routes the query through an agent that can use tools and manage multi-turn interactions:

```bash
samantha ask --agent orchestrator "What is 2+2?"
samantha ask --agent orchestrator --tools calculator,think "Calculate sqrt(144) + 3^2"
samantha ask --agent simple "Hello"
```

### Usage Examples

```bash
# Basic query
samantha ask "What is machine learning?"

# Specify a model
samantha ask -m qwen3:8b "Summarize this concept"

# Use the orchestrator agent with tools
samantha ask --agent orchestrator --tools calculator "What is 15% of 340?"

# Get JSON output
samantha ask --json "Hello"

# Disable memory context injection
samantha ask --no-context "Tell me about Python"

# Set maximum token generation
samantha ask --max-tokens 2048 "Write a detailed essay about AI"
```

### Vision Input

Vision-capable models (such as `gemma3:4b`) can read images alongside your
text prompt. Attach one or more image files with `-i`/`--image`, or capture
the current screen with `-S`/`--screen`:

```bash
# Ask about a local image
samantha ask -i screenshot.png "What is shown in this image?"

# Send multiple images (the flag is repeatable)
samantha ask -i chart-a.png -i chart-b.png "Compare these two charts"

# Capture the current screen and ask about it
samantha ask --screen "Summarize what's on my screen"
```

Vision runs in **direct mode** only. If you also pass `--agent`, the image is
ignored and a note is printed — re-run with `--agent ""` to force direct mode.

The Ollama context window can be tuned for large images or long prompts with
the `SAMANTHA_NUM_CTX` environment variable (default `16384`):

```bash
SAMANTHA_NUM_CTX=8192 samantha ask --screen "What's on my screen?"
```

!!! note "Keep vision on-device"
    Images are sensitive. Samantha prints a privacy warning before sending
    an image to a non-local engine, so a screenshot never leaves your machine
    unnoticed. Use a local engine (e.g. `ollama` with `gemma3:4b`) to keep
    vision fully local.

### JSON Output Format

When using `--json` in **direct mode**, the output includes:

```json
{
  "content": "The response text...",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 85,
    "total_tokens": 97
  }
}
```

When using `--json` in **agent mode**, the output includes:

```json
{
  "content": "The response text...",
  "turns": 3,
  "tool_results": [
    {
      "tool_name": "calculator",
      "content": "51.0",
      "success": true
    }
  ]
}
```

---

## `samantha model`

Manage and inspect language models available on running engines.

### `samantha model list`

List all models available from running inference engines, displayed as a Rich table with model parameters, context length, and VRAM requirements.

```bash
samantha model list
```

**Example output:**

```
           Available Models
┌─────────┬────────────────┬────────┬─────────┬──────┐
│ Engine  │ Model          │ Params │ Context │ VRAM │
├─────────┼────────────────┼────────┼─────────┼──────┤
│ ollama  │ qwen3:8b       │ 8B     │ 32,768  │ 6GB  │
│ ollama  │ llama3.2:3b    │ 3B     │ 8,192   │ 3GB  │
└─────────┴────────────────┴────────┴─────────┴──────┘
```

### `samantha model info <model>`

Show detailed information about a specific model.

```bash
samantha model info qwen3:8b
```

**Example output:**

```
┌─ Qwen 3 8B ──────────────────────────────┐
│ Model ID:     qwen3:8b                    │
│ Name:         Qwen 3 8B                   │
│ Parameters:   8B                          │
│ Context:      32,768                      │
│ Quantization: none                        │
│ Min VRAM:     6GB                         │
│ Engines:      ollama, vllm                │
│ Provider:     Alibaba                     │
│ API Key:      not required                │
└───────────────────────────────────────────┘
```

### `samantha model pull <model>`

Download a model via Ollama. Shows a progress bar during download.

```bash
samantha model pull qwen3:8b
```

!!! note
    The `pull` command requires a running Ollama instance. It connects to the Ollama API at the host configured in your `config.toml`.

---

## `samantha pearl`

Access Pearl's native node, wallet, and RPC tools from the Samantha CLI.

```bash
samantha pearl doctor
samantha pearl node -- <pearld args>
samantha pearl wallet -- <oyster args>
samantha pearl ctl -- <prlctl args>
samantha pearl address
```

All Pearl wrapper commands use the `samantha pearl <command>` shape. The
pass-through commands map to Pearl's native binaries:

| Samantha command | Pearl binary | Use |
|--------------------|--------------|-----|
| `samantha pearl doctor` | n/a | Check whether `pearld`, `oyster`, and `prlctl` are discoverable |
| `samantha pearl node` | `pearld` | Run the Pearl full node |
| `samantha pearl wallet` | `oyster` | Run the Oyster wallet daemon |
| `samantha pearl ctl` | `prlctl` | Query Pearl node or wallet RPC |
| `samantha pearl address` | `prlctl --wallet getnewaddress` | Generate a wallet address from Oyster |

Use `PEARL_HOME=/path/to/pearl` or `--pearl-home /path/to/pearl` if Pearl's
`bin/` directory is not on `PATH`. See the [Pearl CLI guide](pearl.md) for
examples.

---

## `samantha memory`

Manage the document memory store for retrieval-augmented generation.

### `samantha memory index <path>`

Index documents from a file or directory into the memory store.

```bash
samantha memory index ./docs/
samantha memory index ./notes.md
samantha memory index ./data/ --chunk-size 256 --chunk-overlap 32
samantha memory index ./docs/ --backend sqlite
```

| Option                      | Type   | Default | Description                          |
|-----------------------------|--------|---------|--------------------------------------|
| `--backend`, `-b`           | string | config  | Override the default memory backend  |
| `--chunk-size`              | int    | `512`   | Chunk size in tokens                 |
| `--chunk-overlap`           | int    | `64`    | Overlap between chunks in tokens     |

The ingestion pipeline supports text, markdown, code files, and PDF (with `pdfplumber` installed). Binary files and hidden directories are automatically skipped.

### `samantha memory search <query>`

Search the memory store for relevant document chunks.

```bash
samantha memory search "machine learning basics"
samantha memory search -k 10 "neural networks"
samantha memory search --backend faiss "embeddings"
```

| Option             | Type   | Default | Description                          |
|--------------------|--------|---------|--------------------------------------|
| `--top-k`, `-k`    | int    | `5`     | Number of results to return          |
| `--backend`, `-b`  | string | config  | Override the default memory backend  |

Results are displayed in a table with rank, score, source file, and a content preview.

### `samantha memory stats`

Show memory store statistics including document count and database size.

```bash
samantha memory stats
samantha memory stats --backend sqlite
```

| Option             | Type   | Default | Description                          |
|--------------------|--------|---------|--------------------------------------|
| `--backend`, `-b`  | string | config  | Override the default memory backend  |

---

## `samantha telemetry`

Query and manage inference telemetry data stored in SQLite.

### `samantha telemetry stats`

Show aggregated telemetry statistics including total calls, tokens, cost, and latency, broken down by model and engine.

```bash
samantha telemetry stats
samantha telemetry stats -n 5    # Show top 5 models
```

| Option          | Type | Default | Description                   |
|-----------------|------|---------|-------------------------------|
| `-n`, `--top`   | int  | `10`    | Number of top models to show  |

### `samantha telemetry export`

Export raw telemetry records in JSON or CSV format.

```bash
samantha telemetry export                          # JSON to stdout
samantha telemetry export --format csv             # CSV to stdout
samantha telemetry export --format json -o data.json  # JSON to file
samantha telemetry export -f csv -o metrics.csv    # CSV to file
```

| Option                | Type   | Default  | Description                     |
|-----------------------|--------|----------|---------------------------------|
| `-f`, `--format`      | choice | `json`   | Output format: `json` or `csv`  |
| `-o`, `--output`      | path   | stdout   | Output file path                |

### `samantha telemetry clear`

Delete all telemetry records from the database.

```bash
samantha telemetry clear         # Interactive confirmation
samantha telemetry clear --yes   # Skip confirmation
```

| Option         | Type | Default | Description                   |
|----------------|------|---------|-------------------------------|
| `-y`, `--yes`  | flag | off     | Skip confirmation prompt      |

!!! warning
    This permanently deletes all stored telemetry data. Use `--yes` to skip the confirmation prompt in automated scripts.

---

## `samantha bench`

Run inference benchmarks against a running engine.

### `samantha bench run`

Execute benchmarks and report results.

```bash
samantha bench run                               # Run all benchmarks, 10 samples
samantha bench run -n 20                         # 20 samples per benchmark
samantha bench run -b latency                    # Only the latency benchmark
samantha bench run -b throughput -n 50 --json    # Throughput, 50 samples, JSON output
samantha bench run -o results.jsonl              # Write JSONL results to file
samantha bench run -m qwen3:8b -e ollama         # Specific model and engine
```

| Option                     | Type   | Default | Description                              |
|----------------------------|--------|---------|------------------------------------------|
| `-m`, `--model MODEL`      | string | auto    | Model to benchmark                       |
| `-e`, `--engine ENGINE`    | string | auto    | Engine backend                           |
| `-n`, `--samples N`        | int    | `10`    | Number of samples per benchmark          |
| `-b`, `--benchmark NAME`   | string | all     | Specific benchmark to run                |
| `-o`, `--output PATH`      | path   | none    | Write JSONL results to file              |
| `--json`                   | flag   | off     | Output JSON summary to stdout            |

Available benchmarks:

- **latency** -- Measures per-call inference latency (mean, p50, p95, min, max)
- **throughput** -- Measures tokens-per-second throughput

---

## `samantha channel`

Manage messaging channels for multi-platform communication. Channels connect directly to platform APIs (Telegram, Discord, Slack, etc.) -- no gateway required.

### `samantha channel list`

List registered channel backends and their connection status.

```bash
samantha channel list
```

### `samantha channel send`

Send a message to a specific channel.

```bash
samantha channel send slack "Hello from Samantha!"
samantha channel send discord "Build complete"
```

| Argument    | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `TARGET`    | string | Channel name to send to              |
| `MESSAGE`   | string | Message content                      |

### `samantha channel status`

Show connection status for configured channels.

```bash
samantha channel status
```

!!! note "Channel Dependencies"
    Each channel requires its platform-specific credentials (bot tokens, API keys) configured in the `[channel.<platform>]` section of your config. See [Configuration](../getting-started/configuration.md) for details.

---

## `samantha serve`

Start an OpenAI-compatible API server.

```bash
samantha serve                                 # Default host/port from config
samantha serve --port 8000                     # Custom port
samantha serve --host 0.0.0.0 --port 9000      # Bind to all interfaces
samantha serve --model qwen3:8b                # Specify default model
samantha serve --agent orchestrator            # Route requests through an agent
```

| Option                   | Type   | Default | Description                              |
|--------------------------|--------|---------|------------------------------------------|
| `--host HOST`            | string | config  | Bind address                             |
| `--port PORT`            | int    | config  | Port number                              |
| `-e`, `--engine ENGINE`  | string | auto    | Engine backend                           |
| `-m`, `--model MODEL`    | string | config  | Default model for inference              |
| `-a`, `--agent AGENT`    | string | none    | Agent for non-streaming requests         |

!!! note "Server Dependencies"
    The `serve` command requires the server extra:

    ```bash
    uv sync --extra server
    ```

    This installs FastAPI, uvicorn, and related dependencies.

### API Endpoints

The server exposes the following OpenAI-compatible endpoints:

| Method | Path                     | Description                    |
|--------|--------------------------|--------------------------------|
| POST   | `/v1/chat/completions`   | Chat completions (streaming & non-streaming) |
| GET    | `/v1/models`             | List available models          |
| GET    | `/health`                | Health check                   |
| GET    | `/v1/channels`           | List available messaging channels    |
| POST   | `/v1/channels/send`      | Send a message to a channel          |
| GET    | `/v1/channels/status`    | Channel bridge connection status     |

**Example with curl:**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

When an agent is configured (e.g., `--agent orchestrator`), non-streaming requests are routed through the agent with access to all registered tools. For tool-capable agents (`orchestrator`, `react`, `openhands`), all registered tools are automatically loaded and made available.

---

## LLM-guided spec search (no CLI yet)

LLM-guided spec search (the frontier-driven harness-learning subsystem)
is exposed as a Python library only — there is currently no top-level
`samantha` subcommand for it. Construct a `SpecSearchOrchestrator`
directly from `samantha.learning.spec_search.orchestrator` and call
`.run(trigger)` with a trigger from
`samantha.learning.spec_search.triggers`. See
[`docs/user-guide/llm-guided-spec-search.md`](llm-guided-spec-search.md)
for the architecture and the building blocks
(`splits.py`, external corpora, `external_adapter`).
