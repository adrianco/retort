"""The tool-calling shim that makes Swiftlet usable by an agent.

Swiftlet's endpoint drops `tools` silently and 400s on the assistant turn Hermes
replays after a tool call. Both failures are invisible in the scores — they look
exactly like a model that cannot code — so the translation is tested directly,
including a real HTTP round trip against a stub upstream.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from retort.playpen.swiftlet_shim import (
    build_response,
    downgrade_messages,
    parse_tool_calls,
    render_tools_prompt,
    serve,
)

# --- parsing ---------------------------------------------------------------


def test_parse_single_tool_call():
    text = (
        'I will read it.\n'
        '<tool_call>\n{"name": "read_file", "arguments": {"path": "a.py"}}\n</tool_call>'
    )
    prose, calls = parse_tool_calls(text)
    assert prose == "I will read it."
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "read_file"
    assert calls[0]["type"] == "function"
    # OpenAI requires arguments as a JSON *string*, not an object — a client that
    # does json.loads(arguments) breaks if we hand back a dict.
    assert isinstance(calls[0]["function"]["arguments"], str)
    assert json.loads(calls[0]["function"]["arguments"]) == {"path": "a.py"}


def test_parse_multiple_tool_calls_are_all_returned():
    text = (
        '<tool_call>{"name": "a", "arguments": {}}</tool_call>'
        '<tool_call>{"name": "b", "arguments": {"x": 1}}</tool_call>'
    )
    prose, calls = parse_tool_calls(text)
    assert prose == ""
    assert [c["function"]["name"] for c in calls] == ["a", "b"]
    assert len({c["id"] for c in calls}) == 2, "ids must be unique per call"


def test_plain_text_is_untouched():
    prose, calls = parse_tool_calls("just an answer")
    assert (prose, calls) == ("just an answer", [])


def test_malformed_tool_call_stays_visible_as_prose():
    """A broken call is a real model failure and must not be silently swallowed.

    If the harness dropped it, the transcript would show a turn that did nothing
    for no visible reason — the run would look like an incapable model again.
    """
    text = '<tool_call>{"name": "a", "arguments": {oops}}</tool_call>'
    prose, calls = parse_tool_calls(text)
    assert calls == []
    assert "oops" in prose


def test_tool_call_without_a_name_is_not_a_call():
    prose, calls = parse_tool_calls('<tool_call>{"arguments": {}}</tool_call>')
    assert calls == []
    assert "arguments" in prose


# --- message downgrade -----------------------------------------------------


def test_null_content_assistant_turn_survives():
    """The turn that 400s the stock server: content=None plus tool_calls."""
    msgs = downgrade_messages([
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "c1", "type": "function",
                         "function": {"name": "read_file",
                                      "arguments": '{"path": "a.py"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "print(1)"},
    ])
    assert all(isinstance(m["content"], str) for m in msgs), "Swiftlet decodes only str"
    assert all(set(m) == {"role", "content"} for m in msgs), "extra keys break decoding"
    # the prior call is replayed in the form the model itself emits
    assert "<tool_call>" in msgs[0]["content"]
    assert "read_file" in msgs[0]["content"]
    assert json.loads(
        msgs[0]["content"].split("<tool_call>")[1].split("</tool_call>")[0]
    )["arguments"] == {"path": "a.py"}
    # the tool role is preserved — Qwen's template understands it
    assert msgs[1]["role"] == "tool"


def test_multimodal_content_parts_are_flattened():
    msgs = downgrade_messages([
        {"role": "user", "content": [{"type": "text", "text": "hi"},
                                     {"type": "text", "text": "there"}]},
    ])
    assert msgs[0]["content"] == "hi\nthere"


def test_tools_prompt_uses_qwen_tag_vocabulary():
    block = render_tools_prompt([
        {"type": "function", "function": {"name": "read_file", "parameters": {}}}
    ])
    assert "<tools>" in block and "</tools>" in block
    assert "<tool_call>" in block
    assert "read_file" in block


# --- response assembly -----------------------------------------------------


def test_build_response_flips_finish_reason():
    upstream = {
        "id": "chatcmpl-1", "model": "qwen3_next",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant",
            "content": '<tool_call>{"name": "ls", "arguments": {}}</tool_call>'}}],
    }
    out = build_response(upstream, "Qwen3.6-35B-A3B")
    assert out["choices"][0]["finish_reason"] == "tool_calls"
    assert out["model"] == "Qwen3.6-35B-A3B", "advertise the preset name, not the arch"
    assert out["choices"][0]["message"]["content"] is None


def test_build_response_leaves_plain_answers_alone():
    upstream = {
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "done"}}],
    }
    out = build_response(upstream, None)
    assert out["choices"][0]["finish_reason"] == "stop"
    assert out["choices"][0]["message"]["content"] == "done"
    assert "tool_calls" not in out["choices"][0]["message"]


# --- end to end over HTTP --------------------------------------------------


class _StubSwiftlet(BaseHTTPRequestHandler):
    """Stands in for swiftlet-server: records the request, returns a tool call."""

    received: dict[str, Any] = {}

    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        _StubSwiftlet.received = json.loads(self.rfile.read(n))
        body = json.dumps({
            "id": "chatcmpl-stub", "object": "chat.completion", "created": 1,
            "model": "qwen3_next",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant",
                "content": '<tool_call>\n{"name": "write_file", '
                           '"arguments": {"path": "m.py"}}\n</tool_call>'}}],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def shim_pair():
    """A live shim in front of a live stub upstream, on ephemeral ports."""
    upstream = HTTPServer(("127.0.0.1", 0), _StubSwiftlet)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    shim = serve(listen_port=0, upstream_port=upstream.server_address[1],
                 model_name="Qwen3.6-35B-A3B")
    threading.Thread(target=shim.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{shim.server_address[1]}"
    shim.shutdown()
    upstream.shutdown()


def _post(url: str, payload: dict) -> dict:
    import urllib.request
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def test_end_to_end_tools_in_tool_calls_out(shim_pair):
    """The whole point: an agent-shaped request survives the round trip."""
    out = _post(f"{shim_pair}/v1/chat/completions", {
        "model": "Qwen3.6-35B-A3B",
        "messages": [
            {"role": "user", "content": "make m.py"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "c1", "type": "function",
                             "function": {"name": "ls", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "(empty)"},
        ],
        "tools": [{"type": "function",
                   "function": {"name": "write_file", "parameters": {}}}],
    })

    sent = _StubSwiftlet.received
    # the shim must hand Swiftlet only what its decoder accepts...
    assert all(set(m) == {"role", "content"} for m in sent["messages"])
    assert all(isinstance(m["content"], str) for m in sent["messages"])
    assert sent["stream"] is False, "must buffer — tool calls need the whole message"
    # ...with the tools rendered into a system turn it would otherwise never see
    assert sent["messages"][0]["role"] == "system"
    assert "write_file" in sent["messages"][0]["content"]
    assert "tools" not in sent, "Swiftlet would silently drop it anyway"

    # and hand Hermes back a real tool call
    choice = out["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    assert choice["message"]["tool_calls"][0]["function"]["name"] == "write_file"
    assert out["model"] == "Qwen3.6-35B-A3B"


def test_existing_system_message_is_merged_not_duplicated(shim_pair):
    _post(f"{shim_pair}/v1/chat/completions", {
        "messages": [{"role": "system", "content": "You are terse."},
                     {"role": "user", "content": "hi"}],
        "tools": [{"type": "function", "function": {"name": "ls"}}],
    })
    sent = _StubSwiftlet.received
    roles = [m["role"] for m in sent["messages"]]
    assert roles.count("system") == 1, "two system turns confuse the chat template"
    assert "You are terse." in sent["messages"][0]["content"]
    assert "ls" in sent["messages"][0]["content"]


def test_models_endpoint_advertises_the_preset_name(shim_pair):
    import urllib.request
    with urllib.request.urlopen(f"{shim_pair}/v1/models", timeout=10) as r:
        body = json.loads(r.read())
    # _wait_ready and Hermes both match on the configured name, not Swiftlet's
    # raw arch string ("qwen3_next").
    assert body["data"][0]["id"] == "Qwen3.6-35B-A3B"


def test_streaming_client_gets_wellformed_sse(shim_pair):
    import urllib.request
    req = urllib.request.Request(
        f"{shim_pair}/v1/chat/completions",
        data=json.dumps({"messages": [{"role": "user", "content": "hi"}],
                         "stream": True}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode()
    assert raw.endswith("data: [DONE]\n\n")
    chunks = [json.loads(line[6:]) for line in raw.splitlines()
              if line.startswith("data: ") and not line.endswith("[DONE]")]
    assert chunks[-1]["choices"][0]["finish_reason"] == "tool_calls"
    assert chunks[0]["choices"][0]["delta"]["tool_calls"][0]["index"] == 0
