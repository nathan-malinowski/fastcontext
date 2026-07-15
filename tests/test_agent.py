import os
from pathlib import Path

import pytest

from fastcontext.agent.agent import Agent
from fastcontext.agent.llm import LLM
from fastcontext.agent.tool import ToolSet
from fastcontext.agent.tool.read import ReadTool

MODEL = os.getenv("FC_MODEL") or os.getenv("MODEL")
BASE_URL = os.getenv("FC_BASE_URL") or os.getenv("BASE_URL")
API_KEY = os.getenv("FC_API_KEY") or os.getenv("API_KEY")

REPO_ROOT = str(Path(__file__).parent.parent)


@pytest.mark.skipif(
    not (MODEL and BASE_URL),
    reason="integration test: requires a live endpoint via FC_MODEL/FC_BASE_URL (or MODEL/BASE_URL)",
)
async def test_agent(tmp_path):
    llm = LLM(model=MODEL, api_key=API_KEY, base_url=BASE_URL)

    work_dir = REPO_ROOT
    toolset = ToolSet(tools=[ReadTool()], work_dir=work_dir)

    agent = Agent(
        name="TestAgent",
        system_prompt="You are a helpful coding assistant.",
        llm=llm,
        toolset=toolset,
        trajectory_file=str(tmp_path / "test_trajectory.jsonl"),
        work_dir=work_dir,
    )

    result = await agent.run(
        f"Please summarize file content of '{work_dir}/README.md' to one sentence.",
        max_turns=5,
        verbose=True,
    )
    print(result)
    assert result


async def _run_agent(instance: dict, agent_config: dict) -> dict:
    from fastcontext.agent.agent_factory import make_fastcontext_agent

    max_turns = int(agent_config.get("max_turns", 4))
    agent = make_fastcontext_agent(
        trajectory_file=agent_config.get("trajectory_file", ".fastcontext/trajectory.jsonl"),
        work_dir=agent_config.get("work_dir", "/testbed"),
    )

    final_answer = await agent.run(prompt=instance["query"], max_turns=max_turns, verbose=True)
    messages = agent.context.get_messages()

    return {
        "n_turn": agent.n_turn,
        "messages": messages,
        "tools": agent.toolset.schema_list(),
        "final_answer": final_answer,
    }


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_agent())
