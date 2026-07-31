"""
Unit tests for the domain model.

Context
-------
The derived properties on :class:`~brazilian_soccer.models.Match` and
:class:`~brazilian_soccer.models.TeamRecord` are used by every aggregate in the
query layer, and several of them have to behave sensibly when a score is
missing (the Copa do Brasil file has ``NA`` scores and one Libertadores row has
no data at all).  These tests pin the edge cases directly.
"""

from __future__ import annotations

import datetime as dt

import pytest

from brazilian_soccer.models import (
    COMPETITIONS,
    HeadToHead,
    Match,
    Player,
    StandingRow,
    Team,
    TeamRecord,
    competition_name,
)


def make_match(home_goals=2, away_goals=1, **overrides) -> Match:
    defaults = dict(
        id="m1", competition_id="serie-a", season=2019, date=dt.date(2019, 5, 5),
        home_team_id="flamengo-rj", away_team_id="santos-sp",
        home_goals=home_goals, away_goals=away_goals,
        home_team_raw="Flamengo-RJ", away_team_raw="Santos-SP",
    )
    defaults.update(overrides)
    return Match(**defaults)


def test_home_win():
    match = make_match(2, 1)
    assert match.result == "H"
    assert match.winner_id == "flamengo-rj"
    assert match.loser_id == "santos-sp"
    assert match.total_goals == 3
    assert match.goal_difference == 1


def test_away_win():
    match = make_match(0, 3)
    assert match.result == "A"
    assert match.winner_id == "santos-sp"
    assert match.loser_id == "flamengo-rj"


def test_draw():
    match = make_match(1, 1)
    assert match.result == "D"
    assert match.winner_id is None and match.loser_id is None


def test_match_without_a_score_is_inert():
    match = make_match(None, None)
    assert match.has_score is False
    assert match.result is None
    assert match.total_goals is None
    assert match.goal_difference is None
    assert match.winner_id is None
    assert match.goals_for("flamengo-rj") is None


def test_goals_for_and_against_by_side():
    match = make_match(2, 1)
    assert match.goals_for("flamengo-rj") == 2
    assert match.goals_against("flamengo-rj") == 1
    assert match.goals_for("santos-sp") == 1
    assert match.goals_against("santos-sp") == 2


def test_uninvolved_team_gets_nothing():
    match = make_match()
    assert match.involves("palmeiras-sp") is False
    assert match.opponent_of("palmeiras-sp") is None
    assert match.goals_for("palmeiras-sp") is None
    assert match.goals_against("palmeiras-sp") is None


def test_opponent_of():
    match = make_match()
    assert match.opponent_of("flamengo-rj") == "santos-sp"
    assert match.opponent_of("santos-sp") == "flamengo-rj"


def test_match_to_dict_uses_display_names_when_given():
    match = make_match()
    plain = match.to_dict()
    assert plain["home_team"] == "Flamengo-RJ"
    named = match.to_dict({"flamengo-rj": "Flamengo (RJ)", "santos-sp": "Santos (SP)"})
    assert named["home_team"] == "Flamengo (RJ)"
    assert named["date"] == "2019-05-05"
    assert named["competition"] == "Campeonato Brasileiro Série A"


def test_match_to_dict_handles_a_missing_date():
    assert make_match(date=None).to_dict()["date"] is None


def test_team_record_accumulates():
    record = TeamRecord(team_id="x", team_name="X")
    record.add(2, 1)
    record.add(1, 1)
    record.add(0, 3)
    assert (record.played, record.wins, record.draws, record.losses) == (3, 1, 1, 1)
    assert record.points == 4
    assert record.goals_for == 3 and record.goals_against == 5
    assert record.goal_difference == -2
    assert record.win_rate == pytest.approx(33.3, abs=0.1)
    assert record.points_per_game == pytest.approx(1.333, abs=0.001)
    assert record.goals_for_per_game == pytest.approx(1.0)


def test_empty_record_does_not_divide_by_zero():
    record = TeamRecord(team_id="x", team_name="X")
    assert record.win_rate == 0.0
    assert record.points_per_game == 0.0
    assert record.goals_for_per_game == 0.0
    assert record.to_dict()["points"] == 0


def test_standing_row_serialises_position_and_note():
    record = TeamRecord(team_id="x", team_name="X")
    row = StandingRow(position=1, record=record, note="Champion")
    assert row.to_dict()["position"] == 1
    assert row.to_dict()["note"] == "Champion"


def test_head_to_head_played_is_the_sum_of_outcomes():
    record = HeadToHead(team_a_id="a", team_a="A", team_b_id="b", team_b="B",
                        team_a_wins=3, team_b_wins=2, draws=1)
    assert record.played == 6
    assert record.to_dict()["played"] == 6


@pytest.mark.parametrize(
    "team, expected",
    [
        (Team(id="a", name="Botafogo", state="RJ"), "Botafogo (RJ)"),
        (Team(id="b", name="Boca Juniors", country="ARG"), "Boca Juniors (ARG)"),
        (Team(id="c", name="Mystery", country=""), "Mystery"),
    ],
)
def test_team_display_name(team, expected):
    assert team.display_name == expected
    assert team.to_dict()["display_name"] == expected


def test_player_helpers():
    player = Player(id=1, name="Someone", nationality="Brazil", overall=80,
                    skills={"Dribbling": 90, "Finishing": 70, "Passing": 80})
    assert player.is_brazilian is True
    assert player.top_skills(2) == [("Dribbling", 90), ("Passing", 80)]
    assert player.to_dict()["top_skills"][0] == {"skill": "Dribbling", "rating": 90}


def test_non_brazilian_player():
    assert Player(id=2, name="Other", nationality="Argentina").is_brazilian is False
    assert Player(id=3, name="Unknown").is_brazilian is False


def test_competition_name_falls_back_to_the_id():
    assert competition_name("serie-a") == "Campeonato Brasileiro Série A"
    assert competition_name("unknown-cup") == "unknown-cup"


def test_every_competition_has_aliases():
    for competition in COMPETITIONS:
        assert competition.aliases
        assert competition.kind in {"league", "cup"}
