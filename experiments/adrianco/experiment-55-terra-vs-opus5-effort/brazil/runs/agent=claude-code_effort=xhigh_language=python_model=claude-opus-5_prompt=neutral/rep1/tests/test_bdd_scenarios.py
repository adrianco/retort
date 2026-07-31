"""
Binds every ``tests/features/*.feature`` file to pytest.

Context
-------
The step definitions live in ``tests/conftest.py`` so they are shared by all
feature files; this module only has to declare which features to run.  Each
scenario drives the same ``call_tool`` entry point the MCP server uses, so a
green run is evidence about the served behaviour, not just the library.
"""

from __future__ import annotations

from pytest_bdd import scenarios

scenarios("match_queries.feature")
scenarios("team_queries.feature")
scenarios("player_queries.feature")
scenarios("competition_queries.feature")
scenarios("statistics.feature")
scenarios("data_quality.feature")
scenarios("knowledge_graph.feature")
scenarios("performance.feature")
