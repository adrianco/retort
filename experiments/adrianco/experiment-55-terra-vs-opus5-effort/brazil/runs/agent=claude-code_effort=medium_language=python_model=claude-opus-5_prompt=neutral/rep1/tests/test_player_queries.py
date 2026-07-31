"""Feature: Player Queries.

Context
-------
The FIFA file is a FIFA 19 (2018/19) snapshot: 18,207 players, 827 of them
Brazilian, with 20-player squads for most Brazilian first-division clubs.  These
scenarios cover search by name/nationality/club/position, the cross-file link
from a player to their club's match record, and the honest "no exact match"
behaviour for players the snapshot does not contain.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.formatting import format_player, format_players
from brazilian_soccer.queries import SoccerQueries


class TestSearchByName:
    @pytest.mark.parametrize("name", ["Neymar", "Casemiro", "Marcelo", "Alisson"])
    def test_known_players_are_found(self, queries: SoccerQueries, name: str) -> None:
        # Given the FIFA player data is loaded
        # When I search for a well-known Brazilian
        player = queries.get_player(name)
        # Then the player comes back with ratings and a club
        assert player is not None
        assert name.lower() in player.name.lower()
        assert player.overall is not None and player.overall > 0

    def test_multi_token_names_prefer_full_matches(self, queries: SoccerQueries) -> None:
        # When I search a two-word name
        player = queries.get_player("Thiago Silva")
        # Then the player matching both words wins over any single-word Thiago
        assert player.name == "Thiago Silva"
        assert player.nationality == "Brazil"

    def test_accents_are_optional(self, queries: SoccerQueries) -> None:
        with_accent = queries.get_player("Coutinho")
        assert with_accent is not None
        # Searching without accents finds accented names too
        assert queries.search_players(name="jose", limit=5)

    def test_absent_player_is_reported_as_inexact(self, queries: SoccerQueries) -> None:
        # Given Gabriel Barbosa is not in the FIFA 19 snapshot
        result = queries.lookup_player("Gabriel Barbosa")
        # Then a closest match is offered, flagged as not exact
        assert result["player"] is not None
        assert result["exact"] is False
        assert result["alternatives"]

    def test_exact_matches_are_flagged(self, queries: SoccerQueries) -> None:
        result = queries.lookup_player("Neymar")
        assert result["exact"] is True

    def test_nonsense_name_finds_nothing(self, queries: SoccerQueries) -> None:
        assert queries.get_player("Zzzqqxwv") is None
        assert queries.lookup_player("Zzzqqxwv")["player"] is None


class TestFilters:
    def test_by_nationality(self, queries: SoccerQueries) -> None:
        # When I ask for Brazilian players
        players = queries.search_players(nationality="Brazil", limit=1000)
        # Then every one of them is Brazilian and they are sorted by rating
        assert len(players) > 500
        assert {p.nationality for p in players} == {"Brazil"}
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)
        assert players[0].name == "Neymar Jr"

    def test_by_club(self, queries: SoccerQueries) -> None:
        # When I ask who plays for Grêmio
        players = queries.search_players(club="Gremio", limit=50)
        # Then the whole squad comes back, accented club name and all
        assert len(players) >= 15
        assert all("Grêmio" in p.club_raw for p in players)

    def test_by_club_and_position(self, queries: SoccerQueries) -> None:
        keepers = queries.search_players(club="Santos", position="GK", limit=10)
        assert keepers
        assert all(p.position == "GK" for p in keepers)
        assert all("Santos" in p.club_raw for p in keepers)

    def test_by_minimum_rating(self, queries: SoccerQueries) -> None:
        elite = queries.search_players(nationality="Brazil", min_overall=85, limit=50)
        assert elite
        assert all(p.overall >= 85 for p in elite)

    def test_by_age_range(self, queries: SoccerQueries) -> None:
        youngsters = queries.search_players(
            nationality="Brazil", max_age=20, limit=50, sort_by="potential"
        )
        assert youngsters
        assert all(p.age <= 20 for p in youngsters)
        potentials = [p.potential for p in youngsters]
        assert potentials == sorted(potentials, reverse=True)

    @pytest.mark.parametrize("sort_by", ["overall", "potential", "age", "name"])
    def test_sorting_options(self, queries: SoccerQueries, sort_by: str) -> None:
        players = queries.search_players(
            nationality="Brazil", sort_by=sort_by, limit=20
        )
        values = [getattr(p, sort_by if sort_by != "name" else "name") for p in players]
        if sort_by in {"overall", "potential"}:
            assert values == sorted(values, reverse=True)
        else:
            assert values == sorted(values)

    def test_limit_is_respected(self, queries: SoccerQueries) -> None:
        assert len(queries.search_players(nationality="Brazil", limit=7)) == 7


class TestSquads:
    def test_club_squad_reports_average_rating(self, queries: SoccerQueries) -> None:
        squad = queries.club_squad("Cruzeiro")
        assert squad["players_found"] >= 15
        assert 50 <= squad["average_overall"] <= 90
        ratings = [p.overall for p in squad["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_brazilian_players_grouped_by_club(self, queries: SoccerQueries) -> None:
        # "Brazilian players at Brazilian clubs" from the spec's answer format
        rows = queries.players_by_nationality_at_clubs("Brazil", limit=10)
        assert rows
        assert all(row["players"] > 0 for row in rows)
        assert all(row["average_overall"] is not None for row in rows)
        # And the biggest squads come first
        counts = [row["players"] for row in rows]
        assert counts == sorted(counts, reverse=True)

    def test_unknown_club_yields_no_players(self, queries: SoccerQueries) -> None:
        assert queries.club_squad("Nonexistent Athletic")["players_found"] == 0


class TestCrossFileQueries:
    def test_player_club_also_exists_in_match_data(self, queries: SoccerQueries) -> None:
        # Given a player from the FIFA file
        player = queries.search_players(club="Gremio", limit=1)[0]
        # When their club is looked up in the match graph
        record = queries.team_record(player.club_key)
        # Then the club's match record is available -- a genuine cross-file join
        assert record.played > 100
        assert record.team_key == "gremio"

    def test_top_brazilian_clubs_link_both_ways(self, queries: SoccerQueries) -> None:
        for club in ("Cruzeiro", "Fluminense", "Internacional", "Bahia"):
            squad = queries.club_squad(club)
            profile = queries.team_profile(club)
            assert squad["players_found"] > 0
            assert profile["fifa_players"] == squad["players_found"]


class TestPlayerFormatting:
    def test_player_line_has_the_spec_fields(self, queries: SoccerQueries) -> None:
        text = format_player(queries.get_player("Neymar"))
        assert "Overall:" in text and "Position:" in text and "Club:" in text

    def test_detailed_view_adds_attributes(self, queries: SoccerQueries) -> None:
        text = format_player(queries.get_player("Neymar"), detailed=True)
        assert "Top attributes:" in text
        assert "Value:" in text

    def test_player_list_is_numbered(self, queries: SoccerQueries) -> None:
        text = format_players(
            queries.search_players(nationality="Brazil", limit=3), "Top Brazilians:"
        )
        assert text.startswith("Top Brazilians:")
        assert "\n1. " in text and "\n3. " in text

    def test_empty_player_list_is_explicit(self) -> None:
        assert "No players found" in format_players([], "Nobody:")
