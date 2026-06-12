"""Brazilian Soccer MCP Server.

An MCP (Model Context Protocol) server that exposes a knowledge-graph style
query interface over Brazilian soccer datasets (matches, teams, competitions
and FIFA player data).

Public entry points:
    create_server(data_dir)  -> a configured FastMCP server instance
    main()                   -> run the server over stdio (console_script)
"""

from .server import create_server, main

__all__ = ["create_server", "main"]
__version__ = "1.0.0"
