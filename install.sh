#!/bin/bash
# Install the reimagined Ollama Shell (oshell) into a local .venv using uv.
#
# Usage:
#   ./install.sh            # core + TUI
#   ./install.sh all        # everything (web, rag, docs, vision, finetune)
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required: https://docs.astral.sh/uv/  (curl -LsSf https://astral.sh/uv/install.sh | sh)"
    exit 1
fi

EXTRAS="${1:-tui}"
echo "Creating .venv and installing oshell with extras: [$EXTRAS]"
uv venv .venv
uv pip install --python .venv -e ".[$EXTRAS]"

echo
echo "Done. Start it with:  ./'Start Ollama Shell.sh'   (or:  .venv/bin/oshell)"
