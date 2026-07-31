"""
Failure-mode tests: missing data, empty graphs, odd arguments.

Context
-------
An MCP server is long-lived and driven by a language model, so it must not fall
over when the data directory is wrong or when a tool is handed nonsense.  These
tests point the loader at an empty directory and at a hand-written mini dataset
to prove both the degraded and the from-scratch paths work.
"""

from __future__ import annotations

import json
import textwrap

import pytest

from brazilian_soccer import config
from brazilian_soccer.graph import build_knowledge_graph, load_knowledge_graph
from brazilian_soccer.tools import call_tool


@pytest.fixture
def empty_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(config.DATA_DIR_ENV_VAR, str(tmp_path))
    return tmp_path


def test_missing_files_are_reported_not_fatal(empty_data_dir):
    assert sorted(config.missing_datasets()) == sorted(
        spec.key for spec in config.DATASETS
    )
    graph = build_knowledge_graph()
    assert graph.matches == []
    assert graph.players == []
    assert len(graph.report.missing_files) == 6


def test_tools_still_answer_with_no_data(empty_data_dir):
    graph = build_knowledge_graph()
    result = call_tool("dataset_summary", {}, graph=graph)
    assert "Brasileirao_Matches.csv" in result.text
    assert result.data["report"]["missing_files"]

    empty = call_tool("search_matches", {"limit": 5}, graph=graph)
    assert empty.data["count"] == 0
    assert "No matches found" in empty.text


def test_dataset_path_rejects_unknown_keys():
    with pytest.raises(KeyError):
        config.dataset_path("not_a_dataset")


def test_data_dir_env_var_overrides_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv(config.DATA_DIR_ENV_VAR, str(tmp_path))
    assert config.data_dir() == tmp_path.resolve()
    monkeypatch.delenv(config.DATA_DIR_ENV_VAR)
    assert config.data_dir() == config.DEFAULT_DATA_DIR


def test_graph_cache_notices_a_different_data_directory(tmp_path, monkeypatch):
    real = load_knowledge_graph()
    monkeypatch.setenv(config.DATA_DIR_ENV_VAR, str(tmp_path))
    empty = load_knowledge_graph()
    assert empty is not real
    assert empty.matches == []
    monkeypatch.delenv(config.DATA_DIR_ENV_VAR)
    assert load_knowledge_graph().matches


# ---------------------------------------------------------------------------
# A tiny hand-written dataset exercises the full pipeline deterministically
# ---------------------------------------------------------------------------

MINI_BRASILEIRAO = textwrap.dedent(
    """\
    "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
    2019-05-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",3,0,2019,1
    2019-05-08 16:00:00,"Santos-SP","SP","Flamengo-RJ","RJ",1,1,2019,2
    2019-05-15 16:00:00,"Grêmio-RS","RS","Flamengo-RJ","RJ",0,2,2019,3
    2019-05-22 16:00:00,"Flamengo-RJ","RJ","Grêmio-RS","RS",1,0,2019,4
    2019-05-29 16:00:00,"Santos-SP","SP","Grêmio-RS","RS",2,2,2019,5
    2019-06-05 16:00:00,"Grêmio-RS","RS","Santos-SP","SP",0,1,2019,6
    """
)

MINI_FIFA = (
    ",ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,"
    "Height,Weight,Value,Wage,Preferred Foot,Work Rate,Joined,"
    "Contract Valid Until,Dribbling,Finishing\n"
    "0,1,Test Player,25,Brazil,80,85,Santos,ST,9,6'0,170lbs,€10M,€20K,Right,"
    "High/ Medium,\"Jul 1, 2015\",2021,82,84\n"
)


@pytest.fixture
def mini_graph(tmp_path, monkeypatch):
    (tmp_path / "Brasileirao_Matches.csv").write_text(MINI_BRASILEIRAO, encoding="utf-8")
    (tmp_path / "fifa_data.csv").write_text(MINI_FIFA, encoding="utf-8")
    monkeypatch.setenv(config.DATA_DIR_ENV_VAR, str(tmp_path))
    return build_knowledge_graph()


def test_mini_dataset_produces_a_correct_table(mini_graph):
    result = call_tool("competition_standings",
                       {"competition": "brasileirao", "season": 2019}, graph=mini_graph)
    table = result.data["standings"]
    assert [row["team"] for row in table] == ["Flamengo (RJ)", "Santos (SP)", "Grêmio (RS)"]
    assert [row["points"] for row in table] == [10, 5, 1]
    assert table[0]["wins"] == 3 and table[0]["draws"] == 1
    assert sum(row["goals_for"] for row in table) == sum(row["goals_against"] for row in table)


def test_mini_dataset_head_to_head(mini_graph):
    result = call_tool("head_to_head", {"team_a": "Flamengo", "team_b": "Santos"},
                       graph=mini_graph)
    assert result.data["played"] == 2
    assert result.data["team_a_wins"] == 1
    assert result.data["draws"] == 1
    assert result.data["team_a_goals"] == 4


def test_mini_dataset_links_a_player_to_a_club(mini_graph):
    result = call_tool("club_squad", {"club": "Santos"}, graph=mini_graph)
    assert result.data["squad_size"] == 1
    assert result.data["players"][0]["name"] == "Test Player"
    assert result.data["record"]["played"] == 4


def test_mini_dataset_accents_survive(mini_graph):
    result = call_tool("list_teams", {"limit": 10}, graph=mini_graph)
    assert "Grêmio" in result.text
    assert json.dumps(result.data, ensure_ascii=False).count("Grêmio") >= 1
