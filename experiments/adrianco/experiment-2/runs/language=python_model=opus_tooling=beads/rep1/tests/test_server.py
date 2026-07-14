"""Feature: MCP server tool dispatch."""
import json

from soccer_mcp.server import TOOL_DEFS, build_server, dispatch, _format_result


def test_all_tools_have_schema():
    names = {t["name"] for t in TOOL_DEFS}
    for name in ["find_matches", "head_to_head", "team_record", "standings",
                 "find_players", "biggest_wins", "average_goals",
                 "top_scoring_teams", "dataset_summary"]:
        assert name in names


def test_dispatch_returns_serializable_results(engine):
    out = dispatch(engine, "dataset_summary", {})
    text = _format_result(out)
    assert "fifa_players" in text

    text = _format_result(dispatch(engine, "average_goals", {"competition": "Brasileirão"}))
    payload = json.loads(text)
    assert payload["matches"] > 0


def test_build_server_registers_tools(engine):
    server = build_server(engine)
    assert server.name == "brazilian-soccer"


def test_unknown_tool_raises(engine):
    import pytest
    with pytest.raises(ValueError):
        dispatch(engine, "does_not_exist", {})
