"""A tool-calling shim that fronts ``swiftlet-server``.

Swiftlet (https://github.com/leonickson1/Swiftlet) is a Swift + Metal runtime that
streams routed MoE experts from SSD, so a 35B/80B Qwen runs in a few GB of RAM. Its
OpenAI endpoint, though, is **chat-only**: ``Sources/SwiftletServer/main.swift``
declares

.. code-block:: swift

    struct ChatRequest: Decodable {
        struct Message: Decodable { let role: String; let content: String }
        let messages: [Message]
        let stream: Bool?
        let max_tokens: Int?
        let max_completion_tokens: Int?
    }

Two consequences, both fatal to an agentic run and both *silent*:

1. ``tools`` is not a declared key, so Swift's ``JSONDecoder`` **drops it without
   error**. The model is never told any tools exist.
2. ``content`` is a non-optional ``String``, so the assistant turn Hermes replays
   after a tool call — ``{"role": "assistant", "content": null, "tool_calls": [...]}``
   — **fails to decode entirely** and the whole request 400s as "malformed request".

And every reply is hardcoded ``finish_reason: "stop"``; there is no ``tool_calls``
path at all. Point Hermes straight at Swiftlet and it writes no code and scores a
**false zero** — indistinguishable from a model that cannot do the task, which is
precisely the harness-vs-model confusion CLAUDE.md's "suspect the harness before
the model" rule exists to prevent.

This shim sits between the two and translates in both directions:

- **Downgrade** (Hermes -> Swiftlet): render the ``tools`` array into a system
  message using Qwen's *own* template phrasing, and flatten every message to the
  ``{role: str, content: str}`` shape Swiftlet's decoder accepts — including
  re-rendering a historical assistant ``tool_calls`` back into the ``<tool_call>``
  tags the model itself emits, so the conversation it sees is self-consistent.
- **Upgrade** (Swiftlet -> Hermes): parse ``<tool_call>{...}</tool_call>`` out of the
  generated text and re-emit it as a real OpenAI ``tool_calls`` array with
  ``finish_reason: "tool_calls"``.

**Known fidelity gap, deliberate.** llama.cpp's ``--jinja`` renders tools through the
model's actual chat template; we cannot, because Swiftlet applies the template
*internally* from ``messages`` and gives us no way to pass template kwargs. So tools
are injected as system-message text instead. The wording below is copied from Qwen's
own template to keep the model on its trained distribution, but this is an
approximation and it is the first thing to suspect if tool-call quality is worse
here than on oMLX for the same weights. The higher-fidelity fix is upstream: teach
``SwiftletSession`` to pass ``tools`` to ``applyChatTemplate``.

Run standalone::

    python -m retort.playpen.swiftlet_shim \\
        --listen-port 8080 --upstream-port 8081 --model-name Qwen3.6-35B-A3B
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger(__name__)

# Qwen emits tool calls as a JSON object wrapped in <tool_call> tags, one per call.
# DOTALL because the payload is pretty-printed across lines.
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)

# Lifted from Qwen3's chat template so the injected block matches what the weights
# were trained to condition on. Keep the wording; drifting from it costs accuracy.
_TOOLS_PREAMBLE = """\
# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_lines}
</tools>

For each function call, return a json object with function name and arguments \
within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>"""


def render_tools_prompt(tools: list[dict[str, Any]]) -> str:
    """Render an OpenAI ``tools`` array into Qwen's own system-prompt block."""
    lines = "\n".join(json.dumps(t, ensure_ascii=False) for t in tools)
    return _TOOLS_PREAMBLE.format(tool_lines=lines)


def _content_to_text(content: Any) -> str:
    """Flatten any OpenAI ``content`` shape to a plain string.

    ``None`` (an assistant turn that was *only* tool calls) becomes ``""``, and the
    multimodal list-of-parts form is reduced to its text parts. Swiftlet's decoder
    accepts nothing else.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" or "text" in part:
                    parts.append(str(part.get("text", "")))
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p)
    return str(content)


def _render_assistant_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
    """Re-render a historical assistant ``tool_calls`` array as ``<tool_call>`` tags.

    The model produced these tags in the first place; replaying them in the same
    form keeps the transcript on-distribution. Replaying them as OpenAI JSON — or
    dropping them, which is what happens without this — leaves the model looking at
    a tool *result* with no visible call, and it tends to re-issue the call in a loop.
    """
    out = []
    for call in tool_calls:
        fn = call.get("function", {}) or {}
        args = fn.get("arguments", "")
        # OpenAI carries arguments as a JSON *string*; the model writes an object.
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                pass  # keep the raw string; better a odd-looking call than a crash
        payload = json.dumps({"name": fn.get("name", ""), "arguments": args},
                             ensure_ascii=False)
        out.append(f"<tool_call>\n{payload}\n</tool_call>")
    return "\n".join(out)


def downgrade_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Flatten messages to the ``{role, content}`` string pairs Swiftlet decodes.

    Roles are preserved (Qwen's template understands ``tool``), only the payload
    shape changes.
    """
    out: list[dict[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "user"))
        text = _content_to_text(msg.get("content"))
        if msg.get("tool_calls"):
            rendered = _render_assistant_tool_calls(msg["tool_calls"])
            text = f"{text}\n{rendered}".strip() if text else rendered
        out.append({"role": role, "content": text})
    return out


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Split generated text into (prose, OpenAI ``tool_calls``).

    A tag whose body is not valid JSON is **left in the prose untouched** rather than
    dropped or guessed at: a malformed call is a real model failure and must stay
    visible in the transcript, not be silently swallowed by the harness.
    """
    calls: list[dict[str, Any]] = []
    keep_spans: list[tuple[int, int]] = []
    cursor = 0
    for match in _TOOL_CALL_RE.finditer(text):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("unparseable <tool_call> body, left as prose: %r",
                           match.group(1)[:200])
            continue
        if not isinstance(payload, dict) or "name" not in payload:
            logger.warning("<tool_call> without a name, left as prose: %r",
                           match.group(1)[:200])
            continue
        args = payload.get("arguments", {})
        calls.append({
            "id": f"call_{uuid.uuid4().hex[:24]}",
            "type": "function",
            "function": {
                "name": str(payload["name"]),
                # OpenAI requires arguments as a JSON-encoded string.
                "arguments": args if isinstance(args, str)
                else json.dumps(args, ensure_ascii=False),
            },
        })
        keep_spans.append((cursor, match.start()))
        cursor = match.end()
    if not calls:
        return text, []
    keep_spans.append((cursor, len(text)))
    prose = "".join(text[a:b] for a, b in keep_spans)
    return prose.strip(), calls


def build_response(
    upstream: dict[str, Any], model_name: str | None
) -> dict[str, Any]:
    """Rewrite a Swiftlet chat completion into one that can carry tool calls."""
    choices = upstream.get("choices") or []
    if not choices:
        return upstream
    message = (choices[0].get("message") or {})
    prose, calls = parse_tool_calls(message.get("content") or "")

    new_message: dict[str, Any] = {"role": "assistant", "content": prose or None}
    finish = choices[0].get("finish_reason", "stop")
    if calls:
        new_message["tool_calls"] = calls
        finish = "tool_calls"

    out = dict(upstream)
    out["choices"] = [{"index": 0, "message": new_message, "finish_reason": finish}]
    if model_name:
        out["model"] = model_name
    return out


class _Handler(BaseHTTPRequestHandler):
    """Translating reverse proxy. Configured via class attributes set in :func:`serve`."""

    upstream_url: str = "http://127.0.0.1:8081"
    model_name: str | None = None
    read_timeout_s: int = 1800
    default_max_tokens: int = 4096

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter than the default
        logger.debug("shim %s", fmt % args)

    # -- helpers ------------------------------------------------------------

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _upstream_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.upstream_url}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.read_timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    # -- routes -------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.rstrip("/") != "/v1/models":
            self._send_json(404, {"error": "not found"})
            return
        # Advertise the preset's model id. Swiftlet reports its raw arch string
        # ("qwen3_next"), which is not what the design named, and _wait_ready and
        # Hermes both match on the configured name.
        name = self.model_name or "swiftlet"
        self._send_json(200, {
            "object": "list",
            "data": [{"id": name, "object": "model", "owned_by": "swiftlet"}],
        })

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            request = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": f"malformed request: {exc}"})
            return

        messages = list(request.get("messages") or [])
        tools = request.get("tools") or []
        if tools:
            block = render_tools_prompt([
                t for t in tools if isinstance(t, dict)
            ])
            # Fold into an existing leading system turn when there is one, so the
            # template still renders exactly one system block.
            if messages and messages[0].get("role") == "system":
                head = dict(messages[0])
                head["content"] = f"{_content_to_text(head.get('content'))}\n\n{block}".strip()
                messages = [head] + messages[1:]
            else:
                messages = [{"role": "system", "content": block}] + messages

        payload = {
            "messages": downgrade_messages(messages),
            "stream": False,  # we must buffer to parse tool calls
            "max_tokens": int(
                request.get("max_tokens")
                or request.get("max_completion_tokens")
                or self.default_max_tokens
            ),
        }

        try:
            upstream = self._upstream_chat(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            logger.error("swiftlet-server %s: %s", exc.code, detail)
            self._send_json(502, {"error": f"swiftlet-server {exc.code}: {detail}"})
            return
        except Exception as exc:  # connection refused, timeout, bad JSON
            logger.error("swiftlet-server unreachable: %s", exc)
            self._send_json(502, {"error": f"swiftlet-server unreachable: {exc}"})
            return

        response = build_response(upstream, self.model_name)
        if request.get("stream"):
            self._send_synthetic_stream(response)
        else:
            self._send_json(200, response)

    def _send_synthetic_stream(self, response: dict[str, Any]) -> None:
        """Replay a buffered completion as SSE.

        Tool calls can only be recognised once the whole message is in hand, so we
        always call upstream non-streaming. A client that asked for a stream still
        gets well-formed SSE — just all at once.
        """
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        base = {
            "id": response.get("id", "chatcmpl-shim"),
            "object": "chat.completion.chunk",
            "created": response.get("created", 0),
            "model": response.get("model", self.model_name or "swiftlet"),
        }
        delta: dict[str, Any] = {"role": "assistant"}
        if message.get("content"):
            delta["content"] = message["content"]
        if message.get("tool_calls"):
            delta["tool_calls"] = [
                {**call, "index": i} for i, call in enumerate(message["tool_calls"])
            ]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for chunk in (
            {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {},
                                  "finish_reason": choice.get("finish_reason", "stop")}]},
        ):
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def serve(
    listen_host: str = "127.0.0.1",
    listen_port: int = 8080,
    upstream_host: str = "127.0.0.1",
    upstream_port: int = 8081,
    model_name: str | None = None,
    read_timeout_s: int = 1800,
    max_tokens: int = 4096,
) -> ThreadingHTTPServer:
    """Build the shim server (caller runs ``serve_forever``)."""
    handler = type("_BoundHandler", (_Handler,), {
        "upstream_url": f"http://{upstream_host}:{upstream_port}",
        "model_name": model_name,
        "read_timeout_s": read_timeout_s,
        "default_max_tokens": max_tokens,
    })
    return ThreadingHTTPServer((listen_host, listen_port), handler)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, default=8080)
    ap.add_argument("--upstream-host", default="127.0.0.1")
    ap.add_argument("--upstream-port", type=int, default=8081)
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--read-timeout-s", type=int, default=1800)
    ap.add_argument("--max-tokens", type=int, default=4096)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s swiftlet-shim %(message)s")
    server = serve(
        listen_host=args.listen_host, listen_port=args.listen_port,
        upstream_host=args.upstream_host, upstream_port=args.upstream_port,
        model_name=args.model_name, read_timeout_s=args.read_timeout_s,
        max_tokens=args.max_tokens,
    )
    logger.info("listening on %s:%d -> %s:%d (model %s)", args.listen_host,
                args.listen_port, args.upstream_host, args.upstream_port,
                args.model_name)
    server.serve_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
