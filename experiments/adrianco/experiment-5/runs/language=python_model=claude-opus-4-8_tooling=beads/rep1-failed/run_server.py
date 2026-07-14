#!/usr/bin/env python3
"""
================================================================================
Context
================================================================================
Project   : Brazilian Soccer MCP Server
File      : run_server.py
Purpose   : Convenience entry point to launch the MCP server over stdio.

Equivalent to `python -m brazilian_soccer.server`. Configure an MCP client (e.g.
Claude Desktop) to run this script. See README.md for a sample config.
================================================================================
"""

from brazilian_soccer.server import main

if __name__ == "__main__":
    main()
