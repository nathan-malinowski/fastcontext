import asyncio
from pathlib import Path

from fastcontext.agent.agent import Agent
from fastcontext.agent.llm import Message
from fastcontext.agent.tool import ToolSet
from fastcontext.agent.tool.read import ReadTool
from fastcontext.agent.utils import load_system_prompt

REPO_ROOT = str(Path(__file__).parent.parent)


def test_default_style_is_minimal():
    prompt = load_system_prompt()
    assert "You are FastContext" in prompt


def test_tuned_style_renders_workspace_context():
    prompt = load_system_prompt("tuned", work_dir=REPO_ROOT)
    assert "codebase exploration specialist" in prompt
    assert REPO_ROOT in prompt, "workspace path must be substituted"
    assert "pyproject.toml" in prompt, "directory listing must be substituted"
    assert "${" not in prompt, "no unrendered template variables"


def test_env_selects_style(monkeypatch):
    monkeypatch.setenv("FC_SYSTEM_PROMPT", "tuned")
    prompt = load_system_prompt(work_dir=REPO_ROOT)
    assert "codebase exploration specialist" in prompt


class _StubLLM:
    model = "stub"

    async def acall(self, messages, tools):
        return Message(role="assistant", content="<final_answer>\n</final_answer>")


def _make_agent(tmp_path, prompt_style):
    work_dir = str(tmp_path)
    return Agent(
        name="FastContext",
        system_prompt="system",
        llm=_StubLLM(),
        toolset=ToolSet([ReadTool()], work_dir=work_dir),
        trajectory_file=str(tmp_path / "traj" / "traj.jsonl"),
        work_dir=work_dir,
        prompt_style=prompt_style,
    )


def test_tuned_style_wraps_query_in_tags(tmp_path):
    agent = _make_agent(tmp_path, "tuned")
    asyncio.run(agent.run("Where is the config loaded?", max_turns=2))
    first = [m for m in agent.context.get_messages() if m["role"] == "user"][0]["content"]
    assert first == "<query>Where is the config loaded?</query>"
    assert "Repository root" not in first


def test_minimal_style_injects_repository_root(tmp_path):
    agent = _make_agent(tmp_path, "minimal")
    asyncio.run(agent.run("Where is the config loaded?", max_turns=2))
    first = [m for m in agent.context.get_messages() if m["role"] == "user"][0]["content"]
    assert str(tmp_path) in first
    assert "<query>" not in first
