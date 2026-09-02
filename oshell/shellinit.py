"""Shell integration snippets: ``eval "$(oshell init zsh)"`` (also bash, fish,
and PowerShell: ``oshell init powershell | Out-String | Invoke-Expression``).

What the snippet gives your shell — the bits that made shell_gpt feel like
part of the OS rather than an app you open:

* **Ctrl+G** — with text on the line, ask oshell about it. Start the line
  with ``#`` and the *same key* turns the comment into a command, placed on
  your line to edit or run (nothing executes until you press Enter):
  ``# find files over 1g modified this week`` ⏎? No — Ctrl+G → the command.
* **Last-command capture** — a tiny post-command hook writes the command,
  its exit status, and the directory to ``~/.oshell/last_cmd`` (pure shell,
  no process spawn), so ``oshell fix`` can explain whatever just failed and
  ``oshell explain`` with no argument describes what you just ran.
* **command-not-found** — a nudge toward ``oshell do`` instead of a dead end.
* **Theme colors** — sources ``~/.oshell/current/colors.sh`` if present, so
  ``$OSHELL_ACCENT`` & co. are available to your prompt; ``--prompt`` adds a
  small themed two-segment prompt for those who want the full rice.
"""

from __future__ import annotations

SHELLS = ("zsh", "bash", "fish", "powershell")

_ZSH = r"""# oshell shell integration — add to ~/.zshrc:  eval "$(oshell init zsh)"
[[ -r "$HOME/.oshell/current/colors.sh" ]] && source "$HOME/.oshell/current/colors.sh"

# Ctrl+G: ask oshell about what's on your line; empty line -> interactive chat.
# A line starting with '#' is a request for a *command*: it is replaced in
# place with the proposal (nothing runs until you press Enter).
_oshell_widget() {
  local q="$BUFFER"
  if [[ "$q" == \#* ]]; then
    local cmd
    cmd="$(oshell do --print -- "${q#\#}" 2>/dev/null </dev/tty)"
    if [[ -n "$cmd" ]]; then
      BUFFER="$cmd"; CURSOR=${#BUFFER}
    fi
    zle reset-prompt
    return
  fi
  BUFFER=""
  zle -I
  if [[ -n "$q" ]]; then
    oshell ask "$q" </dev/tty
  else
    oshell </dev/tty
  fi
  zle reset-prompt
}
zle -N _oshell_widget
bindkey '^G' _oshell_widget

# Remember the last command + exit status for `oshell fix` / `oshell explain`.
_oshell_preexec() { _OSHELL_LAST_CMD="$1"; }
_oshell_precmd() {
  local rc=$?
  [[ -n "$_OSHELL_LAST_CMD" ]] || return 0
  mkdir -p "$HOME/.oshell" 2>/dev/null
  {
    print -r -- "$rc"
    print -r -- "$PWD"
    print -r -- "${EPOCHSECONDS:-0}"
    print -r -- "$_OSHELL_LAST_CMD"
  } > "$HOME/.oshell/last_cmd.tmp" 2>/dev/null && mv -f "$HOME/.oshell/last_cmd.tmp" "$HOME/.oshell/last_cmd" 2>/dev/null
  _OSHELL_LAST_CMD=""
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec _oshell_preexec
add-zsh-hook precmd _oshell_precmd

# Unknown command? Point at the assistant instead of a dead end.
command_not_found_handler() {
  echo "zsh: command not found: $1" >&2
  echo "  ↳ try: oshell do \"$*\"   (or: oshell fix)" >&2
  return 127
}
"""

_ZSH_PROMPT = r"""
# A small themed prompt (oshell init zsh --prompt). Uses the current theme's
# colors when ~/.oshell/current/colors.sh exists; falls back to plain cyan.
setopt PROMPT_SUBST
_oshell_prompt_color() { print -n "%F{${1:-cyan}}"; }
_oshell_git() {
  local b; b="$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)" || return
  print -n " %F{${OSHELL_MAGENTA:-magenta}} $b%f"
}
PROMPT='%F{${OSHELL_ACCENT:-cyan}}%B%~%b%f$(_oshell_git) %(?.%F{${OSHELL_GREEN:-green}}.%F{${OSHELL_RED:-red}})❯%f '
RPROMPT='%F{${OSHELL_DARK_FOREGROUND:-8}}${OSHELL_THEME:-}%f'
"""

_BASH = r"""# oshell shell integration — add to ~/.bashrc:  eval "$(oshell init bash)"
[[ -r "$HOME/.oshell/current/colors.sh" ]] && source "$HOME/.oshell/current/colors.sh"

# Ctrl+G: ask oshell about what's on your line; '#…' lines become a command
# placed back on the line to edit or run; an empty line opens chat.
_oshell_widget() {
  local q="$READLINE_LINE"
  if [[ "$q" == \#* ]]; then
    local cmd
    cmd="$(oshell do --print -- "${q#\#}" 2>/dev/null </dev/tty)"
    [[ -n "$cmd" ]] && { READLINE_LINE="$cmd"; READLINE_POINT=${#READLINE_LINE}; }
    return
  fi
  READLINE_LINE=""; READLINE_POINT=0
  if [[ -n "$q" ]]; then oshell ask "$q" </dev/tty; else oshell </dev/tty; fi
}
bind -x '"\C-g": _oshell_widget'

# Remember the last command + exit status for `oshell fix` / `oshell explain`.
_oshell_precmd() {
  local rc=$? last
  last="$(HISTTIMEFORMAT= history 1 | sed 's/^ *[0-9]* *//')"
  [[ -n "$last" && "$last" != "$_OSHELL_SEEN" ]] || return 0
  _OSHELL_SEEN="$last"
  mkdir -p "$HOME/.oshell" 2>/dev/null
  printf '%s\n%s\n%s\n%s\n' "$rc" "$PWD" "$(date +%s)" "$last" > "$HOME/.oshell/last_cmd.tmp" \
    && mv -f "$HOME/.oshell/last_cmd.tmp" "$HOME/.oshell/last_cmd"
}
case ";$PROMPT_COMMAND;" in *";_oshell_precmd;"*) ;; *) PROMPT_COMMAND="_oshell_precmd${PROMPT_COMMAND:+;$PROMPT_COMMAND}";; esac

command_not_found_handle() {
  echo "bash: command not found: $1" >&2
  echo "  ↳ try: oshell do \"$*\"   (or: oshell fix)" >&2
  return 127
}
"""

_BASH_PROMPT = r"""
# A small themed prompt (oshell init bash --prompt).
_oshell_ps1() {
  local rc=$? a="${OSHELL_ACCENT:-#56b6c2}" g="${OSHELL_GREEN:-#98c379}" r="${OSHELL_RED:-#e06c75}"
  local c; if (( rc == 0 )); then c="$g"; else c="$r"; fi
  printf '\[\e[1m\e[38;2;%d;%d;%dm\]\w\[\e[0m\] \[\e[38;2;%d;%d;%dm\]❯\[\e[0m\] ' \
    $((16#${a:1:2})) $((16#${a:3:2})) $((16#${a:5:2})) \
    $((16#${c:1:2})) $((16#${c:3:2})) $((16#${c:5:2}))
}
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}"'PS1="$(_oshell_ps1)"'
"""

_FISH = r"""# oshell shell integration — add to ~/.config/fish/config.fish:  oshell init fish | source
if test -r "$HOME/.oshell/current/colors.sh"
    for line in (grep '^OSHELL_' "$HOME/.oshell/current/colors.sh")
        set -l kv (string split -m1 '=' -- $line)
        set -gx $kv[1] (string trim -c '"' -- $kv[2])
    end
end

# Ctrl+G: ask oshell about what's on your line; '#…' becomes a command placed
# back on the line; an empty line opens chat.
function _oshell_widget
    set -l q (commandline)
    if string match -q '#*' -- "$q"
        set -l cmd (oshell do --print -- (string sub -s 2 -- "$q") 2>/dev/null </dev/tty)
        if test -n "$cmd"
            commandline -r -- "$cmd"
        end
        commandline -f repaint
        return
    end
    commandline -r ""
    if test -n "$q"
        oshell ask "$q" </dev/tty
    else
        oshell </dev/tty
    end
    commandline -f repaint
end
bind \cg _oshell_widget

# Remember the last command + exit status for `oshell fix` / `oshell explain`.
function _oshell_postexec --on-event fish_postexec
    set -l rc $status
    mkdir -p "$HOME/.oshell" 2>/dev/null
    printf '%s\n%s\n%s\n%s\n' $rc $PWD (date +%s) "$argv" > "$HOME/.oshell/last_cmd.tmp"
    and mv -f "$HOME/.oshell/last_cmd.tmp" "$HOME/.oshell/last_cmd"
end

function fish_command_not_found
    echo "fish: command not found: $argv[1]" >&2
    echo "  ↳ try: oshell do \"$argv\"   (or: oshell fix)" >&2
end
"""

_FISH_PROMPT = r"""
# A small themed prompt (oshell init fish --prompt).
function fish_prompt
    set -l rc $status
    set_color -o (string replace '#' '' -- (set -q OSHELL_ACCENT; and echo $OSHELL_ACCENT; or echo 56b6c2))
    echo -n (prompt_pwd)
    set_color normal
    if test $rc -eq 0
        set_color (string replace '#' '' -- (set -q OSHELL_GREEN; and echo $OSHELL_GREEN; or echo 98c379))
    else
        set_color (string replace '#' '' -- (set -q OSHELL_RED; and echo $OSHELL_RED; or echo e06c75))
    end
    echo -n ' ❯ '
    set_color normal
end
"""

_PS = r"""# oshell shell integration — add to $PROFILE:  oshell init powershell | Out-String | Invoke-Expression
# Theme colors from the current theme (written by `oshell theme set`).
$__oshellColors = Join-Path $HOME ".oshell/current/colors.sh"
if (Test-Path $__oshellColors) {
  Get-Content $__oshellColors | ForEach-Object {
    if ($_ -match '^(OSHELL_\w+)="([^"]*)"') { Set-Item -Path ("env:" + $Matches[1]) -Value $Matches[2] }
  }
}

# Ctrl+G: ask oshell about what's on your line; a line starting with '#' is a
# request for a *command*: it is replaced in place with the proposal (nothing
# runs until you press Enter); an empty line opens chat.
Set-PSReadLineKeyHandler -Chord Ctrl+g -ScriptBlock {
  $line = $null; $cursor = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
  if ($line -like '#*') {
    $cmd = (& oshell do --print -- $line.Substring(1).Trim() 2>$null) -join "`n"
    if ($cmd) { [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $line.Length, $cmd) }
    return
  }
  [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
  if ($line) { & oshell ask $line } else { & oshell }
  [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
}

# Remember the last command + exit status for `oshell fix` / `oshell explain`.
function global:_oshell_record([bool]$ok) {
  $h = Get-History -Count 1
  if (-not $h -or $h.Id -eq $global:__oshellSeen) { return }
  $global:__oshellSeen = $h.Id
  $rc = if ($ok) { 0 } elseif ($global:LASTEXITCODE) { $global:LASTEXITCODE } else { 1 }
  $dir = Join-Path $HOME ".oshell"
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $epoch = [int][double]::Parse((Get-Date -UFormat %s))
  Set-Content -Path (Join-Path $dir "last_cmd") -Value @("$rc", "$PWD", "$epoch", $h.CommandLine) -Encoding utf8
}
if (-not $global:__oshellPrevPrompt) { $global:__oshellPrevPrompt = $function:prompt }
function global:prompt {
  $ok = $?
  _oshell_record $ok
  & $global:__oshellPrevPrompt
}

# Unknown command? Point at the assistant instead of a dead end.
$ExecutionContext.InvokeCommand.CommandNotFoundAction = {
  param($name, $eventArgs)
  [Console]::Error.WriteLine("powershell: command not found: $name")
  [Console]::Error.WriteLine("  ↳ try: oshell do `"$name`"   (or: oshell fix)")
}
"""

_PS_PROMPT = r"""
# A small themed prompt (oshell init powershell --prompt).
function global:_oshell_rgb([string]$hex, [string]$fallback) {
  if (-not $hex) { $hex = $fallback }
  $r = [Convert]::ToInt32($hex.Substring(1,2),16); $g = [Convert]::ToInt32($hex.Substring(3,2),16); $b = [Convert]::ToInt32($hex.Substring(5,2),16)
  return "$([char]27)[38;2;$r;$g;$($b)m"
}
function global:prompt {
  $ok = $?
  _oshell_record $ok
  $reset = "$([char]27)[0m"
  $accent = _oshell_rgb $env:OSHELL_ACCENT '#56b6c2'
  $mark = if ($ok) { _oshell_rgb $env:OSHELL_GREEN '#98c379' } else { _oshell_rgb $env:OSHELL_RED '#e06c75' }
  $here = (Get-Location).Path.Replace($HOME, '~')
  "$accent$([char]27)[1m$here$reset $mark❯$reset "
}
"""

_SNIPPETS = {
    "zsh": (_ZSH, _ZSH_PROMPT),
    "bash": (_BASH, _BASH_PROMPT),
    "fish": (_FISH, _FISH_PROMPT),
    "powershell": (_PS, _PS_PROMPT),
    "pwsh": (_PS, _PS_PROMPT),
}


def snippet(shell: str, prompt: bool = False) -> str:
    """The integration script for ``shell`` (zsh | bash | fish)."""
    if shell not in _SNIPPETS:
        raise ValueError(f"unsupported shell {shell!r} (supported: {', '.join(SHELLS)})")
    base, themed_prompt = _SNIPPETS[shell]
    return base + (themed_prompt if prompt else "")
