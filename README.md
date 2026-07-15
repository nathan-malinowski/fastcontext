# FastContext: Training Efficient Repository Explorer for Coding Agents

<p align="center">
  <a href="https://arxiv.org/abs/2606.14066"><img src="https://img.shields.io/badge/arXiv-2606.14066-b31b1b.svg" alt="arXiv"></a>
  <a href="https://github.com/microsoft/fastcontext"><img src="https://img.shields.io/badge/Code-GitHub-181717.svg" alt="Code"></a>
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg" alt="Python 3.12+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
</p>

<p align="center">
  <a href="#news">📰 News</a> |
  <a href="#overview">🔎 Overview</a> |
  <a href="#results">📊 Results</a> |
  <a href="#quick-start">⚡ Quick Start</a> |
  <a href="#reproduction">🧪 Reproduction</a> |
  <a href="#citation">📚 Citation</a>
</p>

FastContext is a lightweight repository-exploration subagent for coding agents. Instead of letting the main
coding agent spend its own context window on broad file reads and code searches, the main agent delegates
a natural-language context query to FastContext. FastContext explores the repository with read-only tools,
issues independent tool calls in parallel, and returns compact file-line citations as focused evidence for the
main agent.

<p align="center">
  <img src="figures/overview.png" alt="FastContext overview" width="95%">
</p>

## News

- 🚀 **2026-06-15**: We released the arXiv paper [[📄 arXiv](https://arxiv.org/abs/2606.14066)] and the model weights [[🤗 Model](https://huggingface.co/collections/microsoft/swe-fastcontext)].


## Overview

Modern coding agents often use the same model to explore a repository and solve the task. This makes
exploration expensive: exploratory reads and searches consume tokens, stay in the solver's history, and can
pollute later reasoning with irrelevant snippets.

FastContext separates repository exploration from solving:

- 🧭 **Delegated exploration**: the main agent asks FastContext for repository context before editing or answering.
- 🔒 **Read-only tools**: FastContext uses `Read`, `Glob`, and `Grep`; it does not modify files.
- ⚙️ **Parallel tool calling**: independent reads and searches can be issued in the same exploration turn.
- 📌 **Compact evidence**: the final response is a short `<final_answer>` block with file paths and line ranges.
- 🧠 **Trainable explorers**: the paper trains 4B-30B exploration models with SFT and task-grounded RL.

The intended contract is simple: FastContext finds the relevant code; the main coding agent uses that focused
evidence to edit, test, or answer.

```text
<final_answer>
/path/to/repo/src/router.py:42-58
/path/to/repo/tests/test_router.py:101-119
</final_answer>
```

## Results

Across SWE-bench Multilingual, SWE-bench Pro, and SWE-QA, FastContext improves the score-token tradeoff of
Mini-SWE-Agent style coding agents.

| Result | Finding |
| --- | --- |
| 📈 End-to-end success | Up to **+5.5** score improvement with delegated repository exploration. |
| 💸 Main-agent token use | Up to **60.3%** fewer main-agent tokens. |
| 🧠 Compact trained explorer | FC-4B-RL improves or ties FC-4B-SFT across all reported end-to-end settings. |
| 🎯 Standalone exploration | Trained FastContext models recover patch-relevant files and symbols more accurately than non-FastContext small-model baselines. |

<p align="center">
  <img src="figures/main-result.png" alt="FastContext main results" width="95%">
</p>

## Token Efficiency

FastContext reduces the main agent's context burden by moving broad repository exploration outside the
solver trajectory. The reduction is especially visible in file-reading and code-search tokens.

<p align="center">
  <img src="figures/breakdown.png" alt="FastContext token breakdown" width="95%">
</p>

## Installation

FastContext requires Python 3.12 or newer. The repository uses [`uv`](https://docs.astral.sh/uv/) for package
and environment management.

Install the CLI from the repository root:

```bash
uv tool install .
```

For development:

```bash
uv sync --all-groups
```

Build a local wheel:

```bash
uv build
```

The built wheel is written under `dist/`, for example:

```text
dist/fastcontext-0.1.0-py3-none-any.whl
```

## Model Configuration

FastContext expects an OpenAI-compatible chat completions endpoint. For direct CLI usage, configure:

```bash
export FC_BASE_URL="https://your-endpoint.example/v1"
export FC_MODEL="your-model-name"

# optional: only needed when your endpoint requires authentication
export FC_API_KEY="your-api-key"

# optional: override default FastContext parameters
export FC_MAX_TOKENS=4096
export FC_TEMPERATURE=0.7
```

Benchmark runners may also pass separate FastContext credentials through `FASTCONTEXT_*` variables in
`benchmark/evaluation/configs/example.env`.

## Quick Start

### Local Ollama endpoint

The easiest local setup on macOS is to run an OpenAI-compatible endpoint with
[Ollama](https://ollama.com/). Install Ollama, start the service, and pull a quantized FastContext model:

```bash
brew install ollama
brew services start ollama
ollama pull hf.co/mitkox/FastContext-1.0-4B-RL-Q4_K_M-GGUF
```

Configure FastContext to use the local endpoint:

```bash
export FC_BASE_URL="http://127.0.0.1:11434/v1/"
export FC_MODEL="hf.co/mitkox/FastContext-1.0-4B-RL-Q4_K_M-GGUF:latest"

# Ollama does not require an API key.

# Qwen/FastContext models can emit reasoning separately from final content.
# Ollama accepts: none, low, medium, high, max.
export FC_REASONING_EFFORT="none"

export FC_MAX_TOKENS=1024
export FC_TEMPERATURE=0
```

### Local LM Studio endpoint

[LM Studio](https://lmstudio.ai/) works the same way through its OpenAI-compatible API. Load a
FastContext model in LM Studio, start the server (default port 1234), and point FastContext at it:

```bash
export FC_BASE_URL="http://localhost:1234"
export FC_MODEL="fastcontext-1.0-4b-sft"  # must match an ID from `curl http://localhost:1234/v1/models`

# LM Studio does not require an API key.
```

A bare server root is routed to the OpenAI-compatible `/v1` path automatically, as are LM Studio's
native REST paths (`/api/v1`, `/api/v0`). The native `/api/v1/chat` endpoint itself is not used
because it does not accept custom tool definitions, which the agent's GLOB/GREP/READ loop requires.

Run FastContext from the repository you want to explore:

```bash
fastcontext \
  --query "Find the files that implement authentication and explain where to make a change" \
  --max-turns 6 \
  --traj .fastcontext/trajectory.jsonl
```

Return only the machine-readable citation block:

```bash
fastcontext \
  --query "Locate the request validation logic" \
  --citation
```

Useful CLI options:

| Option | Description |
| --- | --- |
| `--query`, `-q` | Natural-language exploration request. |
| `--traj`, `-t` | JSONL trajectory output path. |
| `--max-turns` | Maximum exploration turns before forcing a final answer. |
| `--verbose` | Print intermediate messages and runtime information. |
| `--citation` | Return only the `<final_answer>` block when present. |

## Claude Code Integration (Optional)

The `skills/fastcontext/` directory ships a [Claude Code](https://claude.com/claude-code) skill that
teaches the agent to delegate repository exploration to FastContext instead of running its own
grep/read chains.

Install the skill for all projects:

```bash
cp -r skills/fastcontext ~/.claude/skills/fastcontext
```

Optionally, install the exploration-enforcer hook. It blocks the first edit to any code file that no
FastContext trajectory has touched yet, nudging the agent to explore before editing. It fires at most
once per file per session, and stands down automatically when the FastContext endpoint is unreachable:

```bash
mkdir -p ~/.claude/hooks
cp skills/fastcontext/hooks/fastcontext-enforcer.sh ~/.claude/hooks/
```

Then register it in `~/.claude/settings.json` (merge into any existing `hooks` key):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/fastcontext-enforcer.sh",
            "timeout": 10,
            "statusMessage": "Checking fastcontext exploration..."
          }
        ]
      }
    ]
  }
}
```

## Programmatic Use

```python
import asyncio

from fastcontext.agent.agent_factory import make_fastcontext_agent


async def main() -> None:
    agent = make_fastcontext_agent(
        trajectory_file=".fastcontext/trajectory.jsonl",
        work_dir="/path/to/repo",
    )
    answer = await agent.run(
        prompt="Find where database migrations are defined",
        max_turns=6,
        citation=True,
    )
    print(answer)


asyncio.run(main())
```

## Reproduction

This repository contains scripts for end-to-end Mini-SWE-Agent runs and standalone exploration evaluation.
The exact paths, model names, and credentials should be adapted to your serving environment.

### End-to-End SWE-Bench Runs

```bash
git submodule update --init --recursive
uv build
cp benchmark/evaluation/configs/example.env .env
```

Edit `.env` with the main-agent and FastContext endpoint credentials, then run:

```bash
uv run --group benchmark python benchmark/evaluation/bench_mini_swe_agent.py \
  --bench swebench-multilingual \
  --agent-config prompts/gpt-multi-fc.yaml \
  --config .env \
  --output preds.json \
  --logs-dir logs \
  --workers 1
```

For SWE-bench Pro, use the Pro prompt:

```bash
uv run --group benchmark python benchmark/evaluation/bench_mini_swe_agent.py \
  --bench ScaleAI/SWE-bench_Pro \
  --agent-config prompts/gpt-pro-fc.yaml \
  --config .env \
  --output preds-pro.json \
  --logs-dir logs-pro
```

### Standalone Exploration

The standalone runner evaluates FastContext as a repository explorer on SWE-bench-style subagent queries.

```bash
cd benchmark/swebench
cp run.sh.sample run.sh
# Edit run.sh with FC_BASE_URL, FC_MODEL, and FC_API_KEY if your endpoint requires authentication.

uv run --group benchmark python bench_fastcontext.py \
  --bench swebench-multilingual \
  --experiment fastcontext-eval \
  --prediction-file predictions.jsonl \
  --local-mount-dir /absolute/path/to/output \
  --num-threads 1
```

After extracting the final FastContext responses into a JSONL file with `instance_id` and `finial_response`
fields, score citation quality from the repository root:

```bash
uv run --group benchmark python benchmark/evaluation/run_score.py \
  swebench-multilingual \
  result_finial_response.jsonl
```

## Training and Serving

The `training/` directory contains scripts used for the SFT and RL experiments described in the paper.
These scripts assume a research training environment with external model checkpoints, datasets, and cluster
settings; treat paths and launcher options as examples to adapt.

```text
training/
  fastcontext-sft/     Supervised fine-tuning scripts and data utilities
  fastcontext-rl/      Reinforcement-learning scripts and reward utilities
```

The `serving/` directory contains example manifests and API checks for serving FastContext-compatible
models behind an OpenAI-compatible endpoint.

## Repository Layout

```text
src/fastcontext/
  cli.py                         Command-line entry point
  agent/
    agent.py                     Agent loop
    agent_factory.py             Default FastContext agent construction
    context.py                   Conversation and trajectory storage
    llm.py                       OpenAI-compatible LLM wrapper
    system.md                    Explorer system prompt
    tool/
      read.py                    Read tool
      glob.py                    Glob tool
      grep.py                    Grep tool
      tool.py                    Tool base classes and ToolSet

benchmark/
  environment/                   Docker environment helpers
  evaluation/                    End-to-end Mini-SWE-Agent runners and scoring utilities
  swebench/                      SWE-bench-style standalone exploration runner

prompts/                         Mini-SWE-Agent prompt configs with FastContext integration
training/                        SFT and RL training scripts
serving/                         Example serving manifests and API checks
tests/                           Unit and integration-style tests
figures/                         README and paper figures
```

## Development

Run linting:

```bash
uv run ruff check .
```

Run tests:

```bash
uv run pytest -q
```

Build the package:

```bash
uv build
```

## Notes

- FastContext is intended for repository exploration, not code modification.
- Tool outputs are capped to keep interactions responsive.
- The default CLI records trajectories under `.fastcontext/` unless `--traj` is provided.
- For best results, write specific exploration queries that name the behavior, subsystem, error, or files you are trying to locate.

## Citation

If you find FastContext useful, please cite:

```bibtex
@misc{zhang2026fastcontexttrainingefficientrepository,
      title={FastContext: Training Efficient Repository Explorer for Coding Agents},
      author={Shaoqiu Zhang and Maoquan Wang and Yuling Shi and Yuhang Wang and Xiaodong Gu and Yongqiang Yao and Tori Gong and Sheng Chen and Rao Fu and Anisha Agarwal and Spandan Garg and Gabriel Ryan and Colin Merkel and Yufan Huang and Shengyu Fu},
      year={2026},
      eprint={2606.14066},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2606.14066},
}
```

## Acknowledgements

FastContext builds on open research infrastructure and benchmarks for coding agents, including SWE-bench,
SWE-bench Multilingual, SWE-bench Pro, SWE-QA, Mini-SWE-Agent, and open model / serving ecosystems.
