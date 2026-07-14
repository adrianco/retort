"""
Integration tests against the real Kaggle datasets in ``data/kaggle``.

These verify end-to-end behaviour and answer the >= 20 sample questions from
TASK.md, plus the data-coverage and performance success criteria. The KB is
loaded once for the whole module.
"""
import os
import time

import pytest

from brazilian_soccer.knowledge_base import SoccerKB
from brazilian_soccer import service as svc

DATA_DIR = "data/kaggle"

pytestmark = pytest.mark.skipif(
    not os.path.isdir(DATA_DIR),
    reason="real datasets not present",
)


@pytest.fixture(scope="module")
def kb():
    return SoccerKB.from_data_dir(DATA_DIR)


# --- data coverage ---------------------------------------------------------

class TestDataCoverage:
    def test_all_six_files_contribute(self, kb):
        # 5 match files collapse (after cross-source de-duplication) into the
        # match set; the FIFA file becomes the player set.
        assert len(kb.matches) > 15000
        assert len(kb.players) == 18207
        # Every competition label has matches, i.e. all match files contribute.
        from collections import Counter
        by_comp = Counter(m.competition for m in kb.matches)
        for comp in ("Brasileirão Série A", "Brasileirão Série B",
                     "Brasileirão Série C", "Copa do Brasil", "Copa Libertadores"):
            assert by_comp[comp] > 0

    def test_five_competitions_present(self, kb):
        comps = set(kb.list_competitions())
        assert comps == {
            "Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C",
            "Copa do Brasil", "Copa Libertadores",
        }

    def test_historical_and_recent_seasons(self, kb):
        seasons = kb.list_seasons("Brasileirão Série A")
        assert 2003 in seasons  # novo_campeonato (Brazilian date format)
        assert 2019 in seasons
        assert max(seasons) >= 2022


# --- performance -----------------------------------------------------------

class TestPerformance:
    def test_load_under_5s(self):
        start = time.time()
        SoccerKB.from_data_dir(DATA_DIR)
        assert time.time() - start < 5.0

    def test_simple_lookup_under_2s(self, kb):
        start = time.time()
        kb.find_matches(team="Flamengo", opponent="Corinthians")
        assert time.time() - start < 2.0

    def test_aggregate_under_5s(self, kb):
        start = time.time()
        kb.standings("Brasileirão Série A", 2019)
        kb.competition_stats(competition="Brasileirão Série A")
        assert time.time() - start < 5.0


# --- sample questions from the spec ---------------------------------------

class TestSampleQuestions:
    # Match queries
    def test_q01_flamengo_vs_fluminense(self, kb):
        res = kb.find_matches(team="Flamengo", opponent="Fluminense")
        assert len(res) > 10  # the Fla-Flu derby has many meetings

    def test_q02_palmeiras_matches_in_2019(self, kb):
        res = kb.find_matches(team="Palmeiras", competition="Brasileirão Série A",
                              season=2019)
        assert len(res) == 38  # full 20-team double round robin

    def test_q03_copa_do_brasil_matches_exist(self, kb):
        res = kb.find_matches(competition="Copa do Brasil")
        assert len(res) > 100

    def test_q04_corinthians_home_record_2017(self, kb):
        rec = kb.team_record("Corinthians", competition="Brasileirão Série A",
                             season=2017, venue="home")
        assert rec["matches"] == 19
        assert rec["wins"] + rec["draws"] + rec["losses"] == 19

    def test_q05_most_goals_serie_a_2019_is_flamengo(self, kb):
        table = kb.standings("Brasileirão Série A", 2019)
        top_scorer = max(table, key=lambda r: r["goals_for"])
        assert top_scorer["team"] == "Flamengo"

    def test_q06_compare_palmeiras_santos_head_to_head(self, kb):
        h2h = kb.head_to_head("Palmeiras", "Santos")
        assert h2h["total"] > 10
        assert h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"] == h2h["total"]

    # Player queries
    def test_q07_all_brazilian_players(self, kb):
        res = kb.search_players(nationality="Brazil")
        assert len(res) == 827

    def test_q08_top_brazilian_player_is_neymar(self, kb):
        res = kb.search_players(nationality="Brazil")
        assert res[0].name == "Neymar Jr"
        assert res[0].overall == 92

    def test_q09_players_at_a_brazilian_club(self, kb):
        # Grêmio is present in the FIFA 2019 club column (accent handling).
        res = kb.search_players(club="Grêmio")
        assert len(res) == 20

    def test_q10_brazilian_forwards(self, kb):
        res = kb.search_players(nationality="Brazil", position="ST")
        assert len(res) > 0
        assert all(p.position == "ST" and p.nationality == "Brazil" for p in res)

    def test_q11_who_is_gabriel_jesus(self, kb):
        res = kb.search_players(name="Gabriel Jesus")
        assert any(p.name == "Gabriel Jesus" for p in res)

    # Competition queries
    def test_q12_who_won_2019_brasileirao(self, kb):
        table = kb.standings("Brasileirão Série A", 2019)
        assert table[0]["team"] == "Flamengo"
        assert table[0]["points"] == 90

    def test_q13_who_won_2017_brasileirao(self, kb):
        table = kb.standings("Brasileirão Série A", 2017)
        assert table[0]["team"] == "Corinthians"

    def test_q14_libertadores_has_a_final_stage(self, kb):
        finals = [m for m in kb.find_matches(competition="Copa Libertadores")
                  if m.stage == "final"]
        assert len(finals) > 0

    # Statistical analysis
    def test_q15_average_goals_per_match(self, kb):
        stats = kb.competition_stats(competition="Brasileirão Série A")
        assert 2.0 < stats["avg_goals_per_match"] < 3.5

    def test_q16_home_win_rate_is_plausible(self, kb):
        stats = kb.competition_stats(competition="Brasileirão Série A")
        assert 40 < stats["home_win_rate"] < 60

    def test_q17_biggest_wins(self, kb):
        res = kb.biggest_wins(competition="Copa Libertadores", limit=5)
        margins = [abs(m.home_score - m.away_score) for m in res]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7

    def test_q18_best_home_record_team(self, kb):
        # "Which team has the best home record?" within 2019 Serie A.
        table = kb.standings("Brasileirão Série A", 2019)
        best = None
        for r in table:
            rec = kb.team_record(r["team"], competition="Brasileirão Série A",
                                 season=2019, venue="home")
            if best is None or rec["points"] > best[1]:
                best = (r["team"], rec["points"])
        assert best[0] == "Flamengo"

    # Simple lookups / relationship
    def test_q19_when_did_flamengo_last_play_corinthians(self, kb):
        res = kb.find_matches(team="Flamengo", opponent="Corinthians", limit=1)
        assert len(res) == 1  # most recent meeting (sorted desc)

    def test_q20_what_competitions_has_palmeiras_played_in(self, kb):
        comps = {m.competition for m in kb.find_matches(team="Palmeiras")}
        assert "Brasileirão Série A" in comps
        assert "Copa Libertadores" in comps

    # Cross-file query (player + match data)
    def test_q21_cross_file_team_has_both_players_and_matches(self, kb):
        santos_players = kb.search_players(club="Santos")
        santos_matches = kb.find_matches(team="Santos",
                                         competition="Brasileirão Série A")
        assert len(santos_players) > 0
        assert len(santos_matches) > 0


# --- formatted answers end-to-end -----------------------------------------

class TestFormattedAnswers:
    def test_standings_answer_mentions_champion(self, kb):
        out = svc.answer_standings(kb, "Brasileirão Série A", 2019)
        assert "Flamengo - 90 pts" in out

    def test_find_matches_answer_has_h2h(self, kb):
        out = svc.answer_find_matches(kb, team="Flamengo", opponent="Fluminense")
        assert "Head-to-head" in out
