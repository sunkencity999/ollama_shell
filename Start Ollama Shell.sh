#!/bin/bash
# Launch the reimagined Ollama Shell (oshell). The v0.1 monolith has been retired;
# this wrapper boots the new CLI from the project's virtualenv.
set -e

cd "$(dirname "$0")"

if [ -x ".venv/bin/oshell" ]; then
    exec ".venv/bin/oshell" "$@"
elif command -v oshell >/dev/null 2>&1; then
    exec oshell "$@"
else
    echo "oshell is not installed. Run ./install.sh (or: uv pip install -e '.[tui]')."
    exit 1
fi
