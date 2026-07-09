# Ollama Shell

### A local-first AI that lives on *your* machine, uses *your* tools, and keeps *your* secrets.

No API keys. No cloud round-trips. No telemetry. Just a capable, agentic model
running on your own hardware — one that can read your files, run your shell,
search the web when you ask, write you a report, drive a hidden browser… and,
when the room goes quiet, sit there and **daydream**.

### ▶ [**Watch the live demo →**](https://sunkencity999.github.io/ollama_shell/)

A 60-second animated playthrough — a late-night session with real tool calls,
markdown-rendered replies (highlighted code included), a live theme switch,
per-turn vitals, memory… and, when it goes quiet, a daydream under a rainy sky
(the session had a traceback in it). No install required to watch.

Created by Christopher Bradford · [contact@christopherdanielbradford.com](mailto:contact@christopherdanielbradford.com)

> **v0.2 — Reimagined.** This began as a feature-rich chat REPL and grew into a
> 4,600-line everything-client. v0.2 turns it inside out around three ideas:
> **local-first & privacy-native**, **the agent loop *is* the shell** (every
> capability is a tool the model calls, MCP-style), and **a light core with
> opt-in power**. The v0.1 monolith is **fully retired** — every feature was
> migrated into clean, tested tools ([see the table](#the-great-migration-complete)).
> The old code lives on only in git history and [`docs/LEGACY_README.md`](docs/LEGACY_README.md).

---

## Why you might love it

- 🔒 **It's genuinely private.** Inference runs locally (Ollama / MLX / LM Studio).
  The only things that ever touch the network are tools *you* can see the model
  call — web search, fetch, Atlassian — each flagged in a privacy banner. Nothing
  phones home on its own. Ever.
- 🧰 **It actually *does* things.** It's not a chatbot with buttons bolted on. The
  model drives a loop — reading files, running commands, searching, writing
  documents — and you watch each tool call happen inline, in real time.
- 🪶 **It starts light and grows with you.** A small core (chat, agent loop, web
  search + fetch, files). Everything heavier — RAG, document export, vision,
  fine-tuning, the full TUI, computer-use — is an opt-in extra you can install
  *from inside the app*.
- 🧠 **It remembers you.** A dependency-free memory of durable facts ("I'm on
  Apple Silicon", "I like terse answers") carries across sessions, and your last
  conversation resumes right where you left it.
- 🩺 **It remembers your *machine*.** The installer ships two local daemons —
  [Mechanic](https://github.com/sunkencity999/mechanic) (runtime baselines) and
  [Drift](https://github.com/sunkencity999/drift) (state snapshots) — mounted
  over MCP, so the shell can answer *"is 92% CPU normal **for this box**?"* and
  *"what changed since Tuesday?"* — then fix what it finds. No cloud model can
  give you that loop.
- 💭 **It has an inner life.** Ask it to `/daydream` and it stops being useful for
  a moment to free-associate a small, surreal vignette about whatever you'd been
  discussing. Useless on purpose. Local-first, so indulging is free.
- 🎨 **It's a place you want to be.** Markdown-rendered replies with highlighted
  code, live-preview color themes (nord, gruvbox, tokyo-night…), a command
  palette, tokens-per-second vitals under every reply — and a night sky that
  rains after a stormy debugging session.

If the design philosophy interests you, here it is in one table:

| Principle | What it means in practice |
|-----------|---------------------------|
| **Local-first** | Inference is local. Network-touching tools are flagged and only run when the model calls them. Your data stays yours. |
| **Agent *is* the shell** | Chat, files, web, shell exec are *tools* invoked in a loop — not hardcoded commands. New power = register a tool. |
| **Light core, opt-in power** | Small core + optional `pip` extras (RAG, docs, vision, finetune, TUI, computer-use), installable from the menu. |

## Quick start

```bash
# 1. Install. Puts `oshell` on your PATH (uv tool install, editable;
#    falls back to a venv + symlink). Warns if Ollama isn't running.
#    Also installs the machine-memory pair (Mechanic + Drift) by default.
./install.sh                    # macOS / Linux — core + tui + machine memory
./install.sh all                # the works: tui, rag, docs, vision, finetune
./install.sh rag                # …or any custom subset (web search is built in)
./install.sh tui --no-monitors  # skip Mechanic + Drift
#   Windows (PowerShell):  .\install.ps1   (no monitors — they need launchd/systemd)

# 2. Make sure Ollama is running (https://ollama.com), then — from anywhere:
oshell                  # interactive agent chat (default command)
oshell tui              # the Textual workspace (needs [tui]) — the good stuff
oshell ask "What time is it? Use your tool."
oshell models           # list backend models
oshell config           # resolved config + which capabilities are live
oshell finetune detect  # local LoRA training backend
```

`oshell` not found? Open a new terminal (so PATH reloads) or add the printed bin
dir to PATH. Prefer raw `uv`? `uv tool install --editable ".[tui]"`. For a dev
checkout, `make install` builds a local `.venv`; `make run / tui / test` wrap the
common flows. On macOS you can also double-click **Start Ollama Shell.command**.

> Because the install is **editable**, code changes take effect on the next
> launch — but a *running* `oshell` won't hot-reload. After updating, quit and
> relaunch to pick up changes.

## What it feels like — the TUI workspace

`oshell tui` opens a workspace, not a scrolling REPL: the conversation on the
left, a tabbed sidebar — **Tools · Context · Activity** — on the right. The header
shows the model, backend, tool count, and privacy posture at a glance
(`gemma4:26b · ollama · 29 tools · 9 net`).

```
┌────────────────────────────────┬──────────────────────────────┐
│ Ollama Shell · llama3.2 · ollama · 12 tools · 2 net           │
├────────────────────────────────┼──────────────────────────────┤
│ ───────────────────── 10:25 ── │ [Tools] Context  Activity     │
│ › what files are here?         │  Active tools                 │
│ The directory contains …       │   local list_dir ×3           │
│ 🔧 list_dir(.) → 14 entries    │   net   web_search            │
│    ⏱ 2.1s · ~38 tok/s · ctx 9% │   …                           │
│ › /daydream                    │  Optional features            │
│ 💭 a clock made of warm rain…  │   ✓ rag (knowledge base)      │
│                                │   ✗ docs  (pip install …[docs])│
├────────────────────────────────┴──────────────────────────────┤
│ Message the model…  (Esc menu · Ctrl+P palette · Ctrl+C quit) │
└─────────────────────────────────────────────────────────────--┘
```

- **Tools** — the live roster (local vs network), warmed by use: tools the model
  has actually reached for this session glow with a `×N` count. This panel is the
  source of truth for what the app can do *right now*.
- **Context** — the pin/exclude state made visual, topped by a **fill gauge**
  (`▰▰▰▱▱▱ 38% of ~32k tokens (auto)`) so excluding messages has visible
  consequences.
- **Activity** — a running log of every tool call and its result.

**Replies are rendered, not dumped.** Finished replies commit to the transcript
as real **Markdown** — headings, lists, and **syntax-highlighted code blocks** —
so a local model's output reads like a document, not a log. A dim, timestamped
rule opens each exchange, and a vitals line closes it: `⏱ 3.4s · ~41 tok/s ·
ctx 12%` — elapsed time, streaming rate, and how full the context window is.

While the model works, a live region streams the reply **token-by-token** behind
an animated status (*Thinking… · Running web_search…*) — no blank-screen waiting.
And it's honest about its own actions: every tool call is echoed inline
(`🔧 run_command(...) → …`) so you can trust — or catch — exactly what it did.
Status chatter ("copied", "model set", install progress) appears as **toast
notifications** that fade from the corner — the transcript stays a conversation.

**The old-school menu.** On startup, and any time you press **Esc**, a
keyboard-driven menu pops up — grouped into titled sections, driven with arrow
keys + Enter or by number (two-digit numbers work: type `1`+`4` for item 14).
A faint constellation hangs behind it. From it:

- **Models** — pick the active model, each badged with its size and quantization
  (`26B · Q8_0`); your choice is **saved as the default** across sessions.
- **Theme** — restyle the whole app, previewed **live** as you arrow through
  nord, gruvbox, tokyo-night, catppuccin, dracula, and friends. Enter keeps it
  (persisted), Esc puts the room back the way it was.
- **Install features** — add RAG / docs / vision / fine-tuning / computer-use into
  the running environment *without leaving the app*. Output streams live into the
  Activity tab and the Tools panel ticks ✓ when it finishes.
- **Attach image** — send an image (file path — drag a file into the terminal — or
  the clipboard with Pillow) to a **vision-capable model** (`llava`, `gemma3`/
  `gemma4`, `llama3.2-vision`).
- Plus New conversation, Copy reply/transcript, Memory, Knowledge base,
  **Daydream**, Fine-tuning, Settings, Help, and Quit.

**The command palette.** Press **Ctrl+P** and every menu action is
fuzzy-searchable — type "day" ↵ instead of Esc-then-14. The menu is for
discovery; the palette is for the tenth session.

**Little niceties.** Paste **multi-line text** (logs, code) straight in — it's
buffered and sent with your next message, not truncated. Copy out with **Ctrl+Y**
(last reply), **Ctrl+B** (the last fenced **code block** — usually what you
actually want), or *Copy transcript* (whole chat) via your OS clipboard, with an
**OSC 52** fallback that even works over SSH. A fresh conversation opens with a
small welcome card — model badge, privacy posture, and a few things to try. To
hand-select text, hold **Option** (macOS/iTerm2) or **Shift** (many terminals)
while dragging.

## 💭 Daydreams — the shell's inner life

Type **`/daydream`** (or pick **Daydream** from the menu) and the model drops the
helpful-assistant act for a moment and just *dreams*. It free-associates a short,
surreal vignette that drifts off from whatever you'd recently been discussing,
coloured by a randomly chosen lens — *"as if you were a cat dozing on a warm
CPU," "in the grammar of dreams, where verbs grow leaves," "like the last thought
of a candle before it gutters out."*

Talk about your G-Shock's backlight, then ask it to daydream, and you might get:

> *A single click triggers a flood of green light that sprouts into heavy, velvet
> vines along the silicon wrist. Verbs begin to leaf, their meanings unfurling
> like emerald ferns in the humid warmth of a digital jungle. Every ticking
> second is a seed falling into the dark, mossy soil of an infinite hour.*

It's deliberately, gloriously useless. Some design choices I cared about:

- **Ephemeral** — a daydream is *never* written to conversation history, so it
  can't pollute the model's working context or your saved session. It floats by
  in dim italic with a 💭, and it's gone.
- **Grounded but divergent** — it riffs on your recent topics, but the random
  motif and a higher temperature mean asking twice never gives the same dream.
- **No tools, all imagination** — tool access is suppressed for the dream; it
  can only wander.

Works at the prompt (`/daydream` / `/dream`), in the menu, and in the plain CLI.
Disable with `{"fun":{"daydreams":false}}`. Want to see one before you install?
[**▶ Watch the demo**](https://sunkencity999.github.io/ollama_shell/).

### Ambient effects — a shell you can live in

The TUI has a quiet visual pulse. The rule: **motion never enters text you're
reading** — it lives in the periphery, and every effect *means* something:

- 🌌 **Dream Mode** — `/daydream` takes the whole stage: a full-screen night sky
  of twinkling stars (and the occasional comet) that the dream streams into,
  centered. Any key wakes the shell; the dream is kept in the transcript.
- 🌦 **Weather in the sky** — the dream sky takes a mood from your session:
  after a stormy debugging stretch (errors, tracebacks, crashes in the recent
  conversation) **rain** streaks fall through the stars; in December it
  **snows**; otherwise, a clear night. Tune the sky's fullness with
  `{"fun":{"sky_density":2.0}}` for a busier night (0 empties it).
- 🌈 **Aurora** — while the model thinks, the spinner and status drift slowly
  through cool hues instead of sitting at a fixed cyan. Breathing, not blinking.
- ✨ **Embers** — when a tool finishes, a tiny spark fades (`✦ ✧ ∗ ·`) in the
  status strip — amber for network tools, magenta for memory, green for local.
- 🎆 **A particle storm** — if the model hits the tool-round cap, a brief scatter
  of warm sparks crosses the status strip while it wraps up with what it has.
- 🐛 **Fireflies** — leave the shell quiet for a bit and two or three faint
  fireflies drift across the empty status strip, keeping the place warm. Any
  keystroke disperses them.
- ✨ **Menu constellation** — a few faint, well-spaced stars behind the startup
  menu. Just because.

**Moods — pick your own weather.** The idle strip's ambience is yours to choose:
**menu → Mood** (with a live animated preview), `/mood` at the prompt, or
`/mood rain` to set one directly. The set: `fireflies` (default) · `rain` ·
`snow` · `aurora` · `ocean` · `starfield` · `embers` · `matrix` · `none`.
Your pick starts playing immediately, persists across sessions, survives a
`/daydream` (waking from the dream, the weather keeps falling), and — if you
choose rain or snow — carries into the dream sky too. The mood appears in the
full-width strip after ~45s of quiet (`{"fun":{"mood_idle_seconds":10}}`).

**…and then it takes the stage.** Leave the shell alone for ~3 minutes and the
mood stops being a strip: the weather falls **on top of the whole workspace** —
rain streaking between your messages, matrix glyphs over the sidebar — with
everything still readable underneath, lightly dimmed. Any key or click wakes
the shell (and is swallowed, screensaver-style); the strip weather carries on.
Tune or disable with `{"fun":{"mood_takeover_seconds":0}}`.

All of it switches off with `{"fun":{"effects":false}}` — and none of it costs
you anything while a turn is rendering (one 10 fps timer that was already there).

## Memory & resume — it knows you next time

A lightweight, **always-on memory** of durable facts about you (your name, the
tools you use, how you like answers, ongoing projects) carries context across
sessions — separate from the heavier, opt-in RAG knowledge base.

- **Hybrid capture** — the model saves a fact on its own when it clearly matters
  (shown inline as `📝 remembered: …` so you can see and correct it), or just say
  *"remember that …"*.
- **Auto-recall** — stored facts are injected into the system prompt, so it simply
  *knows* them next launch. (`recall` lets it search the full set as memory grows.)
- Dependency-free at `~/.oshell/memory.json`. View via **menu → Memory**; prune
  with *"forget X"* / *"forget all"*. Disable with `{"memory":{"enabled":false}}`.

**Conversation resume.** Your transcript is saved to `~/.oshell/last_session.json`
after each turn, so reopening `oshell tui` picks up right where you left off.
Start fresh with **menu → New conversation** or **`/clear`**. Disable with
`{"session":{"persist":false}}`.

**Slash commands.** `/clear` (new conversation), `/daydream` (wander 💭), `/menu`
(open the menu), `/help` (keys + commands).

## Machine memory — Mechanic × Drift, over MCP

Every AI assistant starts blind about your box: ask "why is this slow?" and it
gets generic advice, because a fresh `top` has no baseline and `lsof` has no
yesterday. oshell ships with the two tools that fix that — installed by
default, mounted as native tools, and taught to the model as a **diagnosis
pattern**:

- **[Mechanic](https://github.com/sunkencity999/mechanic)** samples runtime
  metrics (CPU, memory, Docker, *loaded Ollama models*) into a local SQLite
  baseline. Its tools answer *"is this normal **for this machine**?"* —
  `mechanic_is_this_normal`, `mechanic_baseline_for`, `mechanic_what_changed_since`.
- **[Drift](https://github.com/sunkencity999/drift)** snapshots operational
  state (ports, services, packages, users, cron) every few hours. Its tools
  answer *"what changed on this box?"* — `drift_diff_latest`, `drift_diff`,
  `drift_latest`.

**The loop no cloud assistant can close:** Mechanic says *whether* something is
off ("CPU is 8σ above your normal") → Drift says *what moved* ("a new launchd
service appeared 2 hours ago") → `run_command` fixes it. Anomaly → cause → fix,
entirely on your own hardware.

Both are fully standalone projects (local-first, user-level, no sudo, no
egress) with their own daemons; oshell spawns their MCP servers on demand and
degrades gracefully when they're absent — the Tools panel shows
`✗ mechanic (MCP)` with the install hint. Skip them at install time with
`./install.sh tui --no-monitors`.

### Any MCP server, actually

Mechanic and Drift ride a general mechanism: oshell is now a real **MCP
client**. Any stdio MCP server can be mounted as native tools from
`config.local.json` — no plugins, no code:

```json
{
  "mcp_servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "…"},
      "network": true
    }
  }
}
```

Tools register as `<server>_<tool>` (so the roster shows where each came from),
and `network: true` flags a server's tools `net` in the privacy UI. Servers
are spawned once and shared across model switches; a hung server can never
hang a turn (every call has a timeout and degrades to a tool error the model
can route around).

## Computer-use — it can act, not just chat

Ollama Shell is *agentic*: the model can do things on your machine.

**The terminal (always on).** `run_command` runs shell commands through your
platform's own shell — `/bin/sh` on macOS/Linux, **PowerShell** on Windows (`pwsh`
if present, else `powershell`; force `cmd` with `{"shell":{"windows_shell":"cmd"}}`)
— with the workspace as the working directory. So the agent can inspect the
system, drive git/builds, run scripts, and crunch files. The shell is
**persistent**: `cd`, env vars, and activated virtualenvs carry across calls. A new
session is health-probed and **falls back to one-shot automatically** if it's
unresponsive, so it can't hang. `system_info` gives a safe read-only summary
(OS, arch, CPU, cores, RAM) with no shell at all.

The file tools (`read_file`, `write_file`, `create_document`, `list_dir`) are
**not sandboxed** — they accept absolute, `~`, or relative paths and read/write
anywhere you can (e.g. drop a report in `~/Documents`), consistent with
`run_command`'s autonomy.

> **Autonomy & safety.** By default `run_command` runs with **full autonomy** — no
> per-command confirmation. But it's fully transparent: every command and its
> output appear inline, the tool is flagged `exec` (red) in the Tools panel, and a
> banner warns you on startup. To require review or shut it off, set
> `shell.enabled`/timeout in `config.local.json` (e.g. `{"shell":{"enabled":false}}`).
> Commands run with your privileges — treat the model accordingly.

**Hidden browser (opt-in) — the preferred way to do the web.** The model can drive
a **dedicated, headless Chromium off-screen** via Playwright — it never hijacks
your display and needs no Screen Recording permission. Tools: `browser_open`,
`browser_screenshot` (the rendered page, fed back so a vision model can *see* it),
`browser_click`, `browser_type`, `browser_key`.

- Install from **Install features → Hidden browser** (pip-installs Playwright *and*
  downloads Chromium), then flip the **Computer-use (browser)** toggle (or
  `{"browser":{"enabled":true}}`).
- Needs a vision+tools model; runs on a dedicated thread so it persists across
  turns. The model is told: `fetch_url` to *read* a page, the hidden browser for
  *interactive* tasks (login, forms, dynamic apps like Gmail).

**Desktop GUI (opt-in).** For tasks a shell can't do, the model can screenshot the
real desktop and click/type/press keys. It's **off by default** and only available
with a **vision-capable model** (it has to *see* the screen), and the model is told
to prefer the terminal. It takes two one-time opt-ins: install the backend
(**Install features → GUI computer-use**, pyautogui) and flip the **Computer-use
(GUI)** toggle.

- **macOS** needs **Screen Recording + Accessibility** for the *exact terminal app*
  that launches `oshell`. Without Screen Recording, macOS hands back wallpaper-only
  screenshots — so `screenshot` refuses with a clear message rather than feeding the
  model a blank image. Grant it, then fully restart the terminal. **Linux X11** works
  out of the box (Wayland is a planned native backend).
- After a turn that drove the desktop GUI, the model fires a desktop notification
  and re-focuses your terminal so you know it's done (`gui.notify_on_finish` /
  `gui.refocus_terminal`). A pyautogui failsafe (slam the mouse into a corner)
  aborts a runaway loop.

> If a toggle says "on" but no tools appear, the active model isn't vision-capable
> — pick one in **Models**. *Optional features* reflects whether a package is
> **installed**; **Active tools** is the truth for what the model can call now.

The control layer is a `Controller` abstraction (`oshell/gui/`) — pyautogui today,
with a clean seam for native backends (Wayland `grim`/`ydotool`, macOS
`screencapture`/`cliclick`).

## Optional extras

| Extra | Adds |
|-------|------|
| `tui` | The Textual workspace |
| `rag` | ChromaDB + sentence-transformers knowledge base |
| `finetune` | MLX-LM LoRA fine-tuning (Apple Silicon) |
| `docs` | Word / Excel / PDF / Markdown export |
| `vision` | Image analysis (Pillow) |
| `gui` | Desktop computer-use — screenshots + mouse/keyboard (pyautogui) |
| `browser` | Hidden-browser computer-use (Playwright; `playwright install chromium`) |
| `all` | everything above |

```bash
uv pip install -e ".[all]"     # …or just install them from the menu, live
```

## Fine-tuning (local LoRA)

On Apple Silicon, `oshell finetune` drives MLX-LM LoRA training; jobs are tracked
on disk under `~/.oshell/finetune`.

```bash
oshell finetune detect                                      # mlx / unsloth / cpu
oshell finetune create my-run -m <hf-model> -d data.jsonl   # prep + register
oshell finetune start <job-id>                              # launch mlx_lm.lora
oshell finetune status <job-id>                             # running/completed/failed
oshell finetune list
```

Datasets may be `.jsonl/.json/.csv/.tsv/.txt`; records are normalized to a
`{"text": …}` set (plain text / prompt+completion / chat-messages all work). Needs
the `finetune` extra (`mlx-lm`).

## Under the hood

```
oshell/
  config.py            Typed, layered config (defaults<config.json<config.local.json<env)
  capabilities.py      Reports which optional features/integrations are available
  mcp.py               MCP stdio client — mounts any MCP server's tools as native
                       (mechanic + drift ship configured by default)
  fun.py               Daydreams 💭 — motifs, grounding, prompt building, streaming
  providers/           LLMProvider abstraction
    base.py              Message / ToolCall / ChatChunk / LLMProvider
    ollama.py            Ollama REST + streaming (tool-aware)
    openai_compat.py     LM Studio / vLLM / llama.cpp / MLX (OpenAI schema)
  tools/               MCP-style host
    base.py              Tool + ToolRegistry (advertise specs, dispatch calls)
    builtins.py          current_time, list_models, read/write/list files (any path)
    system.py            run_command (cross-platform shell exec) + system_info
    web.py               web_search + fetch_url (core; flagged network-touching)
    documents.py         create_document — txt/md/csv/docx/xlsx/pdf (opt-in [docs])
    knowledge.py         add_knowledge + search_knowledge (opt-in [rag])
    memory.py            remember / recall / forget (always-on)
    gui.py               screenshot + gui_click/type/key/move (opt-in, vision-gated)
    browser.py           browser_open/screenshot/click/type/key (hidden, off-screen)
    atlassian.py         jira_search/get_issue + confluence_search/get_page (Server/DC)
  gui/controller.py      desktop-control backends (pyautogui; native seam)
  browser/controller.py  persistent Playwright browser on a dedicated thread
  desktop.py             notifications + terminal re-focus (after GUI turns)
  knowledge.py         KnowledgeBase: ChromaDB + sentence-transformers (lazy, on-disk, no telemetry)
  memory.py            MemoryStore: dependency-free JSON facts, injected + searchable
  integrations/
    atlassian.py         Jira/Confluence Server REST clients (reuse JIRA_*/CONFLUENCE_* env)
  finetune/            detect hardware, prep datasets, manage jobs, run mlx_lm.lora
  agent/
    loop.py              The loop: model drives multi-round tool-use; pin/exclude; promise-nudge
    events.py            TextDelta / ToolStarted / ToolFinished / TurnComplete / LimitReached
  cli.py               Thin Typer/Rich front-end
  tui/app.py           Textual workspace (Tools / Context / Activity tabs)
  tui/menu.py          Sectioned main menu + model / theme / feature pickers
  tui/ambient.py       Ambient effects: aurora, embers, fireflies, starfield,
                       sky weather, bursts, constellations, moods (1D + 2D)
  tui/overlay.py       The mood takeover — weather on top of the live workspace
  tui/dream.py         Dream Mode — the full-screen /daydream night sky
```

The agent loop emits a stream of **events**; the CLI and TUI are just renderers of
that stream. Swapping the backend is a one-line config change (`provider.name`),
because nothing above `providers/` knows which runtime it's talking to. The loop
also **nudges the model** when it announces an action but forgets to call the
tool, and **finalizes gracefully** if it hits the tool-round cap — so it never
leaves you hanging on a half-finished promise.

### Configuration

Resolved in increasing precedence: built-in defaults → `config.json` (committed,
shared) → `config.local.json` (per-machine, git-ignored) → `OSHELL_*` env vars
(use `__` for nesting, e.g. `OSHELL_PROVIDER__HOST`). See `.env.example`.

**Context window.** `context_length` defaults to `0` = **auto**: oshell asks
the backend for the model's trained maximum (Ollama `/api/show`) and runs with
that, capped at 32k so a 128k-context model doesn't allocate a monster KV cache
by surprise. The resolved size is passed to Ollama as `num_ctx` on every
request — without it, Ollama runs at *its* default (often 4k) and silently
truncates long conversations.

**Setting the maximum directly.** On capable hardware (a Mac Studio, a big-VRAM
GPU box), go past the auto cap by putting an explicit value in your
`config.local.json`:

```json
{
  "context_length": 65536
}
```

An explicit value always wins over auto — use it to go bigger (65536, 131072 —
mind the KV-cache memory: roughly, doubling the context doubles it) or smaller
(4096 to keep a modest machine snappy). The Context tab's gauge always shows
the size actually in effect: `▰▰▱▱▱ 23% of ~64k tokens`.

> v0.1 silently un-tracked `config.json` via a blanket `*.json` .gitignore rule.
> That's fixed: config is tracked; real secrets go in `.env` / `config.local.json`.

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
run locally since baselines are pinned to a Textual version); regenerate after
intentional layout changes with `make snapshot`.

## The great migration (complete)

The v0.1 monolith (`ollama_shell.py`) and all its sibling modules have been
**deleted**. Each capability was reimplemented as a clean, tested tool and verified
*before* its legacy source was removed:

| v0.1 module(s) | → v0.2 | Verified by |
|----------------|--------|-------------|
| `web_browsing` (extraction core) | `fetch_url` + `web_search` | live fetch of a real page |
| `file_creation` + `fixed_file_handler` | `create_document` tool | model wrote a real `.docx` |
| monolith `KnowledgeBase` | `oshell.knowledge` + `add/search_knowledge` | live semantic round-trip |
| `finetune.py` + `finetune_modules/` | `oshell.finetune` + `oshell finetune` | command verified vs real `mlx_lm.lora` |
| `*_mcp_integration` (Confluence/Jira) | `oshell.integrations.atlassian` + 4 tools | live read-only call to a real Server |

**Not carried over** (still in git history if ever needed): the standalone
filesystem-MCP server (its read/write/list operations are covered by the built-in
file tools), the `task_manager` to-do subsystem, and the Glama/`mcp_browser`
browser-automation integrations. Open an issue if you'd like any migrated next.

### Repository layout

| Path | What |
|------|------|
| `oshell/` | the entire application (core + tools + integrations + finetune + tui) |
| `tests/` | the test suite (`tests/legacy/` holds archived v0.1 scratch tests) |
| `examples/`, `scripts/` | relocated v0.1 demos and utilities |
| `docs/` | guides; `docs/LEGACY_README.md` + `docs/legacy/` preserve v0.1 docs |

## License

MIT. Built with care, and a little imagination, on local hardware.
