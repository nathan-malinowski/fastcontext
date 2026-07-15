import { execFileSync } from "node:child_process";
import { closeSync, existsSync, openSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join, resolve } from "node:path";

// OpenCode-native translation of the Claude Code "fastcontext-enforcer" hook.
//
// OpenCode has no PreToolUse hook block; hooks are implemented as plugins. The
// Claude hook runs as a PreToolUse command that can deny a Write|Edit and return
// a reason. Here we register `tool.execute.before`: for edit/write tools we pipe
// the tool args to the original bash enforcer and, when it emits a Claude-style
// deny decision, we throw — which aborts the tool and surfaces the reason to the
// agent. This keeps the (battle-tested) exploration logic in bash untouched while
// reusing it under OpenCode.
//
// The enforcer stands down (allows) when: the file is new, non-code, already
// cited by a trajectory from this session, or the FastContext endpoint is
// unreachable. The bash script scopes trajectories to the current session and
// only counts <final_answer> citations — see the script for details.
//
// Session start: under Claude Code the script derives it from the transcript
// file's birth time; OpenCode has no transcript, so the script falls back to a
// stamp file (claude-fc-enforcer-<session>.start in TMPDIR) created on its
// first run. Left alone, that stamp would be created at the first *edit*
// attempt, disqualifying explorations done earlier in the session. So we touch
// the stamp on the session's first tool call of any kind — exploration always
// precedes editing, and the spawned script inherits our TMPDIR, so both sides
// compute the same path.
//
// The bash enforcer lives at skills/fastcontext/hooks/fastcontext-enforcer.sh in
// this repo, and is copied to ~/.config/opencode/hooks/ on install (see README).
// Resolve whichever is present.

function resolveScript(): string {
  const candidates = [
    resolve(process.cwd(), "skills/fastcontext/hooks/fastcontext-enforcer.sh"),
    resolve(homedir(), ".config/opencode/hooks/fastcontext-enforcer.sh"),
  ];
  return candidates.find((p) => existsSync(p)) ?? candidates[1];
}

function extractReason(stdout: string): string | undefined {
  try {
    const m = stdout.match(/\{[\s\S]*\}/);
    if (!m) return undefined;
    const obj = JSON.parse(m[0]) as {
      hookSpecificOutput?: { permissionDecisionReason?: string };
    };
    return obj.hookSpecificOutput?.permissionDecisionReason;
  } catch {
    return undefined;
  }
}

// Sessions whose start stamp has been written this process lifetime. The
// stamp file itself is the durable record; this just avoids re-statting it
// on every tool call.
const stampedSessions = new Set<string>();

function ensureSessionStamp(sessionID: string): void {
  if (stampedSessions.has(sessionID)) return;
  stampedSessions.add(sessionID);
  const stamp = join(
    process.env.TMPDIR ?? tmpdir(),
    `claude-fc-enforcer-${sessionID}.start`,
  );
  try {
    // Create only if absent — "wx" refuses to touch an existing stamp, so a
    // plugin reload never moves the session start forward.
    closeSync(openSync(stamp, "wx"));
  } catch {
    // Already exists (expected) or TMPDIR unwritable; the script's own
    // fallback creates the stamp on its first run in that case.
  }
}

export default async () => {
  return {
    "tool.execute.before": async (
      input: { tool?: string; sessionID?: string },
      output: { args?: { file_path?: string } },
    ) => {
      ensureSessionStamp(input.sessionID ?? "nosession");

      const tool = String(input.tool ?? "").toLowerCase();
      if (tool !== "edit" && tool !== "write") return;

      const file = output.args?.file_path;
      if (!file) return;

      const script = resolveScript();
      if (!existsSync(script)) return; // enforcer not installed -> stand down

      const payload = JSON.stringify({
        tool_input: { file_path: file },
        session_id: input.sessionID ?? "nosession",
      });

      let stdout = "";
      try {
        stdout = execFileSync("bash", [script], {
          input: payload,
          timeout: 10000,
          encoding: "utf8",
          stdio: ["pipe", "pipe", "ignore"],
        });
      } catch (e: any) {
        // The script exits 0 on both allow and deny (Claude protocol). A
        // non-zero exit means the script itself errored (e.g. `jq` missing) —
        // stand down and allow rather than blocking on a broken gate.
        if (e?.stdout) stdout = String(e.stdout);
        else return;
      }

      const denied =
        stdout.includes('"permissionDecision":"deny"') ||
        stdout.includes('"permissionDecision": "deny"');
      if (denied) {
        const reason =
          extractReason(stdout) ??
          "fastcontext enforcer: explore this file before editing. Run the fastcontext skill first, then retry.";
        throw new Error(reason);
      }
    },
  };
};
