package com.example.soccer;

import com.example.soccer.data.CsvLoader;
import com.example.soccer.model.Match;
import com.example.soccer.model.Player;
import com.example.soccer.query.HeadToHead;
import com.example.soccer.query.QueryEngine;
import com.example.soccer.query.TeamStats;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

public class QueryEngineTest {
    private static QueryEngine engine;

    @BeforeAll
    static void loadData() throws Exception {
        CsvLoader.Dataset ds = new CsvLoader().loadAll(CsvLoader.defaultDataDir());
        engine = new QueryEngine(ds.matches, ds.players);
    }

    @Test void findsMatchesBetweenTwoTeams() {
        List<Match> ms = engine.findMatches("Flamengo", "Fluminense", null, null, null, null, 200);
        assertFalse(ms.isEmpty(), "expected Fla-Flu matches");
        long flaFlu = ms.stream().filter(m -> {
            String c = (m.homeTeam + " " + m.awayTeam).toLowerCase();
            return c.contains("flamengo") && c.contains("fluminense");
        }).count();
        assertTrue(flaFlu >= 5, "expected several Fla-Flu derbies, got " + flaFlu);
    }

    @Test void teamStatsAreConsistent() {
        TeamStats s = engine.teamStats("Palmeiras", 2019, "Brasileirão", null);
        assertTrue(s.matches > 0);
        assertEquals(s.matches, s.wins + s.draws + s.losses);
        assertEquals(s.points, s.wins * 3 + s.draws);
    }

    @Test void headToHeadTotalsBalance() {
        HeadToHead h = engine.headToHead("Palmeiras", "Santos", null, null);
        assertTrue(h.totalMatches > 0);
        assertEquals(h.totalMatches, h.winsA + h.winsB + h.draws);
    }

    @Test void standings2019BrasileiraoHasFlamengoChampion() {
        List<TeamStats> st = engine.standings(2019, "Brasileirão");
        assertFalse(st.isEmpty());
        TeamStats top = st.get(0);
        assertTrue(top.team.toLowerCase().contains("flamengo"),
                "expected Flamengo at top, got " + top.team);
    }

    @Test void findsBrazilianPlayers() {
        List<Player> ps = engine.findPlayers(null, "Brazil", null, null, 85, 50);
        assertFalse(ps.isEmpty());
        assertTrue(ps.stream().allMatch(p -> "Brazil".equalsIgnoreCase(p.nationality)));
        assertTrue(ps.stream().allMatch(p -> p.overall >= 85));
    }

    @Test void findPlayersByName() {
        List<Player> ps = engine.findPlayers("Neymar", null, null, null, null, 5);
        assertTrue(ps.stream().anyMatch(p -> p.name.toLowerCase().contains("neymar")));
    }

    @Test void biggestWinsReturnsResults() {
        List<Match> ms = engine.biggestWins("Brasileirão", null, 5);
        assertEquals(5, ms.size());
        int first = Math.abs(ms.get(0).homeGoal - ms.get(0).awayGoal);
        int last = Math.abs(ms.get(4).homeGoal - ms.get(4).awayGoal);
        assertTrue(first >= last);
    }

    @Test void aggregateStatsReasonable() {
        Map<String, Object> r = engine.aggregateStats("Brasileirão", null);
        assertTrue(((Number) r.get("matches")).intValue() > 1000);
        double avg = ((Number) r.get("avg_goals_per_match")).doubleValue();
        assertTrue(avg > 1.5 && avg < 4.0, "avg goals out of expected range: " + avg);
    }
}
