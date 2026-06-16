"""oshell — a local-first, agentic shell for Ollama.

This package is the *reimagined* core of Ollama Shell. Its design goals:

1. **Local-first / privacy-native** — nothing leaves the machine unless a tool
   explicitly reaches the network, and those tools are auditable.
2. **Agent loop as the shell** — capabilities are *tools* the model can call
   (an MCP-style host), not features bolted onto a chat REPL.
3. **Light core, opt-in power** — the base install is tiny; heavy features
   (web, RAG, fine-tuning, docs export) are optional extras.

The original 4,600-line monolith (``ollama_shell.py``) and its feature modules
have been fully retired: every capability now lives in this package, and the
old code is preserved only in git history and ``docs/LEGACY_README.md``.
See README.md.
"""

__version__ = "0.2.0"

__all__ = ["__version__"]
