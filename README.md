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
| **Local-first** | Inference is local (Ollama/MLX/LM Studio). Every networked tool is flagged and shown in a privacy banner; the base install reaches nothing. |
| **Agent as the shell** | Chat, file ops, web search, etc. are *tools* the model invokes in a loop — not bolted-on commands. New capabilities are additive: register a tool, done. |
| **Light core, opt-in power** | The core install is 5 pure-Python deps. Heavy features (web, RAG, docs export, fine-tuning) are optional `pip` extras. |

## Quick start

```bash
# 1. Install. Puts `oshell` on your PATH (via `uv tool install`, editable;
#    falls back to a venv + symlink). Warns if Ollama isn't running.
./install.sh            # macOS / Linux — core + tui (interactive default)
./install.sh all        # everything: tui, web, rag, docs, vision, finetune
./install.sh web,rag    # or a custom subset of extras
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

On startup (and any time you press **F2**) an old-school, keyboard-driven
**menu** pops up — navigate with ↑/↓ + Enter or just press a number — for Chat,
Models, Tools, Knowledge base, Fine-tuning, Settings, Help, and Quit. Esc drops
back to the conversation.

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
    web.py               web_search + fetch_url (opt-in [web]; flagged network-touching)
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
| `web` | DuckDuckGo search + scraping (BeautifulSoup, Selenium) |
| `rag` | ChromaDB + sentence-transformers knowledge base |
| `finetune` | MLX-LM LoRA fine-tuning (Apple Silicon) |
| `docs` | Word/Excel/PDF/Markdown export |
| `vision` | Image analysis (Pillow) |
| `all` | everything above |

```bash
uv pip install -e ".[all]"
```

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
