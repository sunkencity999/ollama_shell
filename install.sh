#!/usr/bin/env bash
# Install Ollama Shell (oshell) into a local .venv.
#
# Usage:
#   ./install.sh              # core + tui (the interactive default)
#   ./install.sh all          # everything: tui, web, rag, docs, vision, finetune
#   ./install.sh web,rag       # a custom subset of extras
#
# Prefers `uv` (fast); falls back to python3 venv + pip.
set -euo pipefail
cd "$(dirname "$0")"

EXTRAS="${1:-tui}"
SPEC=".[${EXTRAS}]"
echo "==> Installing oshell with extras: [${EXTRAS}]"

if command -v uv >/dev/null 2>&1; then
    echo "==> Using uv"
    uv venv .venv
    uv pip install --python .venv -e "${SPEC}"
elif command -v python3 >/dev/null 2>&1; then
    echo "==> uv not found; falling back to python3 venv + pip"
    python3 -m venv .venv
    ./.venv/bin/python -m pip install --upgrade pip >/dev/null
    ./.venv/bin/python -m pip install -e "${SPEC}"
else
    echo "ERROR: need either 'uv' (https://astral.sh/uv) or python3 installed." >&2
    exit 1
fi

# Friendly heads-up if the Ollama backend isn't reachable (not fatal).
HOST="${OLLAMA_HOST:-http://localhost:11434}"
if command -v curl >/dev/null 2>&1 && ! curl -fsS --max-time 2 "${HOST}/api/tags" >/dev/null 2>&1; then
    echo
    echo "NOTE: Ollama doesn't appear to be running at ${HOST}."
    echo "      Install it from https://ollama.com and run 'ollama serve' (or pull a model)."
fi

cat <<'EOF'

==> Done. Try it:
      ./.venv/bin/oshell              # interactive agent chat
      ./.venv/bin/oshell tui          # Textual workspace
      ./.venv/bin/oshell finetune detect
      ./.venv/bin/oshell config       # resolved config + capabilities

    Or use the launcher:  "./Start Ollama Shell.sh"
EOF
