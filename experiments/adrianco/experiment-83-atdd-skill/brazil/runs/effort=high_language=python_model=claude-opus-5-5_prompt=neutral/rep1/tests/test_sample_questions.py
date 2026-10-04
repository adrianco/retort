"""At least 20 natural-language sample questions, each mapped to the tool call an LLM would make.

Every case runs through the MCP server (tools/call) and checks the answer text.
"""

import time

import pytest

from brsoccer.samples import CASES
from brsoccer.server import MCPServer


@pytest.fixture(scope="module")
def server(db):
    s = MCPServer()
    s.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "pytest", "version": "1"}}})
    return s


def test_at_least_20_sample_questions():
    assert len(CASES) >= 20


@pytest.mark.parametrize("question, tool, args, expected", CASES, ids=[c[0][:50] for c in CASES])
def test_sample_question(server, question, tool, args, expected):
    start = time.perf_counter()
    resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": tool, "arguments": args}})
    elapsed = time.perf_counter() - start
    result = resp["result"]
    text = result["content"][0]["text"]
    assert result["isError"] is False, text
    for snippet in expected:
        assert snippet in text, f"{question!r}: expected {snippet!r} in:\n{text}"
    assert elapsed < 2.0, f"{question!r} took {elapsed:.2f}s"
