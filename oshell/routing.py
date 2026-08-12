"""Automatic model routing: the right local model for each message.

Local inference's biggest UX tax is model choice — an 31B model is wasted on
"thanks!" and a 4B model butchers "prove this invariant holds". When routing is
enabled, oshell picks per message and tells the user it switched. Heuristics
only, deliberately: a classifier model would cost the latency we're saving.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

# Signals that a message deserves the deep model. Kept coarse — the cost of a
# wrong "deep" pick is latency, the cost of a wrong "fast" pick is a bad answer,
# so ties break toward deep.
_DEEP_HINTS = re.compile(
    r"\b(explain why|analyze|analyse|architect|design|debug|refactor|prove|"
    r"optimi[sz]e|step[- ]by[- ]step|trade[- ]?offs?|root cause|deep dive|"
    r"security|vulnerabilit|algorithm|complexit|write (a |an )?(script|program|parser)|"
    r"implement)\b",
    re.IGNORECASE,
)
_CODE_FENCE = re.compile(r"```|\bdef |\bclass |\bfunction\b|=>|::")
_DEEP_LENGTH = 600  # chars of prompt (or pasted context) that imply real work


class RoutingConfig(BaseModel):
    """Which model handles what. Empty slots fall back to the current model."""

    enabled: bool = False
    fast_model: str = ""  # quick chat, small questions
    deep_model: str = ""  # reasoning, code, long context
    vision_model: str = ""  # any turn with images attached


def classify(text: str, has_images: bool = False) -> str:
    """Bucket a message: 'vision' | 'deep' | 'fast'."""
    if has_images:
        return "vision"
    if len(text) >= _DEEP_LENGTH or _CODE_FENCE.search(text) or _DEEP_HINTS.search(text):
        return "deep"
    return "fast"


def pick_model(
    text: str,
    has_images: bool,
    cfg: RoutingConfig,
    current: str,
) -> tuple[str, str] | None:
    """The (model, reason) to switch to for this message, or None to stay put."""
    if not cfg.enabled:
        return None
    bucket = classify(text, has_images)
    target = {
        "vision": cfg.vision_model,
        "deep": cfg.deep_model,
        "fast": cfg.fast_model,
    }[bucket]
    if not target or target == current:
        return None
    reasons = {
        "vision": "image attached",
        "deep": "this one deserves the big model",
        "fast": "quick question, fast model",
    }
    return target, reasons[bucket]
