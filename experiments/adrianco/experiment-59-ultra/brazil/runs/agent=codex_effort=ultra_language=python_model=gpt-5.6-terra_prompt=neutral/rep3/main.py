"""Compatibility entry point for MCP clients that invoke ``main.py``."""

from server import main


if __name__ == "__main__":
    raise SystemExit(main())
