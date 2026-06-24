#!/usr/bin/env bash
# Install Ollama Shell (oshell) and put it on your PATH (macOS / Linux).
#
# Usage:
#   ./install.sh              # core + tui (interactive default)
#   ./install.sh all          # everything: tui, rag, docs, vision, finetune
#   ./install.sh rag          # a custom subset of extras (web search is built in)
#
# Prefers `uv tool install` (manages a PATH-linked bin dir, editable from this
# repo). Falls back to a local .venv + a symlink into ~/.local/bin.
set -euo pipefail
cd "$(dirname "$0")"

EXTRAS="${1:-tui}"
SPEC=".[${EXTRAS}]"
echo "==> Installing oshell with extras: [${EXTRAS}]"

if command -v uv >/dev/null 2>&1; then
    echo "==> Using uv tool install (editable)"
    uv tool install --editable "${SPEC}" --force
    # Ensure uv's tool bin dir is on PATH in future shells (best-effort).
    uv tool update-shell 2>/dev/null || true
    BIN="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
else
    echo "==> uv not found; falling back to python3 venv + pip + symlink"
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: need uv or python3." >&2; exit 1; }
    python3 -m venv .venv
    ./.venv/bin/python -m pip install --upgrade pip >/dev/null
    ./.venv/bin/python -m pip install -e "${SPEC}"
    BIN="$HOME/.local/bin"
    mkdir -p "$BIN"
    ln -sf "$(pwd)/.venv/bin/oshell" "$BIN/oshell"
fi

# Is the bin dir actually on PATH right now?
case ":$PATH:" in
    *":$BIN:"*) ON_PATH=1 ;;
    *) ON_PATH=0 ;;
esac

# Friendly heads-up if the Ollama backend isn't reachable (not fatal).
HOST="${OLLAMA_HOST:-http://localhost:11434}"
if command -v curl >/dev/null 2>&1 && ! curl -fsS --max-time 2 "${HOST}/api/tags" >/dev/null 2>&1; then
    echo
    echo "NOTE: Ollama doesn't appear to be running at ${HOST}."
    echo "      Install it from https://ollama.com and run 'ollama serve'."
fi

echo
echo "==> Installed 'oshell' to ${BIN}"
if [ "${ON_PATH}" -eq 0 ]; then
    echo "    ${BIN} is not on your PATH yet. Add this to your shell profile:"
    echo "        export PATH=\"${BIN}:\$PATH\""
    echo "    then open a new terminal."
fi
cat <<'EOF'

==> Try it (open a new terminal if PATH was just updated):
      oshell                 # interactive agent chat
      oshell tui             # Textual workspace
      oshell finetune detect
      oshell config          # resolved config + capabilities
EOF
