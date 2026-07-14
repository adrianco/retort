#!/usr/bin/env python3
"""
================================================================================
run_server.py - Convenience launcher for the Brazilian Soccer MCP server
================================================================================

CONTEXT
-------
Thin entry point so the server can be started with ``python run_server.py``
(handy for MCP client config) without remembering the module path. All logic
lives in ``brazilian_soccer_mcp.server``.
================================================================================
"""

from brazilian_soccer_mcp.server import main

if __name__ == "__main__":
    main()
