"""
Command line interface.

Context
-------
The MCP server speaks JSON-RPC over stdio, which is awkward to poke at by hand.
This CLI exposes exactly the same tool layer so the knowledge graph can be
exercised directly::

    brazilian-soccer-mcp serve                       # run the MCP server
    brazilian-soccer-mcp tools                       # list tools + arguments
    brazilian-soccer-mcp summary                     # dataset coverage report
    brazilian-soccer-mcp call head_to_head team_a=Flamengo team_b=Fluminense
    brazilian-soccer-mcp call competition_standings season=2019 --json

``call`` accepts ``key=value`` pairs (JSON-decoded when possible, so
``limit=5``, ``seasons=[2018,2019]`` and ``brazilian_clubs_only=true`` all work)
or a single ``--args '{"...": ...}'`` JSON object.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .graph import load_knowledge_graph
from .tools import call_tool, list_tools


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_pairs(pairs: Sequence[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"argument {pair!r} is not in key=value form")
        key, _, value = pair.partition("=")
        arguments[key.strip()] = _parse_value(value)
    return arguments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer-mcp",
        description="Brazilian soccer knowledge graph -- MCP server and CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="run the MCP server")
    serve.add_argument("--transport", default="stdio",
                       choices=["stdio", "sse", "streamable-http"])

    subparsers.add_parser("tools", help="list the available tools")
    subparsers.add_parser("summary", help="print the dataset coverage report")

    call = subparsers.add_parser("call", help="call one tool")
    call.add_argument("tool")
    call.add_argument("pairs", nargs="*", help="key=value arguments")
    call.add_argument("--args", dest="args_json", help="arguments as a JSON object")
    call.add_argument("--json", dest="as_json", action="store_true",
                      help="print the structured payload instead of the text answer")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        from .server import main as serve_main

        serve_main(args.transport)
        return 0

    if args.command == "tools":
        for spec in list_tools():
            print(f"{spec['name']}\n    {spec['description']}")
            for name, description in spec["parameters"].items():
                print(f"      - {name}: {description}")
            print()
        return 0

    if args.command == "summary":
        print(call_tool("dataset_summary", graph=load_knowledge_graph()).text)
        return 0

    if args.command == "call":
        arguments = _parse_pairs(args.pairs)
        if args.args_json:
            arguments.update(json.loads(args.args_json))
        try:
            result = call_tool(args.tool, arguments)
        except KeyError as error:
            print(error, file=sys.stderr)
            return 2
        if args.as_json:
            print(json.dumps(result.data, indent=2, ensure_ascii=False, default=str))
        else:
            print(result.text)
        return 0

    parser.error(f"unknown command {args.command!r}")  # pragma: no cover
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
