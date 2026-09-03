#!/usr/bin/env bash
# Install Ollama Shell (oshell) and make it part of the machine (macOS / Linux).
#
# Usage:
#   ./install.sh                    # core + tui + machine memory + presence (the default)
#   ./install.sh all                # everything: tui, rag, docs, vision, finetune
#   ./install.sh rag                # a custom subset of extras (web search is built in)
#   ./install.sh tui --no-monitors  # skip the Mechanic + Drift machine-memory pair
#   ./install.sh --no-shell         # don't touch your shell rc (no Ctrl+G / `oshell fix`)
#   ./install.sh --no-jobs          # don't register the once-a-minute job tick with the OS
#   ./install.sh --no-orders        # don't create the standing-orders job
#   ./install.sh --no-setup         # don't run the first-run model wizard at the end
#   ./install.sh --dry-run          # print what would happen, change nothing
#
# What "installed" means for a shell that is meant to be the first layer of
# your OS — every step is idempotent and individually skippable:
#
#   1. the `oshell` command (uv tool install, or a .venv + ~/.local/bin symlink)
#   2. machine memory: Mechanic ("is this normal for this box?") and Drift
#      ("what changed on this box?"), local-first daemons oshell mounts over MCP
#   3. shell integration for your $SHELL (zsh/bash/fish): Ctrl+G, '#…'→command,
#      last-command capture for `oshell fix`, command-not-found nudge
#   4. the theme's terminal exports in ~/.oshell/current/ (Ghostty, Alacritty,
#      Kitty, WezTerm, btop) so your terminal can follow `oshell theme set`
#   5. presence: `oshell jobs tick` registered with launchd / systemd --user
#      (runs due jobs once a minute, exits otherwise) and the standing-orders
#      job with an editable ~/.oshell/orders.md (nothing sensitive runs
#      unattended — proposals wait in the inbox)
#   6. `oshell setup`, the interactive first-run wizard (models sized to this box)
set -euo pipefail
cd "$(dirname "$0")"

EXTRAS="tui"
INSTALL_MONITORS=1
INSTALL_SHELL=1
INSTALL_JOBS=1
INSTALL_ORDERS=1
RUN_SETUP=1
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --no-monitors) INSTALL_MONITORS=0 ;;
        --no-shell) INSTALL_SHELL=0 ;;
        --no-jobs) INSTALL_JOBS=0 ;;
        --no-orders) INSTALL_ORDERS=0 ;;
        --no-setup) RUN_SETUP=0 ;;
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        --*) echo "unknown flag: $arg" >&2; exit 2 ;;
        *) EXTRAS="$arg" ;;
    esac
done
SPEC=".[${EXTRAS}]"

run() {  # run or, in --dry-run, just print
    if [ "${DRY_RUN}" -eq 1 ]; then echo "    \$ $*"; else "$@"; fi
}

# ── 1. the command ────────────────────────────────────────────────────────────
echo "==> Installing oshell with extras: [${EXTRAS}]"
if command -v uv >/dev/null 2>&1; then
    echo "==> Using uv tool install (editable)"
    run uv tool install --editable "${SPEC}" --force
    run uv tool update-shell 2>/dev/null || true
    BIN="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
else
    echo "==> uv not found; falling back to python3 venv + pip + symlink"
    command -v python3 >/dev/null 2>&1 || { echo "ERROR: need uv or python3." >&2; exit 1; }
    run python3 -m venv .venv
    run ./.venv/bin/python -m pip install --upgrade pip >/dev/null
    run ./.venv/bin/python -m pip install -e "${SPEC}"
    BIN="$HOME/.local/bin"
    run mkdir -p "$BIN"
    run ln -sf "$(pwd)/.venv/bin/oshell" "$BIN/oshell"
fi
OSHELL="${BIN}/oshell"
if [ "${DRY_RUN}" -eq 1 ] && [ ! -x "${OSHELL}" ]; then OSHELL="oshell"; fi

# ── 2. machine memory: Mechanic (baselines) + Drift (state diffs) ─────────────
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
    if [ "${DRY_RUN}" -eq 1 ]; then
        echo "    \$ git clone --depth 1 ${repo} && bash ${name}/scripts/install.sh"
        return 0
    fi
    local src
    src="$(mktemp -d)"
    if git clone --quiet --depth 1 "${repo}" "${src}/${name}" \
        && (cd "${src}/${name}" && bash scripts/install.sh); then
        echo "==> ${name} installed."
    else
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

# ── 3. shell integration: Ctrl+G, '#…'→command, last-command capture ─────────
# Appends ONE marked line to your rc file; re-running finds the marker and
# leaves it alone. The line evals `oshell init <shell>` at shell start, so the
# integration tracks oshell upgrades without editing the rc again.
MARKER="# oshell shell integration"
install_shell_hook() {
    local shell_name rc line
    shell_name="$(basename "${SHELL:-/bin/sh}")"
    case "${shell_name}" in
        zsh)  rc="${ZDOTDIR:-$HOME}/.zshrc"; line='eval "$(oshell init zsh)"' ;;
        bash) rc="$HOME/.bashrc"; line='eval "$(oshell init bash)"' ;;
        fish) rc="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"; line='oshell init fish | source' ;;
        *)
            echo "NOTE: shell '${shell_name}' isn't one I know how to hook (zsh/bash/fish)."
            echo "      See: oshell init --help"
            return 0 ;;
    esac
    if [ -f "${rc}" ] && grep -qF "${MARKER}" "${rc}"; then
        echo "==> Shell integration already in ${rc}"
        return 0
    fi
    echo "==> Adding shell integration to ${rc}"
    echo "    ${line}"
    if [ "${DRY_RUN}" -eq 1 ]; then return 0; fi
    mkdir -p "$(dirname "${rc}")"
    {
        echo
        echo "${MARKER} — Ctrl+G asks · '#…' + Ctrl+G becomes the command · oshell fix knows your last command"
        echo "command -v oshell >/dev/null 2>&1 && ${line}"
    } >> "${rc}"
    if [ "${shell_name}" = "bash" ] && [ "$(uname -s)" = "Darwin" ] && [ -f "$HOME/.bash_profile" ] \
        && ! grep -q "bashrc" "$HOME/.bash_profile"; then
        echo "    (macOS bash: make sure ~/.bash_profile sources ~/.bashrc)"
    fi
}
if [ "${INSTALL_SHELL}" -eq 1 ]; then
    echo
    install_shell_hook
else
    echo "==> Skipping shell integration (--no-shell)"
fi

# ── 4. theme exports: ~/.oshell/current/ for terminals that want to follow ────
echo
echo "==> Writing theme exports to ~/.oshell/current/ (Ghostty · Alacritty · Kitty · WezTerm · btop)"
THEME="$("${OSHELL}" theme 2>/dev/null | awk 'NR==1{print $2}' || true)"
if [ "${DRY_RUN}" -eq 1 ]; then
    echo "    \$ oshell theme set ${THEME:-tokyo-night}"
else
    "${OSHELL}" theme set "${THEME:-tokyo-night}" >/dev/null 2>&1 || true
fi

# ── 5. presence: the job tick + standing orders ───────────────────────────────
if [ "${INSTALL_JOBS}" -eq 1 ]; then
    echo
    echo "==> Registering the once-a-minute job tick with the OS (skip with --no-jobs)"
    echo "    It runs whatever is due and exits otherwise; nothing sensitive runs unattended."
    run "${OSHELL}" jobs install || echo "NOTE: scheduler registration failed — later: oshell jobs install"
    if [ "${INSTALL_ORDERS}" -eq 1 ]; then
        echo "==> Creating the standing-orders job (edit orders in-app: menu → Standing orders)"
        if [ "${DRY_RUN}" -eq 1 ]; then
            echo "    \$ oshell orders install"
        else
            "${OSHELL}" orders install >/dev/null 2>&1 \
                || echo "NOTE: orders job already exists or failed — see: oshell orders"
        fi
    else
        echo "==> Skipping the standing-orders job (--no-orders)"
    fi
else
    echo "==> Skipping the job scheduler (--no-jobs); jobs stay on disk, nothing wakes them"
fi

# Is the bin dir actually on PATH right now?
case ":$PATH:" in
    *":$BIN:"*) ON_PATH=1 ;;
    *) ON_PATH=0 ;;
esac

# Friendly heads-up if the Ollama backend isn't reachable (not fatal).
HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_UP=1
if command -v curl >/dev/null 2>&1 && ! curl -fsS --max-time 2 "${HOST}/api/tags" >/dev/null 2>&1; then
    OLLAMA_UP=0
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

==> Try it (open a new terminal so the shell integration loads):
      oshell tui             # the workspace — bar, tiles, fastfetch, vitals
      oshell                 # interactive agent chat
      oshell do "…"          # propose a command → run / edit / describe / chat / no
      oshell fix             # why did the last command fail, and what fixes it
      oshell theme list      # 22 Omarchy palettes; `oshell theme set osaka-jade`
      oshell fetch           # neofetch for your assistant
      oshell orders          # standing orders (the agent keeps these true)
      oshell inbox           # what scheduled runs left for you
      oshell doctor          # health-check the whole rig

==> With Mechanic + Drift installed, ask it things only YOUR box can answer:
      "is my CPU usage normal right now?"
      "what changed on this machine since yesterday?"
EOF

# ── 6. first-run wizard (interactive; sizes models to this machine) ───────────
if [ "${RUN_SETUP}" -eq 1 ] && [ "${DRY_RUN}" -eq 0 ] && [ -t 0 ] && [ -t 1 ] && [ "${OLLAMA_UP}" -eq 1 ]; then
    echo
    echo "==> First-run wizard (skip with --no-setup; rerun any time with: oshell setup)"
    "${OSHELL}" setup </dev/tty || true
elif [ "${RUN_SETUP}" -eq 1 ] && [ "${DRY_RUN}" -eq 0 ]; then
    echo
    echo "==> Next: run 'oshell setup' to size models to this machine."
fi
