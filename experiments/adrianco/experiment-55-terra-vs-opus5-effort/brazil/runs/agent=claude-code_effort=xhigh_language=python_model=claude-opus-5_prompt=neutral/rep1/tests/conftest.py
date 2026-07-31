"""
Shared pytest fixtures and the BDD step vocabulary.

Context
-------
Building the knowledge graph reads ~43k CSV rows, so it is built **once** per
session and shared by every test (``graph`` fixture).  Tests never mutate it.

The BDD layer (``tests/features/*.feature``) is deliberately built on a tiny,
reusable step vocabulary so new scenarios can be written without new Python:

    Given the knowledge graph is loaded
    When I call the "head_to_head" tool with {"team_a": "Flamengo", ...}
    Then the answer contains "Fla-Flu"
    And the field "played" is at least 30
    And every returned match has a date, a score and a competition

Steps operate on the same :func:`brazilian_soccer.tools.call_tool` entry point
the MCP server uses, so a passing scenario proves the served behaviour.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from brazilian_soccer.graph import build_knowledge_graph
from brazilian_soccer.tools import ToolResult, call_tool


@pytest.fixture(scope="session")
def graph():
    """The knowledge graph, built once for the whole test session."""

    return build_knowledge_graph()


@pytest.fixture
def context(graph) -> dict[str, Any]:
    """Mutable per-scenario state shared between BDD steps."""

    return {"graph": graph}


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("the knowledge graph is loaded", target_fixture="context")
def _graph_loaded(graph) -> dict[str, Any]:
    assert graph.matches, "the graph should contain matches"
    assert graph.players, "the graph should contain players"
    return {"graph": graph}


@given("the match data is loaded", target_fixture="context")
def _match_data_loaded(graph) -> dict[str, Any]:
    assert graph.matches_by_competition["serie-a"], "Serie A matches should be loaded"
    return {"graph": graph}


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


def _invoke(context: dict[str, Any], tool: str, arguments: dict[str, Any]) -> ToolResult:
    started = time.perf_counter()
    result = call_tool(tool, arguments, graph=context["graph"])
    context["elapsed"] = time.perf_counter() - started
    context["tool"] = tool
    context["arguments"] = arguments
    context["result"] = result
    return result


@when(parsers.parse('I call the "{tool}" tool with {arguments}'))
def _call_tool_with(context: dict[str, Any], tool: str, arguments: str) -> None:
    _invoke(context, tool, json.loads(arguments))


@when(parsers.parse('I call the "{tool}" tool'))
def _call_tool(context: dict[str, Any], tool: str) -> None:
    _invoke(context, tool, {})


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


def _result(context: dict[str, Any]) -> ToolResult:
    result = context.get("result")
    assert result is not None, "no tool has been called yet"
    return result


def _dig(data: Any, path: str) -> Any:
    """Follow a dotted path, e.g. ``standings.0.team``."""

    current = data
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        else:
            assert isinstance(current, dict), f"cannot read {part!r} from {type(current)}"
            assert part in current, f"missing key {part!r}; have {sorted(current)}"
            current = current[part]
    return current


@then(parsers.parse('the answer contains "{needle}"'))
def _answer_contains(context: dict[str, Any], needle: str) -> None:
    text = _result(context).text
    assert needle in text, f"expected {needle!r} in answer:\n{text}"


@then(parsers.parse('the answer does not contain "{needle}"'))
def _answer_excludes(context: dict[str, Any], needle: str) -> None:
    text = _result(context).text
    assert needle not in text, f"did not expect {needle!r} in answer:\n{text}"


@then(parsers.parse('the field "{path}" equals {expected}'))
def _field_equals(context: dict[str, Any], path: str, expected: str) -> None:
    actual = _dig(_result(context).data, path)
    assert actual == json.loads(expected), f"{path} == {actual!r}, expected {expected}"


@then(parsers.parse('the field "{path}" is at least {minimum:d}'))
def _field_at_least(context: dict[str, Any], path: str, minimum: int) -> None:
    actual = _dig(_result(context).data, path)
    assert actual >= minimum, f"{path} == {actual!r}, expected >= {minimum}"


@then(parsers.parse('the field "{path}" contains "{needle}"'))
def _field_contains(context: dict[str, Any], path: str, needle: str) -> None:
    actual = _dig(_result(context).data, path)
    assert needle in str(actual), f"{path} == {actual!r}, expected to contain {needle!r}"


@then("every returned match has a date, a score and a competition")
def _matches_well_formed(context: dict[str, Any]) -> None:
    matches = _result(context).data.get("matches")
    assert matches, "expected the payload to include matches"
    for match in matches:
        assert match["date"], f"match without a date: {match}"
        assert match["home_goals"] is not None and match["away_goals"] is not None, match
        assert match["competition"], match
        assert match["home_team"] and match["away_team"], match


@then("every returned player has a name, a rating and a club")
def _players_well_formed(context: dict[str, Any]) -> None:
    players = _result(context).data.get("players")
    assert players, "expected the payload to include players"
    for player in players:
        assert player["name"], player
        assert player["overall"] is not None, player
        assert player["club"], player


@then(parsers.parse("the payload lists at least {minimum:d} items under \"{path}\""))
def _payload_length(context: dict[str, Any], minimum: int, path: str) -> None:
    items = _dig(_result(context).data, path)
    assert len(items) >= minimum, f"{path} had {len(items)} items, expected >= {minimum}"


@then(parsers.parse("the call completes in under {seconds:g} seconds"))
def _call_fast(context: dict[str, Any], seconds: float) -> None:
    elapsed = context["elapsed"]
    assert elapsed < seconds, f"call took {elapsed:.3f}s, budget was {seconds}s"


@then("the answer reports no results rather than failing")
def _graceful_empty(context: dict[str, Any]) -> None:
    result = _result(context)
    assert result.text.strip(), "an empty-result answer should still explain itself"
    lowered = result.text.lower()
    assert any(word in lowered for word in ("no ", "not ", "does not", "cannot")), result.text
