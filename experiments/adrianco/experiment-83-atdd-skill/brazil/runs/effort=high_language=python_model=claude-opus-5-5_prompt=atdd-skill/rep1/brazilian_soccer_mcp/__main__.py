"""Run the Brazilian soccer MCP server over stdio: python -m brazilian_soccer_mcp [--data-dir DIR]"""
import argparse
import logging
import sys
import time
from pathlib import Path

from brazilian_soccer_mcp.data import SoccerData
from brazilian_soccer_mcp.knowledge import SoccerKnowledge
from brazilian_soccer_mcp.server import McpServer, serve

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "kaggle"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Brazilian soccer knowledge MCP server (stdio)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA), help="Directory holding the Kaggle CSV files")
    options = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = time.perf_counter()
    data = SoccerData.load(options.data_dir)
    logging.info("Loaded %d matches and %d players from %s in %.2fs", len(data.matches), len(data.players),
                 options.data_dir, time.perf_counter() - started)
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    serve(McpServer(SoccerKnowledge(data)))


if __name__ == "__main__":
    main()
