"""Model Context Protocol server over stdio.

Context
-------
Implements the MCP JSON-RPC 2.0 wire protocol directly on the standard library
so that the server has **no third-party dependencies** and can be launched by
any MCP client with ``python -m brazilian_soccer.server``.

Supported methods:

``initialize``            handshake, advertises the ``tools`` and ``resources``
                          capabilities and negotiates the protocol version
``notifications/initialized``  acknowledged silently
``ping``                  liveness check
``tools/list``            the sixteen tools from :mod:`brazilian_soccer.tools`
``tools/call``            run a tool, returning text + ``structuredContent``
``resources/list``        the six source CSV files as readable resources
``resources/read``        a description of one source file
``prompts/list``          a small set of ready-made question templates

Framing is one JSON object per line, which is what the MCP stdio transport
specifies.  Anything written to stdout that is not a response would corrupt the
stream, so all logging goes to stderr.

Run it directly for a smoke test::

    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \\
        python -m brazilian_soccer.server
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, IO

from . import __version__
from .graph import KnowledgeGraph, load_graph
from .loaders import SOURCES
from .tools import TOOLS_BY_NAME, call_tool, list_tools

__all__ = ["MCPServer", "main", "SERVER_INFO", "PROTOCOL_VERSION"]

#: Protocol revision this server implements.  If a client asks for a different
#: revision we echo theirs back when we recognise it, else offer ours.
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

SERVER_INFO = {
    "name": "brazilian-soccer",
    "title": "Brazilian Soccer Knowledge Graph",
    "version": __version__,
}

INSTRUCTIONS = """\
This server answers questions about Brazilian club football from six Kaggle
datasets: Campeonato Brasileiro Série A (2003-2023), Série B and C (2014-2023),
Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and the FIFA 19
player database.

Guidance:
* Club names may be written any way you like -- "Palmeiras", "Palmeiras-SP",
  "SE Palmeiras" all work. If a name is ambiguous (Botafogo, Atlético, América)
  call `resolve_team` first.
* Standings, records and averages are computed from match results; overlapping
  fixtures across the source files are merged so nothing is double counted.
* The data has no goalscorer, lineup or referee columns, so individual
  top-scorer questions cannot be answered.
* FIFA 19 only licensed 15 Brazilian clubs and anonymises their player names,
  so `club_squad` returns nothing for Flamengo, Palmeiras, Corinthians,
  São Paulo or Vasco da Gama.
* Call `dataset_summary` to check coverage before saying data is missing.
"""


# ---------------------------------------------------------------------------
# JSON-RPC plumbing
# ---------------------------------------------------------------------------

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPServer:
    """A stdio MCP server.  Also usable in-process for tests."""

    def __init__(self, graph: KnowledgeGraph | None = None,
                 data_dir: str | Path | None = None):
        self._graph = graph
        self._data_dir = data_dir
        self.initialized = False

    # -- lazily build the graph so `initialize` returns quickly -----------
    @property
    def graph(self) -> KnowledgeGraph:
        if self._graph is None:
            self._graph = load_graph(self._data_dir)
        return self._graph

    # -- request handling -------------------------------------------------
    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC request; returns ``None`` for notifications."""
        # Echo the client's id whenever we can read one: a client correlating
        # replies by id can never resolve a call we answer with id null.
        request_id = request.get("id") if isinstance(request, dict) else None
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return _error_response(request_id, INVALID_REQUEST,
                                   "Expected a JSON-RPC 2.0 request object.")
        method = request.get("method")
        if not isinstance(method, str):
            return _error_response(request_id, INVALID_REQUEST, "Missing method.")
        is_notification = request_id is None

        params = request.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            # Positional parameters are legal JSON-RPC but no MCP method uses
            # them, so this is a client bug -- report it as Invalid Params
            # rather than letting it surface as an internal error.
            return None if is_notification else _error_response(
                request_id, INVALID_PARAMS,
                "'params' must be an object; this server takes no positional "
                "parameters.")

        handler = getattr(self, f"_do_{method.replace('/', '_').replace('.', '_')}", None)
        if handler is None:
            if is_notification:
                return None
            return _error_response(request_id, METHOD_NOT_FOUND,
                                   f"Unknown method {method!r}.")
        try:
            result = handler(params)
        except _RpcError as exc:
            return None if is_notification else _error_response(
                request_id, exc.code, exc.message)
        except Exception as exc:  # pragma: no cover - safety net
            return None if is_notification else _error_response(
                request_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    # -- methods ----------------------------------------------------------
    def _do_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        self.initialized = True
        return {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        }

    def _do_notifications_initialized(self, params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _do_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def _do_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"tools": list_tools()}

    def _do_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str):
            raise _RpcError(INVALID_PARAMS, "tools/call requires a 'name' string.")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise _RpcError(INVALID_PARAMS, "'arguments' must be an object.")
        return call_tool(name, arguments, graph=self.graph)

    def _do_resources_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "resources": [
                {
                    "uri": f"dataset://kaggle/{source.filename}",
                    "name": source.filename,
                    "title": source.description,
                    "description": source.description,
                    "mimeType": "text/csv",
                }
                for source in SOURCES
            ]
        }

    def _do_resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri", "")
        filename = str(uri).rsplit("/", 1)[-1]
        source = next((s for s in SOURCES if s.filename == filename), None)
        if source is None:
            raise _RpcError(INVALID_PARAMS, f"Unknown resource {uri!r}.")
        rows = self.graph.report.rows_read.get(source.filename, 0)
        path = Path(self.graph.data_dir) / source.filename
        header = ""
        if path.is_file():
            with path.open("r", encoding="utf-8-sig") as handle:
                header = handle.readline().strip()
        text = (f"{source.filename}\n{source.description}\n"
                f"Rows loaded: {rows}\nPath: {path}\nColumns: {header}\n")
        return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": text}]}

    def _do_prompts_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"prompts": [
            {"name": "season-review",
             "title": "Review a Brasileirão season",
             "description": "Standings, champion, relegation and scoring trends "
                            "for one season.",
             "arguments": [{"name": "season", "description": "Season year",
                            "required": True}]},
            {"name": "derby-report",
             "title": "Derby report",
             "description": "Head-to-head history of a classic rivalry.",
             "arguments": [{"name": "team_a", "description": "First club",
                            "required": True},
                           {"name": "team_b", "description": "Second club",
                            "required": True}]},
        ]}

    def _do_prompts_get(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "season-review":
            season = arguments.get("season", "2019")
            text = (f"Review the {season} Campeonato Brasileiro Série A. Use the "
                    "standings tool for the final table, competition_stats for "
                    "scoring trends and biggest_wins for the standout results.")
        elif name == "derby-report":
            text = (f"Report on the rivalry between {arguments.get('team_a')} and "
                    f"{arguments.get('team_b')}: use head_to_head for the overall "
                    "record and find_matches for the recent meetings.")
        else:
            raise _RpcError(INVALID_PARAMS, f"Unknown prompt {name!r}.")
        return {"messages": [{"role": "user",
                              "content": {"type": "text", "text": text}}]}

    # -- transport --------------------------------------------------------
    def serve(self, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> None:
        """Read line-delimited JSON-RPC from *stdin* and write replies."""
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                _write(stdout, _error_response(None, PARSE_ERROR, f"Invalid JSON: {exc}"))
                continue
            if isinstance(request, list):  # JSON-RPC batch
                if not request:
                    # An empty batch is an Invalid Request, not silence.
                    _write(stdout, _error_response(
                        None, INVALID_REQUEST, "Batch must not be empty."))
                    continue
                responses = [r for r in (self.handle(item) for item in request)
                             if r is not None]
                if responses:
                    _write(stdout, responses)
                continue
            response = self.handle(request)
            if response is not None:
                _write(stdout, response)


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def _write(stream: IO[str], payload: Any) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    stream.flush()


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer-mcp",
        description="MCP server exposing a Brazilian football knowledge graph.")
    parser.add_argument("--data-dir", default=None,
                        help="Directory holding the Kaggle CSV files "
                             "(default: ./data/kaggle or $BR_SOCCER_DATA).")
    parser.add_argument("--preload", action="store_true",
                        help="Build the knowledge graph before accepting requests.")
    parser.add_argument("--self-test", action="store_true",
                        help="Load the data, print a summary and exit.")
    args = parser.parse_args(argv)

    server = MCPServer(data_dir=args.data_dir)
    if args.self_test:
        summary = call_tool("dataset_summary", {}, graph=server.graph)
        print(summary["content"][0]["text"])
        print(f"\n{len(TOOLS_BY_NAME)} tools registered: "
              + ", ".join(sorted(TOOLS_BY_NAME)))
        return 0
    if args.preload:
        _ = server.graph
        print(f"brazilian-soccer MCP server ready "
              f"({len(server.graph.matches)} matches, "
              f"{len(server.graph.players)} players)", file=sys.stderr)
    server.serve()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
