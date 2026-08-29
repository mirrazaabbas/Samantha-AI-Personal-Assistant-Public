#!/usr/bin/env bash
# samantha-uninstall.sh — clean removal of Samantha from $HOME.
#
# Removes:
#   ~/.samantha/
#   ~/.local/bin/samantha
#   ~/.local/bin/samantha-uninstall
#
# Does NOT remove: ollama, uv, or the Rust toolchain.

set -euo pipefail

SAMANTHA_HOME="${SAMANTHA_HOME:-$HOME/.samantha}"

if [[ -f "$SAMANTHA_HOME/.state/bg.pid" ]]; then
    pid=$(cat "$SAMANTHA_HOME/.state/bg.pid" 2>/dev/null || echo "")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "Stopping background work (pid=$pid)..."
        kill "$pid" 2>/dev/null || true
    fi
fi

if command -v ollama >/dev/null 2>&1; then
    ollama stop >/dev/null 2>&1 || true
fi

if [[ -d "$SAMANTHA_HOME" ]]; then
    rm -rf "$SAMANTHA_HOME"
    echo "Removed $SAMANTHA_HOME"
fi

for f in "$HOME/.local/bin/samantha" "$HOME/.local/bin/samantha-uninstall"; do
    if [[ -L "$f" ]] || [[ -f "$f" ]]; then
        rm -f "$f"
        echo "Removed $f"
    fi
done

cat <<EOF

Samantha removed.

Left intact (may be used by other tools):
  - Ollama       (uninstall: brew uninstall ollama  /  rm -f /usr/local/bin/ollama)
  - uv           (uninstall: rm -rf ~/.local/share/uv ~/.cargo/bin/uv)
  - Rust toolchain (uninstall: rustup self uninstall)
EOF
