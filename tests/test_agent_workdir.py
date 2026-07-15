import asyncio

from fastcontext.agent.agent import Agent
from fastcontext.agent.llm import Message
from fastcontext.agent.tool import ToolSet
from fastcontext.agent.tool.read import ReadTool


class _StubLLM:
    model = "stub"

    async def acall(self, messages, tools):
        return Message(role="assistant", content="<final_answer>\n</final_answer>")


def _make_agent(tmp_path) -> Agent:
    work_dir = str(tmp_path)
    return Agent(
        name="FastContext",
        system_prompt="system",
        llm=_StubLLM(),
        toolset=ToolSet([ReadTool()], work_dir=work_dir),
        trajectory_file=str(tmp_path / "traj" / "traj.jsonl"),
        work_dir=work_dir,
    )


def test_user_prompt_includes_repository_root(tmp_path):
    agent = _make_agent(tmp_path)
    asyncio.run(agent.run("Where is the config loaded?", max_turns=2))

    user_messages = [m for m in agent.context.get_messages() if m["role"] == "user"]
    assert user_messages, "expected a user message in the agent context"
    first = user_messages[0]["content"]
    assert str(tmp_path) in first, "user prompt must state the repository root"
    assert "Where is the config loaded?" in first, "original query must be preserved"


def test_injection_survives_prompt_mentioning_sibling_path(tmp_path):
    agent = _make_agent(tmp_path)
    query = f"why does this differ from {tmp_path}-archive/foo.py?"
    asyncio.run(agent.run(query, max_turns=2))

    first = [m for m in agent.context.get_messages() if m["role"] == "user"][0]["content"]
    assert "use this absolute path in all tool calls" in first, (
        "a prompt merely mentioning a sibling path must not suppress the root injection"
    )


class _NoneContentLLM:
    model = "stub"

    async def acall(self, messages, tools):
        return Message(role="assistant", content=None, reasoning_content="thinking only")


def test_none_content_final_message_does_not_crash_citation_mode(tmp_path):
    agent = _make_agent(tmp_path)
    agent.llm = _NoneContentLLM()
    result = asyncio.run(agent.run("anything", max_turns=2, citation=True))
    assert result == ""


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        test_user_prompt_includes_repository_root(Path(d))
