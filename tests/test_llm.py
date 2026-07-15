import os

import pytest

from fastcontext.agent.llm import LLM

MODEL = os.getenv("FC_MODEL") or os.getenv("MODEL")
BASE_URL = os.getenv("FC_BASE_URL") or os.getenv("BASE_URL")
API_KEY = os.getenv("FC_API_KEY") or os.getenv("API_KEY")

pytestmark = pytest.mark.skipif(
    not (MODEL and BASE_URL),
    reason="integration test: requires a live endpoint via FC_MODEL/FC_BASE_URL (or MODEL/BASE_URL)",
)


async def test_llm():
    llm = LLM(model=MODEL, api_key=API_KEY, base_url=BASE_URL)
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
    ]
    msg = await llm.acall(
        messages=messages,
        tools=None,
    )
    print(msg.to_dict())
    assert msg.role == "assistant"
    assert msg.content or msg.tool_calls


async def test_llm_tools():
    llm = LLM(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.0,
        max_tokens=1024,
    )
    messages = [
        {"role": "system", "content": "You are a powerful AI agent."},
        {
            "role": "user",
            "content": "read file content from ./test_llm.py and ./README.md",
        },
    ]
    from fastcontext.agent.tool.read import ReadTool

    msg = await llm.acall(
        messages=messages,
        tools=[ReadTool().schema()],
    )
    print(msg.to_dict())
    assert msg.role == "assistant"


async def test_llm_tools_result():
    llm = LLM(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.0,
        max_tokens=1024,
    )
    messages = [
        {"role": "system", "content": "You are a powerful AI agent."},
        {"role": "user", "content": "please show me the current time"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_0",
                    "function": {"arguments": '{"command": "date"}', "name": "bash"},
                    "type": "function",
                },
                {
                    "id": "call_1",
                    "function": {"arguments": '{"command": "date"}', "name": "bash"},
                    "type": "function",
                },
            ],
        },
        {
            "role": "tool",
            "content": "Thu Aug 21 17:42:44 CST 2025",
            "tool_call_id": "call_0",
        },
        {
            "role": "tool",
            "content": "Thu Aug 21 17:42:44 CST 2025",
            "tool_call_id": "call_1",
            "name": "bash",
        },
    ]
    msg = await llm.acall(
        messages=messages,
        tools=None,
    )
    print(msg.to_dict())
    assert msg.role == "assistant"


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_llm_tools())
