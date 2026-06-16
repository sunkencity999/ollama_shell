"""Normalize arbitrary datasets into a framework-ready training directory.

Input formats: ``.jsonl`` / ``.json`` (records), ``.csv`` / ``.tsv`` (rows),
``.txt`` (lines). Every record is reduced to a single ``{"text": ...}`` example
— the lowest common denominator both MLX-LM and Unsloth accept — using these
rules, in order:

    {"text": "..."}                         -> used as-is
    {"prompt": "...", "completion": "..."}   -> "<prompt>\n<completion>"
    {"messages": [{role, content}, ...]}     -> "ROLE: content" lines (chat)
    csv/tsv row                              -> a "text" column if present,
                                                else all cells joined by space
    txt line                                 -> the line itself

For MLX it writes ``train.jsonl`` + ``valid.jsonl`` (a small holdout); for
Unsloth it writes ``train.json`` (a list). Returns the output directory.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


class DatasetError(RuntimeError):
    """Raised for missing files or unsupported/empty datasets."""


def _record_to_text(rec: dict) -> str | None:
    if "text" in rec and isinstance(rec["text"], str):
        return rec["text"]
    if "prompt" in rec and "completion" in rec:
        return f"{rec['prompt']}\n{rec['completion']}"
    if "messages" in rec and isinstance(rec["messages"], list):
        lines = [
            f"{m.get('role', '')}: {m.get('content', '')}".strip()
            for m in rec["messages"]
            if m.get("content")
        ]
        return "\n".join(lines) if lines else None
    return None


def _load_records(src: Path) -> list[str]:
    """Read the source file into a list of training `text` strings."""
    suffix = src.suffix.lower()
    texts: list[str] = []

    if suffix == ".jsonl":
        for line in src.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = _record_to_text(rec) if isinstance(rec, dict) else str(rec)
            if t:
                texts.append(t)
    elif suffix == ".json":
        data = json.loads(src.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("data", [])
        for rec in items:
            t = _record_to_text(rec) if isinstance(rec, dict) else str(rec)
            if t:
                texts.append(t)
    elif suffix in (".csv", ".tsv"):
        delim = "\t" if suffix == ".tsv" else ","
        rows = list(csv.DictReader(src.read_text(encoding="utf-8").splitlines(), delimiter=delim))
        for row in rows:
            texts.append(row.get("text") or " ".join(str(v) for v in row.values() if v))
    elif suffix == ".txt":
        texts = [ln.strip() for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        raise DatasetError(f"unsupported dataset format: {suffix} (use jsonl/json/csv/tsv/txt)")

    if not texts:
        raise DatasetError("no usable records found in dataset")
    return texts


def prepare_dataset(dataset_path: str, output_dir: str, framework: str = "mlx") -> str:
    """Convert ``dataset_path`` into a training dir under ``output_dir``."""
    src = Path(dataset_path).expanduser()
    if not src.is_file():
        raise DatasetError(f"dataset not found: {dataset_path}")
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    texts = _load_records(src)

    if framework == "unsloth":
        (out / "train.json").write_text(
            json.dumps([{"text": t} for t in texts], indent=2), encoding="utf-8"
        )
        return str(out)

    # MLX (default): jsonl with a small validation holdout.
    split = max(1, len(texts) // 10) if len(texts) > 1 else 0
    valid, train = (texts[:split], texts[split:]) if split else (texts, texts)
    _write_jsonl(out / "train.jsonl", train)
    _write_jsonl(out / "valid.jsonl", valid)
    return str(out)


def _write_jsonl(path: Path, texts: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for t in texts:
            f.write(json.dumps({"text": t}) + "\n")
