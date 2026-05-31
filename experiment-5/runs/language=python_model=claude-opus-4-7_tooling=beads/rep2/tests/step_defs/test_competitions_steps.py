"""Step definitions for ``features/competitions.feature``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from soccer_mcp import competitions as comp_mod

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "competitions.feature"))


@pytest.fixture
def context() -> dict:
    return {}


@given("the match data is loaded")
def _data_loaded(data):
    assert len(data.matches) > 0


@when("I compute the 2019 Brasileirão champion")
def _champion(data, context):
    context["champion"] = comp_mod.champion(data, "Brasileirão", 2019)


@when("I compute the 2019 Brasileirão standings")
def _standings(data, context):
    context["standings"] = comp_mod.standings(data, "Brasileirão", 2019)


@then('the champion\'s name should contain "Flamengo"')
def _champion_name(context):
    assert context["champion"] is not None
    assert "Flamengo" in context["champion"]["team"]


@then("I should receive at least 16 teams")
def _enough_teams(context):
    assert len(context["standings"]) >= 16


@then("every row should have a position assigned")
def _positions(context):
    for row in context["standings"]:
        assert row["position"] >= 1


@then("rows should be sorted by points descending")
def _sort_desc(context):
    points = [row["points"] for row in context["standings"]]
    assert points == sorted(points, reverse=True)
