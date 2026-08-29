#!/usr/bin/env bash
# samantha-wrapper.sh — symlinked to ~/.local/bin/samantha.
# Activates the managed venv and execs the real samantha CLI.

SAMANTHA_HOME="${SAMANTHA_HOME:-$HOME/.samantha}"
VENV="$SAMANTHA_HOME/.venv"

if [[ ! -d "$VENV" ]]; then
    echo "samantha: venv not found at $VENV" >&2
    echo "Re-run the installer: curl -fsSL https://github.com/mirrazaabbas/Samantha-AI-Personal-Assistant-Public/install.sh | bash" >&2
    exit 1
fi

exec "$VENV/bin/samantha" "$@"
