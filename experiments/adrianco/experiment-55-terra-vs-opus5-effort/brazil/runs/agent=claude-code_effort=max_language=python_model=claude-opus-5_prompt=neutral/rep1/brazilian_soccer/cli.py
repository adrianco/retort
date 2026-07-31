"""Terminal client for the same MCP tools.

Context
-------
Handy for demos and for checking behaviour without an MCP client attached.  It
drives the *server* rather than the query functions, so what it prints is what a
model would receive::

    python -m brazilian_soccer.cli tools
    python -m brazilian_soccer.cli call standings competition="Serie A" season=2019
    python -m brazilian_soccer.cli call find_matches team=Flamengo opponent=Fluminense limit=5
    python -m brazilian_soccer.cli demo --limit 5
    python -m brazilian_soccer.cli serve

Arguments are ``key=value`` pairs; values are parsed as JSON when possible
(``limit=5``, ``seasons=[2018,2019]``, ``ascending=true``) and treated as plain
strings otherwise.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import anyio

from .demo import SAMPLE_QUESTIONS, render_demo, run_demo
from .server import build_server

__all__ = ["main", "parse_value"]


def parse_value(raw: str) -> Any:
    """``"5"`` -> 5, ``"[2018,2019]"`` -> list, ``"Serie A"`` -> str."""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def _parse_arguments(pairs: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"Expected key=value, got {pair!r}")
        key, _, raw = pair.partition("=")
        arguments[key.strip()] = parse_value(raw.strip())
    return arguments


def _text(result: Any) -> str:
    return "\n".join(block.text for block in result.content if getattr(block, "text", None))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer",
        description="Query the Brazilian soccer knowledge graph from the terminal.",
    )
    parser.add_argument("--data-dir", default=None, help="Directory holding the Kaggle CSVs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("tools", help="List the MCP tools and their arguments")

    call_parser = subparsers.add_parser("call", help="Call one tool")
    call_parser.add_argument("tool")
    call_parser.add_argument("arguments", nargs="*", help="key=value pairs")

    demo_parser = subparsers.add_parser("demo", help="Answer the specification's sample questions")
    demo_parser.add_argument("--limit", type=int, default=None, help="Only the first N questions")

    serve_parser = subparsers.add_parser("serve", help="Run the MCP server")
    serve_parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "sse", "streamable-http"]
    )

    args = parser.parse_args(argv)
    server = build_server(data_dir=args.data_dir)

    if args.command == "tools":
        async def _list() -> None:
            for tool in await server.list_tools():
                parameters = ", ".join(tool.input_schema.get("properties", {}))
                summary = (tool.description or "").strip().splitlines()[0]
                print(f"{tool.name}({parameters})\n    {summary}")

        anyio.run(_list)
        return 0

    if args.command == "call":
        arguments = _parse_arguments(args.arguments)

        async def _call() -> None:
            result = await server.call_tool(args.tool, arguments)
            print(_text(result))

        anyio.run(_call)
        return 0

    if args.command == "demo":
        questions = SAMPLE_QUESTIONS[: args.limit] if args.limit else None
        print(render_demo(run_demo(questions=questions)))
        return 0

    if args.command == "serve":
        server.run(args.transport)
        return 0

    return 1  # pragma: no cover - argparse rejects unknown commands


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
