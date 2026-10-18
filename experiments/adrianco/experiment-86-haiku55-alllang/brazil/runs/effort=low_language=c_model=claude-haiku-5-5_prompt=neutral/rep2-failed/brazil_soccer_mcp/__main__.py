"""Run the MCP server over stdio: `python -m brazil_soccer_mcp [--data-dir PATH]`."""

import argparse
from pathlib import Path

from .server import DEFAULT_DATA_DIR, serve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Directory with the Kaggle CSVs")
    args = parser.parse_args()
    serve(data_dir=args.data_dir)


if __name__ == "__main__":
    main()
