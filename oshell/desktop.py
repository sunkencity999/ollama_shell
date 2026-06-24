"""Cross-platform desktop niceties: notifications and terminal re-focus.

Used after a GUI turn so the user knows the agent is done even if focus moved to
another app, and to bring their terminal back to the front. All best-effort and
never raise — they shell out to the platform's native tools.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

# How TERM_PROGRAM (set by macOS terminals) maps to an app name for `activate`.
_MAC_TERM_APPS = {
    "iTerm.app": "iTerm",
    "Apple_Terminal": "Terminal",
    "WezTerm": "WezTerm",
    "ghostty": "Ghostty",
    "vscode": "Code",
}


def notify(title: str, message: str) -> bool:
    """Show a desktop notification. Returns True if it was dispatched."""
    system = platform.system().lower()
    try:
        if system == "darwin":
            safe = message.replace('"', "'")
            tsafe = title.replace('"', "'")
            subprocess.run(
                ["osascript", "-e", f'display notification "{safe}" with title "{tsafe}"'],
                check=True,
                timeout=5,
            )
            return True
        if system == "linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=True, timeout=5)
            return True
        if system == "windows" and shutil.which("powershell"):
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager,"
                "Windows.UI.Notifications,ContentType=WindowsRuntime] | Out-Null; "
                f"Write-Host '{message}'"  # minimal; full toast needs BurntToast
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=5)
            return True
    except Exception:
        return False
    return False


def focus_terminal() -> bool:
    """Bring the launching terminal back to the front (best-effort)."""
    system = platform.system().lower()
    try:
        if system == "darwin":
            app = _MAC_TERM_APPS.get(os.environ.get("TERM_PROGRAM", ""))
            if not app:
                return False
            subprocess.run(
                ["osascript", "-e", f'tell application "{app}" to activate'],
                check=True,
                timeout=5,
            )
            return True
        if system == "linux" and shutil.which("wmctrl") and os.environ.get("WINDOWID"):
            subprocess.run(["wmctrl", "-ia", os.environ["WINDOWID"]], timeout=5)
            return True
    except Exception:
        return False
    return False
