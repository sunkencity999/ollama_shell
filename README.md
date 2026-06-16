# Ollama Shell

**A local-first, agentic shell for Ollama.** The model runs on *your* machine,
can use *your* tools (files, time, models, the web), and never phones home
unless a tool you can see explicitly reaches out.

Created by Christopher Bradford · [contact@christopherdanielbradford.com](mailto:contact@christopherdanielbradford.com)

> **v0.2 — Reimagined.** This project began as a feature-rich chat REPL and grew
> into an everything-client. v0.2 inverts the architecture around three ideas:
> **(1) local-first / privacy-native**, **(2) the agent loop *is* the shell**
> (capabilities are tools the model calls, MCP-style), and **(3) a light core
> with opt-in power**. The proven feature set from v0.1 lives on as the
> [legacy engine](#legacy-engine). See [`docs/LEGACY_README.md`](docs/LEGACY_README.md)
> for the original, full v0.1 documentation.

---

## Why this design

| Principle | What it means in practice |
|-----------|---------------------------|
| **Local-first** | Inference is local (Ollama/MLX/LM Studio). Every networked tool is flagged and shown in a privacy banner; the base install reaches nothing. |
| **Agent as the shell** | Chat, file ops, web search, etc. are *tools* the model invokes in a loop — not bolted-on commands. New capabilities are additive: register a tool, done. |
| **Light core, opt-in power** | The core install is 5 pure-Python deps. Heavy features (web, RAG, docs export, fine-tuning) are optional `pip` extras. |

## Quick start

```bash
# 1. Install (uv recommended). Core is tiny; add extras as needed.
uv venv .venv
uv pip install --python .venv -e .            # core
uv pip install --python .venv -e ".[tui,web]" # + Textual UI + web search

# 2. Make sure Ollama is running, then:
.venv/bin/oshell chat        # interactive agent chat (default)
.venv/bin/oshell tui         # Textual workspace (needs [tui])
.venv/bin/oshell ask "What time is it? Use your tool."
.venv/bin/oshell models      # list backend models
.venv/bin/oshell config      # show resolved config
```

`make install` / `make run` / `make tui` / `make test` wrap the above.

## The TUI workspace

`oshell tui` opens a three-pane workspace instead of a scrolling REPL:

```
┌──────────────────────────────┬───────────────────────┐
│ Conversation                 │ Context  📌 pinned     │
│ › what files are here?       │  0 syst You are Ollama │
│ ⚙ list_dir → README.md, ...  │  1 user what files...  │
│ The directory contains …     │ ───────────────────────│
│                              │ Tool activity          │
│                              │ ⚙ list_dir({})         │
│                              │   ↳ README.md pyproject │
└──────────────────────────────┴───────────────────────┘
```

The **context inspector** makes the old invisible `/pin` and `/exclude` commands
visual: you can see exactly which messages the model is being shown.

## Architecture

```
oshell/
  config.py            Typed, layered config (defaults<config.json<config.local.json<env)
  providers/           LLMProvider abstraction
    base.py              Message / ToolCall / ChatChunk / LLMProvider
    ollama.py            Ollama REST + streaming (tool-aware)
    openai_compat.py     LM Studio / vLLM / llama.cpp / MLX (OpenAI schema)
  tools/               MCP-style host
    base.py              Tool + ToolRegistry (advertise specs, dispatch calls)
    builtins.py          current_time, list_models, sandboxed read/write/list files
    web.py               web_search + fetch_url (opt-in [web]; flagged network-touching)
  agent/
    loop.py              The loop: model drives, multi-round tool-use, pin/exclude
    events.py            TextDelta / ToolStarted / ToolFinished / TurnComplete / LimitReached
  cli.py                 Thin Typer/Rich front-end
  tui/app.py             Textual workspace
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
| `docs` | Word/Excel/PDF/Markdown export |
| `vision` | Image analysis (Pillow) |
| `all` | everything above |

```bash
uv pip install -e ".[all]"
```

## Development

```bash
make install     # .venv + core + dev + tui
make test        # pytest (live Ollama tests self-skip when offline)
make cov         # + coverage report
make lint        # ruff
make fmt         # ruff --fix + format
```

CI (GitHub Actions) runs ruff + mypy + pytest on Python 3.10–3.13.

## Legacy engine

The original v0.1 application — a 4,600-line interactive shell plus modules for
web research, fine-tuning (Unsloth/MLX), Confluence/Jira/filesystem MCP
integrations, and a vector knowledge base — remains runnable at the repo root:

```bash
python ollama_shell.py
```

These modules are the *proven* feature set. The v0.2 roadmap bridges them into the new core as tools so capabilities
migrate cleanly and the monolith can retire. **Done:** `web_browsing`'s
extraction core → the `fetch_url` tool (paired with `web_search`). **Next:**
`file_creation` → document-export tools; then Confluence/Jira/RAG/fine-tuning.
Full v0.1 docs: [`docs/LEGACY_README.md`](docs/LEGACY_README.md).

### Repository layout

| Path | What |
|------|------|
| `oshell/` | the reimagined v0.2 core (this README) |
| `ollama_shell.py` + sibling modules | the v0.1 legacy engine |
| `tests/` | v0.2 test suite (`tests/legacy/` holds archived v0.1 scratch tests) |
| `examples/`, `scripts/` | relocated demos and installer/migration utilities |
| `docs/` | guides + legacy README |

## License

MIT.
