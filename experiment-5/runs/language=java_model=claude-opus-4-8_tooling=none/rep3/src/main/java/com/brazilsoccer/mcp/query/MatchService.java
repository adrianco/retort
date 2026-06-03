/*
 * ============================================================================
 * MatchService.java
 * ============================================================================
 * Context:
 *   Implements the spec's "Match Queries" category: find matches by team(s),
 *   competition, season and/or date range across every loaded dataset. All
 *   team matching goes through accent-insensitive keys (TeamNames.key) so user
 *   input like "Sao Paulo" matches "São Paulo-SP".
 *
 *   Results are returned most-recent-first and capped by an optional limit so
 *   tool responses stay readable.
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.Competitions;
import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.model.Match;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Query service for finding matches by various criteria. */
public final class MatchService {

    private final DataStore store;

    public MatchService(DataStore store) {
        this.store = store;
    }

    /** Criteria for {@link #search(Criteria)}; all fields optional/nullable. */
    public static final class Criteria {
        public String team;          // a participant (home or away)
        public String opponent;      // restrict to matches also involving this team
        public String competition;   // substring match against competition name
        public Integer season;
        public LocalDate from;       // inclusive
        public LocalDate to;         // inclusive
        public int limit = 50;       // 0 or negative = unlimited
    }

    /**
     * Find matches satisfying every supplied criterion, sorted most-recent
     * first (matches without a date sort last).
     */
    public List<Match> search(Criteria c) {
        String teamKey = c.team == null ? null : TeamNames.key(c.team);
        String oppKey = c.opponent == null ? null : TeamNames.key(c.opponent);

        List<Match> out = new ArrayList<>();
        for (Match m : store.matches()) {
            if (teamKey != null && !teamMatches(m, teamKey)) continue;
            if (oppKey != null && !teamMatches(m, oppKey)) continue;
            if (c.season != null && m.season() != c.season) continue;
            if (c.competition != null && !Competitions.matches(m.competition(), c.competition)) continue;
            if (c.from != null && (m.date() == null || m.date().isBefore(c.from))) continue;
            if (c.to != null && (m.date() == null || m.date().isAfter(c.to))) continue;
            out.add(m);
        }

        out.sort(Comparator.comparing(
                (Match m) -> m.date() == null ? LocalDate.MIN : m.date()).reversed());

        if (c.limit > 0 && out.size() > c.limit) {
            return new ArrayList<>(out.subList(0, c.limit));
        }
        return out;
    }

    /** True if the given match involves the team identified by {@code key}. */
    public static boolean teamMatches(Match m, String key) {
        return keyMatches(m.homeTeamKey(), key) || keyMatches(m.awayTeamKey(), key);
    }

    /**
     * Match two team keys: exact match, or (for queries of 4+ chars) a
     * substring match so partial names like "atletico" find "atleticomg".
     */
    public static boolean keyMatches(String teamKey, String queryKey) {
        if (teamKey == null || queryKey == null || queryKey.isEmpty()) return false;
        if (teamKey.equals(queryKey)) return true;
        return queryKey.length() >= 4 && teamKey.contains(queryKey);
    }
}
