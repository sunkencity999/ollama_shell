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
    documents.py         create_document — txt/md/csv/docx/xlsx/pdf (opt-in [docs])
    knowledge.py         add_knowledge + search_knowledge — local vectors (opt-in [rag])
    atlassian.py         jira_search/get_issue + confluence_search/get_page (Server/DC)
  knowledge.py           KnowledgeBase: ChromaDB + sentence-transformers (lazy, on-disk)
  integrations/
    atlassian.py         Jira/Confluence Server REST clients (reuse JIRA_*/CONFLUENCE_* env)
  finetune/              detect hardware, prep datasets, manage jobs, run mlx_lm.lora
    cli.py               `oshell finetune detect|create|start|status|list`
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
| `finetune` | MLX-LM LoRA fine-tuning (Apple Silicon) |
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
