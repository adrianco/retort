#!/usr/bin/env python3
"""Main entry point for the Brazilian Soccer MCP Server."""

import uvicorn
from src.api import app


def main():
    """Run the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
