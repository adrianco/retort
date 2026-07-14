/*
 * ============================================================================
 * StatsService.java
 * ============================================================================
 * Context:
 *   Implements the spec's "Statistical Analysis" category: average goals per
 *   match, home win rate, biggest victories, and top-scoring teams. When a
 *   specific competition + season is requested, the underlying match set is
 *   de-duplicated via CompetitionService.dedupedMatches so overlapping source
 *   files don't skew the averages. Cross-competition "biggest wins" style
 *   queries scan the whole corpus.
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.Competitions;
import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Query service for aggregate statistics. */
public final class StatsService {

    private final DataStore store;

    public StatsService(DataStore store) {
        this.store = store;
    }

    /** Aggregate league statistics over a filtered match set. */
    public static final class LeagueStats {
        public int matches;
        public int totalGoals;
        public int homeWins;
        public int awayWins;
        public int draws;

        public double goalsPerMatch() {
            return matches == 0 ? 0.0 : (double) totalGoals / matches;
        }
        public double homeWinRate() {
            return matches == 0 ? 0.0 : (homeWins * 100.0) / matches;
        }
        public double awayWinRate() {
            return matches == 0 ? 0.0 : (awayWins * 100.0) / matches;
        }
        public double drawRate() {
            return matches == 0 ? 0.0 : (draws * 100.0) / matches;
        }
    }

    /**
     * Compute league-wide statistics. If both competition and season are given,
     * the de-duplicated single-source view is used; otherwise all scored
     * matches matching the (optional) filters are considered.
     */
    public LeagueStats leagueStats(String competition, Integer season) {
        LeagueStats s = new LeagueStats();
        for (Match m : selectMatches(competition, season)) {
            if (!m.hasScore()) continue;
            s.matches++;
            s.totalGoals += m.totalGoals();
            if (m.homeGoal() > m.awayGoal()) s.homeWins++;
            else if (m.homeGoal() < m.awayGoal()) s.awayWins++;
            else s.draws++;
        }
        return s;
    }

    /** Biggest victories (largest goal margin) over a filtered match set. */
    public List<Match> biggestWins(String competition, Integer season, int limit) {
        List<Match> scored = new ArrayList<>();
        for (Match m : selectMatches(competition, season)) {
            if (m.hasScore()) scored.add(m);
        }
        scored.sort(Comparator
                .comparingInt((Match m) -> Math.abs(m.homeGoal() - m.awayGoal())).reversed()
                .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        if (limit > 0 && scored.size() > limit) {
            return new ArrayList<>(scored.subList(0, limit));
        }
        return scored;
    }

    /** Teams ranked by total goals scored over a filtered match set. */
    public List<TeamRecord> topScoringTeams(String competition, Integer season, int limit) {
        Map<String, TeamRecord> table = new HashMap<>();
        for (Match m : selectMatches(competition, season)) {
            if (!m.hasScore()) continue;
            table.computeIfAbsent(m.homeTeamKey(), k -> new TeamRecord(m.homeTeam()))
                    .add(m.homeGoal(), m.awayGoal());
            table.computeIfAbsent(m.awayTeamKey(), k -> new TeamRecord(m.awayTeam()))
                    .add(m.awayGoal(), m.homeGoal());
        }
        List<TeamRecord> rows = new ArrayList<>(table.values());
        rows.sort(Comparator.comparingInt((TeamRecord r) -> r.goalsFor).reversed()
                .thenComparing(r -> r.team));
        if (limit > 0 && rows.size() > limit) {
            return new ArrayList<>(rows.subList(0, limit));
        }
        return rows;
    }

    /**
     * Filter the canonical (already de-duplicated) match set by the optional
     * competition and season criteria.
     */
    private List<Match> selectMatches(String competition, Integer season) {
        List<Match> out = new ArrayList<>();
        for (Match m : store.matches()) {
            if (season != null && m.season() != season) continue;
            if (competition != null && !Competitions.matches(m.competition(), competition)) continue;
            out.add(m);
        }
        return out;
    }
}
