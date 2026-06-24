# Ollama Shell

**A local-first, agentic shell for Ollama.** The model runs on *your* machine,
can use *your* tools (files, time, models, the web), and never phones home
unless a tool you can see explicitly reaches out.

Created by Christopher Bradford · [contact@christopherdanielbradford.com](mailto:contact@christopherdanielbradford.com)

> **v0.2 — Reimagined.** This project began as a feature-rich chat REPL and grew
> into a 4,600-line everything-client. v0.2 inverts the architecture around three
> ideas: **(1) local-first / privacy-native**, **(2) the agent loop *is* the shell**
> (capabilities are tools the model calls, MCP-style), and **(3) a light core
> with opt-in power**. The v0.1 monolith has now been **fully retired** — every
> capability was migrated into clean, tested tools (see
> [migration](#legacy-migration-complete)). The original code lives on only in
> git history and [`docs/LEGACY_README.md`](docs/LEGACY_README.md).

---

## Why this design

| Principle | What it means in practice |
|-----------|---------------------------|
| **Local-first** | Inference is local (Ollama/MLX/LM Studio). Network-touching tools (web search/fetch, Atlassian) are flagged in a privacy banner and only run when the model calls them — nothing phones home on its own. |
| **Agent as the shell** | Chat, file ops, web search, etc. are *tools* the model invokes in a loop — not bolted-on commands. New capabilities are additive: register a tool, done. |
| **Light core, opt-in power** | A small core (chat, agent loop, **web search + fetch**, files). Heavy features (RAG, docs export, fine-tuning, the TUI) are optional `pip` extras. |

## Quick start

```bash
# 1. Install. Puts `oshell` on your PATH (via `uv tool install`, editable;
#    falls back to a venv + symlink). Warns if Ollama isn't running.
./install.sh            # macOS / Linux — core + tui (interactive default)
./install.sh all        # everything: tui, rag, docs, vision, finetune
./install.sh rag        # or a custom subset of extras (web search is built in)
#   Windows (PowerShell):  .\install.ps1   (same arguments)

# 2. Make sure Ollama is running (https://ollama.com), then — from anywhere:
oshell                  # interactive agent chat (default command)
oshell tui              # Textual workspace (needs [tui])
oshell ask "What time is it? Use your tool."
oshell models           # list backend models
oshell config           # resolved config + which capabilities are available
oshell finetune detect  # local LoRA training backend
```

If `oshell` isn't found, open a new terminal (so the updated PATH loads) or add
the printed bin dir to PATH. Prefer raw `uv`? `uv tool install --editable ".[tui]"`.
For a dev checkout, `make install` builds a local `.venv`; `make run / tui / test`
wrap the common flows. macOS users can also double-click **Start Ollama Shell.command**.

## The TUI workspace

`oshell tui` opens a workspace instead of a scrolling REPL: the conversation on
the left, and a tabbed sidebar — **Tools**, **Context**, **Activity** — on the
right. The header shows the model, backend, tool count, and privacy posture.

```
┌────────────────────────────────┬──────────────────────────────┐
│ Ollama Shell · llama3.2 · ollama · 12 tools · network: web_…   │
├────────────────────────────────┼──────────────────────────────┤
│ Conversation                   │ [Tools] Context  Activity     │
│ › what files are here?         │  Active tools                 │
│ The directory contains …       │   local list_dir              │
│                                │   net   web_search            │
│                                │   …                           │
│                                │  Optional features            │
│                                │   ✓ rag (knowledge base)      │
│                                │   ✗ docs  (pip install …[docs])│
├────────────────────────────────┴──────────────────────────────┤
│ Message the model…   (Ctrl+C quit · Ctrl+T tools)              │
└─────────────────────────────────────────────────────────────--┘
```

- **Tools** — the live tool roster (local vs network) plus which optional
  features this install actually has. This is the TUI's source of truth for
  what the app can currently do.
- **Context** — the pin/exclude state, making the `/pin` and `/exclude` controls
  visual: you see exactly which messages the model is shown.
- **Activity** — a running log of tool calls and their results.

While the model works, a live region under the conversation shows an animated
spinner with the current status (*Thinking…*, *Running web_search…*) and then
**streams the reply token-by-token** as it's generated — no more staring at a
blank space.

On startup (and any time you press **Esc**) an old-school, keyboard-driven
**menu** pops up — navigate with ↑/↓ + Enter or just press a number. From it you can:

- **Models** — pick the active model from those on the backend. Your choice is
  **saved as the default** (to `config.local.json`) and persists across sessions
  until you change it.
- **Install features** — install optional capabilities (RAG, docs export,
  vision, fine-tuning) into the running environment without leaving the app.
  Install output **streams live into the Activity tab** (with the current step
  on the spinner), and the Tools panel refreshes ✓ when it finishes.
- **Attach image** — attach an image (by file path — drag a file into the
  terminal to paste it — or from the clipboard with Pillow installed) to send to
  a **vision-capable model** (e.g. `llava`, `gemma3`/`gemma4`, `llama3.2-vision`;
  pick one in Models). The agent only advertises tools to models that support
  them, so vision-only models like `llava` work too.

You can also **paste multi-line text** (logs, code) straight into the prompt —
it's buffered and sent with your next message rather than truncated to one line.

**Copying out.** The TUI captures the mouse, so normal click-drag selection
doesn't work in the window. Use **Ctrl+Y** to copy the model's last reply, or the
menu's *Copy transcript* for the whole conversation (via your OS clipboard, with
an OSC 52 fallback for SSH). To select text by hand, hold **Option** (macOS /
iTerm2) or **Shift** (many terminals) while dragging to use native selection.
- Plus Chat, Tools, Knowledge base, Fine-tuning, Settings, Help, and Quit.

## Architecture

```
oshell/
  config.py            Typed, layered config (defaults<config.json<config.local.json<env)
  capabilities.py      Reports which optional features/integrations are available
  providers/           LLMProvider abstraction
    base.py              Message / ToolCall / ChatChunk / LLMProvider
    ollama.py            Ollama REST + streaming (tool-aware)
    openai_compat.py     LM Studio / vLLM / llama.cpp / MLX (OpenAI schema)
  tools/               MCP-style host
    base.py              Tool + ToolRegistry (advertise specs, dispatch calls)
    builtins.py          current_time, list_models, sandboxed read/write/list files
    system.py            run_command (shell exec, cross-platform) + system_info
    gui.py               screenshot + gui_click/type/key/move (opt-in, vision-gated)
  gui/controller.py      desktop-control backends (pyautogui; native seam)
    web.py               web_search + fetch_url (core; flagged network-touching)
    documents.py         create_document — txt/md/csv/docx/xlsx/pdf (opt-in [docs])
    knowledge.py         add_knowledge + search_knowledge tools (opt-in [rag])
    atlassian.py         jira_search/get_issue + confluence_search/get_page (Server/DC)
  knowledge.py         KnowledgeBase: ChromaDB + sentence-transformers (lazy, on-disk, no telemetry)
  integrations/
    atlassian.py         Jira/Confluence Server REST clients (reuse JIRA_*/CONFLUENCE_* env)
  finetune/            detect hardware, prep datasets, manage jobs, run mlx_lm.lora
    cli.py               `oshell finetune detect|create|start|status|list`
  agent/
    loop.py              The loop: model drives, multi-round tool-use, pin/exclude
    events.py            TextDelta / ToolStarted / ToolFinished / TurnComplete / LimitReached
  cli.py               Thin Typer/Rich front-end
  tui/app.py           Textual workspace (Tools / Context / Activity tabs)
```

The agent loop emits a stream of **events**; the CLI and TUI are just renderers
of that stream. Swapping the backend is a one-line config change
(`provider.name`), because nothing above `providers/` knows which runtime it's
talking to.

### Configuration

Resolved in increasing precedence: built-in defaults → `config.json` (committed,
shared) → `config.local.json` (per-machine, git-ignored) → `OSHELL_*` env vars
(use `__` for nesting, e.g. `OSHELL_PROVIDER__HOST`). See `.env.example`.

> v0.1 silently un-tracked `config.json` via a blanket `*.json` .gitignore rule.
> That's fixed: config is tracked; real secrets go in `.env` / `config.local.json`.

### Optional extras

| Extra | Adds |
|-------|------|
| `tui` | Textual workspace |
| `rag` | ChromaDB + sentence-transformers knowledge base |
| `finetune` | MLX-LM LoRA fine-tuning (Apple Silicon) |
| `docs` | Word/Excel/PDF/Markdown export |
| `vision` | Image analysis (Pillow) |
| `gui` | GUI computer-use — screenshots + mouse/keyboard (pyautogui) |
| `all` | everything above |

```bash
uv pip install -e ".[all]"
```

## Terminal / computer-use

Ollama Shell is an *agentic* TUI: the model can act on your machine, not just
chat. The `run_command` tool runs shell commands through the platform's own
shell — `/bin/sh` on macOS/Linux, `cmd.exe` on Windows — with the workspace as
the working directory, so the agent can inspect the system, drive git/builds,
run scripts, and process files. `system_info` gives a safe, read-only summary
(OS, arch, CPU, cores, RAM) without a shell.

**Cross-platform.** Commands run through the platform's own shell: `/bin/sh` on
macOS/Linux, **PowerShell** on Windows (`pwsh` if present, else `powershell`;
force `cmd` with `{"shell":{"windows_shell":"cmd"}}`). The shell is **persistent**
— `cd`, env vars, and activated virtualenvs carry across `run_command` calls (a
long-lived `/bin/sh`, or PowerShell on Windows). A new session is health-probed
and **falls back to one-shot automatically** if it isn't responsive, so it can
never hang. GUI key chords are normalized per-OS (`cmd`→`win` on Windows,
`command` on macOS) and the model is told which OS it's on. Disable persistence
with `{"shell": {"persistent": false}}`.

> **Autonomy & safety.** By default `run_command` runs **without per-command
> confirmation** — full autonomy. Every command and its output are shown inline
> in the conversation (`🔧 run_command(...) → …`) and the tool is flagged `exec`
> (red) in the Tools panel, with a banner on startup, so you always see what
> ran. To require review or disable it, set `shell.enabled`/timeout in
> `config.local.json` (e.g. `{"shell": {"enabled": false}}`) — or just don't ask
> it to. Commands run with your user's privileges; treat the model accordingly.

### GUI computer-use (opt-in)

Beyond the terminal, the model can drive the **desktop GUI** — take a
screenshot, then click/type/press keys — for tasks a shell can't do. It's
**off by default** and only available with a **vision-capable model** (it has to
*see* the screen). The terminal stays the autonomous default; the model is told
to prefer `run_command` and use the GUI only when a task genuinely needs it.

```jsonc
// config.local.json
{ "gui": { "enabled": true } }
```

- Install the backend from the menu (**Install features → GUI computer-use**) or
  `./install.sh gui` (pyautogui). macOS needs **Screen Recording + Accessibility**
  permission for your terminal; Linux X11 works out of the box (Wayland support is
  a planned native backend).
- Select a vision+tools model (e.g. `gemma3`/`gemma4`, `llama3.2-vision`) in
  **Models** — the GUI tools (`screenshot`, `gui_click`, `gui_type`, `gui_key`,
  `gui_move`) appear only then, flagged `exec` (red).
- The model screenshots, the image is fed back so it can see, it acts, and
  screenshots again to verify. A pyautogui failsafe (slam the mouse into a
  screen corner) aborts a runaway loop.

The control layer is a `Controller` abstraction (`oshell/gui/`) with a pyautogui
backend today and a clean seam for native backends (Wayland `grim`/`ydotool`,
macOS `screencapture`/`cliclick`).

## Fine-tuning (local LoRA)

On Apple Silicon, `oshell finetune` drives MLX-LM LoRA training; jobs are tracked
on disk under `~/.oshell/finetune`.

```bash
oshell finetune detect                                   # mlx / unsloth / cpu
oshell finetune create my-run -m <hf-model> -d data.jsonl  # prep + register
oshell finetune start <job-id>                           # launch mlx_lm.lora
oshell finetune status <job-id>                          # running/completed/failed
oshell finetune list
```

Datasets may be `.jsonl/.json/.csv/.tsv/.txt`; records are normalized to a
`{"text": …}` training set (text / prompt+completion / chat-messages all work).
Needs the `finetune` extra (`mlx-lm`).

## Development

```bash
make install     # .venv + core + dev + tui
make test        # pytest (live Ollama tests self-skip when offline)
make cov         # + coverage report
make lint        # ruff
make fmt         # ruff --fix + format
```

CI (GitHub Actions) runs ruff + mypy + pytest (`-m "not snapshot"`) on Python
3.10–3.13. The TUI has a Textual SVG **layout snapshot** test (marked `snapshot`,
run locally since baselines are pinned to a Textual version); regenerate it after
intentional layout changes with `make snapshot`.

## Legacy migration (complete)

The v0.1 monolith (`ollama_shell.py`) and all its sibling modules have been
**deleted**. Each capability was reimplemented as a clean, tested tool and
verified before its legacy source was removed:

| v0.1 module(s) | → v0.2 | Verification |
|----------------|--------|--------------|
| `web_browsing` (extraction core) | `fetch_url` + `web_search` | live fetch of a real page |
| `file_creation` + `fixed_file_handler` | `create_document` tool | model wrote a real `.docx` |
| monolith `KnowledgeBase` | `oshell.knowledge` + `add/search_knowledge` | live semantic round-trip |
| `finetune.py` + `finetune_modules/` | `oshell.finetune` + `oshell finetune` | command verified vs real `mlx_lm.lora` |
| `*_mcp_integration` (Confluence/Jira) | `oshell.integrations.atlassian` + 4 tools | live read-only call to a real Server |

**Not carried over** (available in git history if ever needed): the standalone
filesystem-MCP server (the core read/write/list operations are covered by
built-in sandboxed tools), the `task_manager` to-do subsystem, and the
Glama/`mcp_browser` browser-automation integrations. Open an issue or ask if
you want any of these migrated next.

### Repository layout

| Path | What |
|------|------|
| `oshell/` | the entire application (core + tools + integrations + finetune + tui) |
| `tests/` | the test suite (`tests/legacy/` holds archived v0.1 scratch tests) |
| `examples/`, `scripts/` | relocated v0.1 demos and utilities |
| `docs/` | guides; `docs/LEGACY_README.md` + `docs/legacy/` preserve v0.1 docs |

## License

MIT.
