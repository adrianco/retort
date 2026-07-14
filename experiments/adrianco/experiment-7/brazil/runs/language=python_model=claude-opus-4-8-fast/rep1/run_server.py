#!/usr/bin/env python3
"""
================================================================================
run_server.py
================================================================================

CONTEXT
-------
Convenience launcher for the Brazilian Soccer MCP server. Equivalent to
``python -m brazilian_soccer_mcp.server``; provided so the server can be started
with a single, discoverable command and registered in MCP client configs.

Usage:
    python run_server.py
================================================================================
"""

from brazilian_soccer_mcp.server import main

if __name__ == "__main__":
    main()
