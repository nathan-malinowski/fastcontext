#!/bin/bash
# PreToolUse enforcer (Write|Edit): nudge Claude to run fastcontext before
# editing a code file that no trajectory from THIS session has cited.
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

# Session start time: prefer the birth time of the Claude Code transcript
# (transcript_path arrives in the hook input and is created when the session
# starts). Fall back to a stamp file created on this hook's first run for the
# session — later than true session start, so pre-edit explorations may be
# missed on that path, but only when transcript_path is absent.
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
start=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  start=$(stat -f %B "$transcript" 2>/dev/null || stat -c %W "$transcript" 2>/dev/null)
fi
case "$start" in ''|*[!0-9]*|0) start="" ;; esac
if [ -z "$start" ]; then
  stamp="${marker}.start"
  [ -f "$stamp" ] || : > "$stamp"
  start=$(stat -f %m "$stamp" 2>/dev/null || stat -c %Y "$stamp" 2>/dev/null)
fi

# Allow when a trajectory written during THIS session cites the file in its
# <final_answer> block, by absolute path or repo-relative path. Mentions
# elsewhere in the trajectory (tool output, directory listings) don't count,
# and neither do trajectories from earlier sessions. Basename alone is not
# enough: it would unlock every utils.py in the repo at once. Canonicalize
# the file path first — git returns real paths while tool input may use
# symlinked ones (e.g. /var vs /private/var on macOS).
file_dir=$(cd "$(dirname "$file")" 2>/dev/null && pwd -P) || file_dir=$(dirname "$file")
file_real="$file_dir/$(basename "$file")"
repo=$(git -C "$file_dir" rev-parse --show-toplevel 2>/dev/null)
dir="${repo:-$PWD}/.fastcontext"
[ -d "$dir" ] || dir="$PWD/.fastcontext"
if [ -d "$dir" ]; then
  # A citation is "<path>:<line...>" with nothing path-like immediately
  # before it. The left boundary keeps a bare basename from matching inside
  # a deeper path (mod.py vs src/mod.py, submod.py), so the repo-relative
  # form is safe to include even for root-level files. The trailing colon
  # requires an actual line-number citation, not a prose mention.
  esc() { printf '%s' "$1" | sed 's/[][\\^$.*+?(){}|]/\\&/g'; }
  rel="${file_real#"${repo:-$PWD}"/}"
  pats="$(esc "$file")|$(esc "$file_real")"
  [ "$rel" != "$file_real" ] && pats="$pats|$(esc "$rel")"
  cite_re="(^|[^A-Za-z0-9_./-])($pats):"
  for traj in "$dir"/*.jsonl; do
    [ -f "$traj" ] || continue
    mtime=$(stat -f %m "$traj" 2>/dev/null || stat -c %Y "$traj" 2>/dev/null)
    case "$mtime" in ''|*[!0-9]*) continue ;; esac
    [ "$mtime" -ge "$start" ] || continue
    # Keep only text inside <final_answer>...</final_answer>, splitting
    # mid-line so prose sharing a line with a tag stays excluded.
    if jq -r 'select(.role=="assistant") | .content // empty' "$traj" 2>/dev/null \
       | awk '{
           line = $0
           if (!f) {
             i = index(line, "<final_answer>")
             if (!i) next
             f = 1; line = substr(line, i + 14)
           }
           j = index(line, "</final_answer>")
           if (j) { print substr(line, 1, j - 1); f = 0 } else print line
         }' \
       | grep -qsE "$cite_re"; then
      echo "$file" >> "$marker"
      exit 0
    fi
  done
fi

# Allow when the FastContext endpoint is down -- exploration is impossible
# anyway. Mirror normalize_base_url: add a scheme if missing, append /v1 only
# to a bare server root, then probe the OpenAI-compatible models endpoint.
endpoint_up() {
  if [ -n "$FC_BASE_URL" ]; then
    b="${FC_BASE_URL%/}"
    case "$b" in *://*) : ;; *) b="http://$b" ;; esac
    case "${b#*://}" in */*) : ;; *) b="$b/v1" ;; esac
    curl -s --max-time 2 "$b/models" >/dev/null 2>&1
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
