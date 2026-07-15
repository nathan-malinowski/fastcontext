#!/bin/bash
# PreToolUse enforcer (Write|Edit): nudge Claude to run fastcontext before
# editing a code file that no trajectory in this repo has touched yet.
# Fires at most once per file per session, and only when the FastContext
# endpoint is actually reachable.

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

marker="${TMPDIR:-/tmp}/claude-fc-enforcer-${session}"
if [ -f "$marker" ] && grep -qxF "$file" "$marker"; then
  exit 0                        # already nudged once for this file this session
fi

# Allow when the FastContext endpoint is down -- exploration is impossible anyway.
curl -s --max-time 1 "${FC_BASE_URL:-http://localhost:1234}/v1/models" >/dev/null 2>&1 || exit 0

# Allow when any trajectory in the file's repo (or CWD) already mentions the file.
base=$(basename "$file")
repo=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null)
for dir in "$repo/.fastcontext" "$PWD/.fastcontext"; do
  [ -d "$dir" ] && grep -rqsF "$base" "$dir" 2>/dev/null && exit 0
done

echo "$file" >> "$marker"
reason="fastcontext enforcer: $base has not been explored this session. Use the fastcontext skill first (export FC_MODEL/FC_BASE_URL, then: fastcontext -q '<focused question about this area>' --max-turns 8 --citation from the repo root), then retry the edit. This gate fires once per file."
jq -cn --arg reason "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
exit 0
