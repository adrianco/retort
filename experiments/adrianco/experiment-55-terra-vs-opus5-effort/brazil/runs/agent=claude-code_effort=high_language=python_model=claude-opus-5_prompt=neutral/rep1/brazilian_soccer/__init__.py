"""Brazilian Soccer MCP Server.

Context
-------
A knowledge-graph interface over six Kaggle datasets covering Brazilian club
football -- Campeonato Brasileiro Série A/B/C, Copa do Brasil, Copa
Libertadores and the FIFA 19 player database -- exposed to LLMs through the
Model Context Protocol.

Module map:

``normalization``  low-level text/date/number cleaning
``clubs``          curated club registry + team-name resolver
``competitions``   competition registry and aliases
``models``         ``Team`` / ``Match`` / ``Player`` dataclasses
``loaders``        one reader per CSV file
``graph``          the deduplicated, indexed knowledge graph
``queries``        the query API that every MCP tool calls
``formatting``     human-readable rendering of query results
``tools``          MCP tool schemas + dispatch
``server``         JSON-RPC-over-stdio MCP server
``cli``            command line client for local exploration and demos
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
