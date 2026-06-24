"""Document-export tool — the clean successor to legacy ``file_creation.py``.

One ``create_document`` tool writes a file in a format chosen by its extension:
``.txt`` / ``.md`` (core), and ``.csv`` / ``.docx`` / ``.xlsx`` / ``.pdf``
(``[docs]`` extra). It is workspace-sandboxed like the other filesystem tools,
so the model cannot write outside the working directory — an improvement over
the legacy code, which always dumped into a top-level ``Created Files/`` dir.

Each rich format degrades to an actionable ``ToolError`` when its optional
dependency is missing, so the agent can tell the user what to install.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from .base import ToolError
from .builtins import _PathTool

# Extensions handled with no extra dependency.
_PLAINTEXT = {"txt", "md", "markdown", "text"}


class CreateDocumentTool(_PathTool):
    name = "create_document"
    description = (
        "Create a document at any path on the system. The file extension picks the "
        "format: txt/md (plain), csv (rows), docx (Word), xlsx (Excel from CSV text), "
        "pdf. For csv/xlsx, pass CSV-formatted text as content."
    )
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Destination — absolute, ~, or relative to the working dir "
                "(extension sets the format)",
            },
            "content": {
                "type": "string",
                "description": "Document body. For csv/xlsx, supply CSV-formatted text.",
            },
        },
        "required": ["path", "content"],
    }

    def run(self, path: str = "", content: str = "", **_: Any) -> str:
        if "." not in path:
            raise ToolError("path needs an extension (e.g. .txt, .md, .csv, .docx, .xlsx, .pdf)")
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        ext = path.rsplit(".", 1)[-1].lower()

        if ext in _PLAINTEXT or ext == "csv":
            target.write_text(content, encoding="utf-8")
        elif ext in ("doc", "docx"):
            _write_docx(target, content)
        elif ext in ("xls", "xlsx"):
            _write_xlsx(target, content)
        elif ext == "pdf":
            _write_pdf(target, content)
        else:
            raise ToolError(f"unsupported extension: .{ext}")

        return f"created {ext} document: {self._display(target)} ({len(content)} bytes of source)"


def _write_docx(target, content: str) -> None:
    try:
        import docx  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via extras
        raise ToolError("docx needs the 'docs' extra: pip install 'ollama-shell[docs]'") from exc
    doc = docx.Document()
    for para in content.split("\n\n"):  # blank line => new paragraph
        if para.strip():
            doc.add_paragraph(para)
    doc.save(str(target))


def _write_xlsx(target, content: str) -> None:
    try:
        from openpyxl import Workbook  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via extras
        raise ToolError("xlsx needs the 'docs' extra: pip install 'ollama-shell[docs]'") from exc
    wb = Workbook()
    ws = wb.active
    for row in csv.reader(io.StringIO(content)):  # stdlib csv — no pandas needed
        ws.append(row)
    wb.save(str(target))


def _write_pdf(target, content: str) -> None:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via extras
        raise ToolError("pdf needs the 'docs' extra: pip install 'ollama-shell[docs]'") from exc
    from html import escape

    html = f"<html><body><pre>{escape(content)}</pre></body></html>"
    HTML(string=html).write_pdf(str(target))
