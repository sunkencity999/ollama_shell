"""install.sh: the shell hook is idempotent and shell-aware; --dry-run changes nothing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "install.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _hook(shell: str, home: Path) -> subprocess.CompletedProcess:
    """Extract just the hook function from install.sh into a file and run it for ``shell``.

    (A temp file rather than `source <(…)`: process substitution isn't reliable
    under the stripped-down environment these tests run bash with.)
    """
    fn = home.parent / "hook.sh"
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index("MARKER=")
    end = text.index("\n}\n", start) + 3
    fn.write_text(text[start:end], encoding="utf-8")
    snippet = (
        f'source "{fn}"; '
        f'DRY_RUN=0 SHELL={shell} HOME="{home}" ZDOTDIR= XDG_CONFIG_HOME= install_shell_hook'
    )
    return subprocess.run(
        ["bash", "-c", snippet], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}
    )


def test_install_sh_parses():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


@pytest.mark.parametrize(
    "shell, rc, line",
    [
        ("/bin/zsh", ".zshrc", 'eval "$(oshell init zsh)"'),
        ("/bin/bash", ".bashrc", 'eval "$(oshell init bash)"'),
        ("/usr/bin/fish", ".config/fish/config.fish", "oshell init fish | source"),
    ],
)
def test_shell_hook_is_appended_once(tmp_path, shell, rc, line):
    home = tmp_path / "hookhome"  # conftest already owns tmp_path/home
    home.mkdir()
    r = _hook(shell, home)
    assert r.returncode == 0, r.stderr
    rc_path = home / rc
    text = rc_path.read_text()
    assert "# oshell shell integration" in text and line in text
    assert "command -v oshell" in text  # guarded: a missing binary never breaks the shell
    # Re-running finds the marker and leaves the file alone.
    r2 = _hook(shell, home)
    assert "already" in r2.stdout
    assert rc_path.read_text() == text


def test_unknown_shell_is_skipped_gracefully(tmp_path):
    home = tmp_path / "hookhome"  # conftest already owns tmp_path/home
    home.mkdir()
    r = _hook("/bin/tcsh", home)
    assert r.returncode == 0 and "isn't one I know" in r.stdout
    assert not list(home.iterdir())


def test_dry_run_prints_every_step_and_writes_nothing(tmp_path):
    home = tmp_path / "hookhome"  # conftest already owns tmp_path/home
    home.mkdir()
    r = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", "--no-monitors"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(home),
            "SHELL": "/bin/zsh",
        },
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    for step in ("shell integration", "theme set", "jobs install", "orders install", "Try it"):
        assert step in out, step
    assert not (home / ".zshrc").exists()  # dry run: nothing written
    assert not (home / ".oshell").exists()
