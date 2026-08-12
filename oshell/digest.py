"""Morning drift digest: one calm line about what changed overnight.

Drift's ``diff_latest`` returns structured JSON (categories → added/removed
lists) plus prose. We compress that into a single glanceable line for the TUI's
once-a-day digest — counting real changes and ignoring churn that flaps on
every macOS snapshot and means nothing (Spotlight's mdworker fleet).
"""

from __future__ import annotations

import json

_NOISE_PREFIXES = ("com.apple.mdworker",)


def _noisy(item: object) -> bool:
    return isinstance(item, str) and item.startswith(_NOISE_PREFIXES)


def _walk(node: object) -> tuple[int, int]:
    """Count (added, removed) leaves anywhere under a diff category."""
    added = removed = 0
    if isinstance(node, dict):
        for key, val in node.items():
            if key in ("added", "removed") and isinstance(val, list):
                n = sum(1 for v in val if not _noisy(v))
                if key == "added":
                    added += n
                else:
                    removed += n
            else:
                a, r = _walk(val)
                added += a
                removed += r
    return added, removed


def summarize_drift(raw: str) -> str | None:
    """A one-line digest ("services +1, ports +2/−1"), or None for a quiet night."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict) or not data.get("ok"):
        return None
    parts = []
    for category, node in sorted((data.get("diff") or {}).items()):
        added, removed = _walk(node)
        bits = ([f"+{added}"] if added else []) + ([f"−{removed}"] if removed else [])
        if bits:
            parts.append(f"{category} {'/'.join(bits)}")
    return ", ".join(parts) or None
