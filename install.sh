#!/usr/bin/env bash
# Install Ollama Shell (oshell) and put it on your PATH (macOS / Linux).
#
# Usage:
#   ./install.sh                    # core + tui + machine memory (the default)
#   ./install.sh all                # everything: tui, rag, docs, vision, finetune
#   ./install.sh rag                # a custom subset of extras (web search is built in)
#   ./install.sh tui --no-monitors  # skip the Mechanic + Drift machine-memory pair
#
# By default this also installs Mechanic (github.com/sunkencity999/mechanic —
# "is this normal for this box?") and Drift (github.com/sunkencity999/drift —
# "what changed on this box?"): local-first, user-level daemons that give the
# shell memory of the machine it lives on. oshell mounts them over MCP
# automatically; skip with --no-monitors (oshell works fine without them).
#
# Prefers `uv tool install` (manages a PATH-linked bin dir, editable from this
# repo). Falls back to a local .venv + a symlink into ~/.local/bin.
set -euo pipefail
cd "$(dirname "$0")"

EXTRAS="tui"
INSTALL_MONITORS=1
for arg in "$@"; do
    case "$arg" in
        --no-monitors) INSTALL_MONITORS=0 ;;
        *) EXTRAS="$arg" ;;
    esac
done
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

# ── machine memory: Mechanic (baselines) + Drift (state diffs) ────────────────
# Each is a fully standalone project with its own installer (venv + user-level
# daemon under launchd/systemd). oshell discovers them over MCP at startup and
# degrades gracefully if they're absent — so a failure here is never fatal.
install_monitor() {
    local name="$1" repo="$2" blurb="$3"
    local share="${XDG_DATA_HOME:-$HOME/.local/share}"
    if [ -x "${share}/${name}/.venv/bin/${name}" ]; then
        echo "==> ${name} already installed (${share}/${name})"
        return 0
    fi
    if ! command -v git >/dev/null 2>&1; then
        echo "NOTE: git not found — skipping ${name} (${blurb})."
        echo "      Install later: git clone ${repo} && cd ${name} && bash scripts/install.sh"
        return 0
    fi
    echo "==> Installing ${name} — ${blurb}"
    local src rc=0
    src="$(mktemp -d)"
    if git clone --quiet --depth 1 "${repo}" "${src}/${name}" \
        && (cd "${src}/${name}" && bash scripts/install.sh); then
        echo "==> ${name} installed."
    else
        rc=1
        echo "NOTE: ${name} install failed — oshell works without it."
        echo "      Install later: git clone ${repo} && cd ${name} && bash scripts/install.sh"
    fi
    rm -rf "${src}"
    return 0
}

if [ "${INSTALL_MONITORS}" -eq 1 ]; then
    echo
    echo "==> Machine memory (skip with --no-monitors)"
    install_monitor mechanic "https://github.com/sunkencity999/mechanic" \
        "so the shell knows what's NORMAL for this box"
    install_monitor drift "https://github.com/sunkencity999/drift" \
        "so the shell knows what CHANGED on this box"
else
    echo "==> Skipping Mechanic + Drift (--no-monitors)"
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
      oshell config          # resolved config + capabilities

==> With Mechanic + Drift installed, ask it things only YOUR box can answer:
      "is my CPU usage normal right now?"
      "what changed on this machine since yesterday?"
EOF
