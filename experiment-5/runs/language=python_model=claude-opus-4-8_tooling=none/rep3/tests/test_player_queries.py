# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : tests.test_player_queries
# Purpose : BDD scenarios for category 3 (Player Queries): search by name,
#           nationality, club, position and rating against the FIFA dataset.
# =============================================================================


class TestPlayerSearch:
    """Feature: Find player information."""

    def test_search_by_name(self, graph):
        # When I search for "Neymar"
        results = graph.find_players(name="Neymar")
        # Then Neymar Jr is returned
        assert any("Neymar" in p.name for p in results)

    def test_search_by_nationality(self, graph):
        # When I ask for Brazilian players
        brazilians = graph.find_players(nationality="Brazil")
        # Then many are returned and all are Brazilian
        assert len(brazilians) > 100
        assert all(p.nationality == "Brazil" for p in brazilians)

    def test_top_brazilians_sorted_by_overall(self, graph):
        top = graph.find_players(nationality="Brazil", sort_by="overall", limit=5)
        overalls = [p.overall for p in top]
        assert overalls == sorted(overalls, reverse=True)
        # Neymar is the top-rated Brazilian in this dataset
        assert top[0].name.startswith("Neymar")

    def test_search_by_club(self, graph):
        # When I list players for a Brazilian club present in the data
        santos = graph.find_players(club="Santos")
        assert len(santos) > 0
        assert all("santos" in p.club_norm for p in santos)

    def test_filter_by_position(self, graph):
        gks = graph.find_players(position="GK", limit=10)
        assert all(p.position == "GK" for p in gks)

    def test_min_overall_filter(self, graph):
        elite = graph.find_players(min_overall=90)
        assert all(p.overall >= 90 for p in elite)


class TestPlayerClubSummary:
    """Feature: Brazilian players grouped by club."""

    def test_summary_sorted_by_count(self, graph):
        summary = graph.players_by_club_summary(nationality="Brazil")
        assert len(summary) > 0
        counts = [row["players"] for row in summary]
        assert counts == sorted(counts, reverse=True)
        # Each row carries an average rating
        assert all("avg_overall" in row for row in summary)
