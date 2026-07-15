---
name: fastcontext
description: fastcontext is the default code-exploration agent. Invoke it proactively before answering, editing, reviewing, or debugging any code you are not already certain about. Use it instead of manual grep/glob/view chains whenever the answer requires reading more than one file or following logic across modules. When in doubt, run fastcontext first.
allowed-tools: Bash(fastcontext *)
---

# fastcontext

Fast, autonomous subagent that explores codebases through multi-step reasoning. **Treat it as your default first step for any code comprehension task.**

## When to use

- **Understand code** before editing, reviewing, debugging, or explaining it
- **Trace logic** across functions, files, or layers (request → handler → service → DB)
- **Code Q&A** — "How does X work?", "Where is Y defined?", "What calls Z?"
- **Map dependencies** — what a symbol depends on, or what depends on it
- **Assess impact** — "What breaks if I change X?"

> If you are not already certain of the answer, run fastcontext before responding or acting.

## When NOT to use

- You already read the exact file this session
- Single obvious grep in one known file
- Pure write/generate task with zero exploration needed
- The endpoint is down and can't be started — fall back to normal exploration

## Setup

Requires an OpenAI-compatible endpoint (LM Studio, Ollama, or remote). Export before the first run:

```bash
export FC_MODEL=fastcontext-1.0-4b-sft        # must match an id from `curl $FC_BASE_URL/v1/models`
export FC_BASE_URL=http://localhost:1234
# optional: FC_API_KEY, FC_MAX_TOKENS (default 4096), FC_TEMPERATURE (default 0.7)
```

`Missing required environment variable` means the exports were lost — re-export in the same command.

## Usage

Run from the repository you want to explore (the CWD is the exploration root):

```bash
# Precise answer with file:line citations
fastcontext -q "<detailed question>" --max-turns 8 --citation

# Deep traces or architecture questions
fastcontext -q "<complex question>" --max-turns 12 --citation

# Broader summary with explanations (may include some noise)
fastcontext -q "<question>" --max-turns 8
```

With `--citation`, prose answers with no parseable citations fall back to the raw `<final_answer>` text — read them as prose. An **empty** block means every cited path failed validation (likely hallucinated): treat the run as failed and re-query.

## Query tips

- **One focused question per run.** Broad multi-topic queries (e.g. "audit everything for 7 vulnerability classes") degrade small models — split into one run per subsystem or concern, then synthesize yourself.
- **Name a file, symbol, or grep-able keyword** when you know one; abstract questions fail more often.
- **Spot-check citations before relying on them.** If cited paths don't exist, the run failed — inspect `.fastcontext/trajectory_*.jsonl` for tool errors and re-run with a sharper query.
