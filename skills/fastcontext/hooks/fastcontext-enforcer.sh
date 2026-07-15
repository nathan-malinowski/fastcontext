#!/bin/bash
# PreToolUse enforcer (Write|Edit): nudge Claude to run fastcontext before
# editing a code file that no trajectory in this repo has touched yet.
# Fires at most once per file per session, and only when the FastContext
# endpoint is actually reachable.
#
# Note: hooks run in Claude Code's own environment. For a non-default
# endpoint (e.g. Ollama), FC_BASE_URL must be set there — via settings.json
# "env" or the shell that launched Claude Code — not just inside agent
# commands. The two common local defaults are probed as a fallback.

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
session=$(printf '%s' "$input" | jq -r '.session_id // "nosession"')

[ -z "$file" ] && exit 0        # no file path -> allow
[ -f "$file" ] || exit 0        # new file -> allow (nothing to explore)

case "$file" in
  */.fastcontext/*) exit 0 ;;   # never gate trajectory files themselves
  *.py|*.js|*.ts|*.tsx|*.jsx|*.go|*.rs|*.java|*.c|*.h|*.cpp|*.hpp|*.cc|*.rb|*.php|*.cs|*.swift|*.kt|*.scala|*.sh) ;;
  *) exit 0 ;;                  # non-code file -> allow
esac

# One resolution per file per session: covers both "already nudged" and
# "already checked and allowed", so repeat edits skip the expensive path.
marker="${TMPDIR:-/tmp}/claude-fc-enforcer-${session}"
if [ -f "$marker" ] && grep -qxF "$file" "$marker"; then
  exit 0
fi

# Allow when any trajectory in the file's repo (or CWD) already mentions the
# file, by absolute path or repo-relative path. Basename alone is not enough:
# it would unlock every utils.py in the repo at once.
repo=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null)
dir="${repo:-$PWD}/.fastcontext"
[ -d "$dir" ] || dir="$PWD/.fastcontext"
if [ -d "$dir" ]; then
  if grep -rqsF "$file" "$dir" 2>/dev/null; then
    echo "$file" >> "$marker"
    exit 0
  fi
  rel="${file#"${repo:-$PWD}"/}"
  if [ "$rel" != "$file" ] && grep -rqsF "$rel" "$dir" 2>/dev/null; then
    echo "$file" >> "$marker"
    exit 0
  fi
fi

# Allow when the FastContext endpoint is down -- exploration is impossible
# anyway. Strip a trailing /v1 so README-style FC_BASE_URL values work.
endpoint_up() {
  if [ -n "$FC_BASE_URL" ]; then
    b="${FC_BASE_URL%/}"; b="${b%/v1}"
    curl -s --max-time 1 "$b/v1/models" >/dev/null 2>&1
  else
    curl -s --max-time 1 "http://localhost:1234/v1/models" >/dev/null 2>&1 ||
      curl -s --max-time 1 "http://localhost:11434/v1/models" >/dev/null 2>&1
  fi
}
endpoint_up || exit 0

echo "$file" >> "$marker"
base=$(basename "$file")
reason="fastcontext enforcer: $base has not been explored this session. Use the fastcontext skill first (export FC_MODEL/FC_BASE_URL, then: fastcontext -q '<focused question about this area>' --max-turns 8 --citation from the repo root), then retry the edit. This gate fires once per file."
jq -cn --arg reason "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
exit 0
