"""Entry point: ``python -m brazsoccer_mcp [--data-dir PATH]`` serves MCP over stdio.

Logs go to stderr so they never corrupt the JSON-RPC stream on stdout.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .mcp_server import run
from .store import SoccerData

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brazilian soccer MCP server")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("BRAZSOCCER_DATA_DIR", DEFAULT_DATA_DIR)),
        help="directory holding the Kaggle CSV files",
    )
    args = parser.parse_args(argv)

    data = SoccerData.load(args.data_dir)
    print(
        f"loaded {len(data.matches)} matches and {len(data.players)} players "
        f"from {args.data_dir}",
        file=sys.stderr,
    )
    run(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
