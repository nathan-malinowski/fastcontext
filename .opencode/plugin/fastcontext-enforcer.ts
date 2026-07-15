import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { resolve } from "node:path";

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
// explored this session, or the FastContext endpoint is unreachable.
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

export default async () => {
  return {
    "tool.execute.before": async (
      input: { tool?: string; sessionID?: string },
      output: { args?: { file_path?: string } },
    ) => {
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
