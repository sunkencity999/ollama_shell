"""Drift digest: real changes counted, Spotlight churn ignored, quiet is None."""

from __future__ import annotations

import json

from oshell.digest import summarize_drift


def _payload(diff):
    return json.dumps({"ok": True, "diff": diff, "summary": "..."})


def test_counts_nested_categories():
    raw = _payload(
        {
            "services": {"labels": {"added": ["com.utm.UTM"], "removed": []}},
            "ports": {"added": [8080, 5432], "removed": [3000]},
        }
    )
    assert summarize_drift(raw) == "ports +2/−1, services +1"


def test_spotlight_churn_is_ignored():
    raw = _payload(
        {
            "services": {
                "labels": {
                    "added": ["com.apple.mdworker.shared.09000000", "real.daemon"],
                    "removed": ["com.apple.mdworker.shared.1E000000"],
                }
            }
        }
    )
    assert summarize_drift(raw) == "services +1"


def test_quiet_night_and_bad_payloads_are_none():
    assert summarize_drift(_payload({})) is None
    assert summarize_drift(_payload({"services": {"added": [], "removed": []}})) is None
    only_noise = _payload({"services": {"added": ["com.apple.mdworker.x"], "removed": []}})
    assert summarize_drift(only_noise) is None
    assert summarize_drift("not json") is None
    assert summarize_drift(json.dumps({"ok": False, "diff": {"x": {"added": [1]}}})) is None
