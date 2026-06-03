/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    query/SoccerQueries.java
 * Purpose: The query engine. Implements every capability the specification
 *          requires over the in-memory SoccerData knowledge base:
 *            - match search (by team, between two teams, by season/competition)
 *            - team statistics and head-to-head records
 *            - computed league standings and relegation
 *            - player search (name, nationality, club) and rating ranking
 *            - aggregate statistics (avg goals/match, biggest wins)
 *          All team matching goes through normalized keys (see TeamNames) so
 *          naming variations are handled consistently.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.SoccerData;
import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.QueryResults.HeadToHead;
import com.brazilsoccer.mcp.query.QueryResults.StandingRow;
import com.brazilsoccer.mcp.query.QueryResults.TeamStats;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class SoccerQueries {

    private final SoccerData data;

    public SoccerQueries(SoccerData data) {
        this.data = data;
    }

    public SoccerData data() {
        return data;
    }

    // ---- match queries -----------------------------------------------------

    /**
     * Find matches, filtered by any combination of: a single team (home or
     * away), competition, season, and date range. Null/blank arguments are
     * ignored. Results are sorted newest first.
     */
    public List<Match> findMatches(String team, String competition, Integer season,
                                   LocalDate from, LocalDate to) {
        String teamKey = TeamNames.key(team);
        String compKey = competition == null ? "" : TeamNames.key(competition);
        List<Match> out = new ArrayList<>();
        for (Match m : data.matches()) {
            if (!teamKey.isEmpty()
                    && !TeamNames.matches(m.homeTeamKey(), teamKey)
                    && !TeamNames.matches(m.awayTeamKey(), teamKey)) {
                continue;
            }
            if (!compKey.isEmpty() && !TeamNames.key(m.competition()).contains(compKey)) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            if (from != null && (m.date() == null || m.date().isBefore(from))) {
                continue;
            }
            if (to != null && (m.date() == null || m.date().isAfter(to))) {
                continue;
            }
            out.add(m);
        }
        out.sort(byDateDescending());
        return out;
    }

    /** Find every match between two specific teams, newest first. */
    public List<Match> findMatchesBetween(String teamA, String teamB) {
        String a = TeamNames.key(teamA);
        String b = TeamNames.key(teamB);
        List<Match> out = new ArrayList<>();
        for (Match m : data.matches()) {
            boolean aHome = TeamNames.matches(m.homeTeamKey(), a);
            boolean aAway = TeamNames.matches(m.awayTeamKey(), a);
            boolean bHome = TeamNames.matches(m.homeTeamKey(), b);
            boolean bAway = TeamNames.matches(m.awayTeamKey(), b);
            if ((aHome && bAway) || (aAway && bHome)) {
                out.add(m);
            }
        }
        out.sort(byDateDescending());
        return out;
    }

    /** Head-to-head summary between two teams. */
    public HeadToHead headToHead(String teamA, String teamB) {
        String a = TeamNames.key(teamA);
        List<Match> games = findMatchesBetween(teamA, teamB);
        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        for (Match m : games) {
            if (!m.hasScore()) {
                continue;
            }
            boolean aIsHome = TeamNames.matches(m.homeTeamKey(), a);
            int forA = aIsHome ? m.homeGoal() : m.awayGoal();
            int forB = aIsHome ? m.awayGoal() : m.homeGoal();
            aGoals += forA;
            bGoals += forB;
            if (forA > forB) {
                aWins++;
            } else if (forB > forA) {
                bWins++;
            } else {
                draws++;
            }
        }
        return new HeadToHead(canonicalName(teamA), canonicalName(teamB),
                games.size(), aWins, bWins, draws, aGoals, bGoals);
    }

    // ---- team queries ------------------------------------------------------

    /**
     * Aggregate statistics for a team across matches matching the optional
     * competition/season filters. {@code homeOnly}/{@code awayOnly} restrict to
     * home or away games respectively.
     */
    public TeamStats teamStats(String team, String competition, Integer season,
                               boolean homeOnly, boolean awayOnly) {
        String teamKey = TeamNames.key(team);
        String compKey = competition == null ? "" : TeamNames.key(competition);
        int matches = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        for (Match m : data.matches()) {
            if (!compKey.isEmpty() && !TeamNames.key(m.competition()).contains(compKey)) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            boolean isHome = TeamNames.matches(m.homeTeamKey(), teamKey);
            boolean isAway = TeamNames.matches(m.awayTeamKey(), teamKey);
            if (!isHome && !isAway) {
                continue;
            }
            if (homeOnly && !isHome) {
                continue;
            }
            if (awayOnly && !isAway) {
                continue;
            }
            if (!m.hasScore()) {
                continue;
            }
            int forT = isHome ? m.homeGoal() : m.awayGoal();
            int against = isHome ? m.awayGoal() : m.homeGoal();
            matches++;
            gf += forT;
            ga += against;
            if (forT > against) {
                wins++;
            } else if (forT < against) {
                losses++;
            } else {
                draws++;
            }
        }
        return new TeamStats(canonicalName(team), matches, wins, draws, losses, gf, ga);
    }

    // ---- competition queries ----------------------------------------------

    /**
     * Compute a league table for a competition and season from match results
     * (3 points for a win, 1 for a draw). Sorted by points, then goal
     * difference, then goals for.
     */
    public List<StandingRow> standings(String competition, int season) {
        String compKey = competition == null ? "" : TeamNames.key(competition);
        // The same league season is present in several source files with
        // inconsistent team-name spellings. Computing a table by merging them
        // would invent phantom teams and double-count games, so we build the
        // table from a single source: the file with the most matches for this
        // competition and season (within one file naming is consistent).
        Map<String, List<Match>> bySource = new HashMap<>();
        for (Match m : data.matches()) {
            if (m.season() == null || m.season() != season) {
                continue;
            }
            if (!compKey.isEmpty() && !TeamNames.key(m.competition()).contains(compKey)) {
                continue;
            }
            if (!m.hasScore()) {
                continue;
            }
            bySource.computeIfAbsent(m.source(), k -> new ArrayList<>()).add(m);
        }
        // Prefer a dedicated competition file (consistent naming) over the
        // aggregate BR-Football file, which mixes spellings of the same club;
        // fall back to it only when it is the sole source (e.g. Série B/C).
        List<Match> chosen = bySource.entrySet().stream()
                .max(Comparator
                        .comparingInt((Map.Entry<String, List<Match>> e) ->
                                e.getKey().equals("BR-Football-Dataset.csv") ? 0 : 1)
                        .thenComparingInt(e -> e.getValue().size()))
                .map(Map.Entry::getValue)
                .orElse(List.of());

        Map<String, int[]> table = new HashMap<>(); // key -> [P,W,D,L,GF,GA]
        Map<String, String> names = new HashMap<>();
        for (Match m : chosen) {
            accumulate(table, names, m.homeTeamKey(), m.homeTeam(), m.homeGoal(), m.awayGoal());
            accumulate(table, names, m.awayTeamKey(), m.awayTeam(), m.awayGoal(), m.homeGoal());
        }
        List<StandingRow> rows = new ArrayList<>();
        for (Map.Entry<String, int[]> e : table.entrySet()) {
            int[] s = e.getValue();
            int points = s[1] * 3 + s[2];
            rows.add(new StandingRow(0, names.get(e.getKey()),
                    s[0], s[1], s[2], s[3], s[4], s[5], points));
        }
        rows.sort(Comparator
                .comparingInt(StandingRow::points).reversed()
                .thenComparing(Comparator.comparingInt(StandingRow::goalDifference).reversed())
                .thenComparing(Comparator.comparingInt(StandingRow::goalsFor).reversed())
                .thenComparing(StandingRow::team));
        // Assign 1-based positions.
        List<StandingRow> ranked = new ArrayList<>(rows.size());
        for (int i = 0; i < rows.size(); i++) {
            StandingRow r = rows.get(i);
            ranked.add(new StandingRow(i + 1, r.team(), r.played(), r.wins(), r.draws(),
                    r.losses(), r.goalsFor(), r.goalsAgainst(), r.points()));
        }
        return ranked;
    }

    private static void accumulate(Map<String, int[]> table, Map<String, String> names,
                                   String key, String name, int gf, int ga) {
        if (key == null || key.isEmpty()) {
            return;
        }
        names.putIfAbsent(key, name);
        int[] s = table.computeIfAbsent(key, k -> new int[6]);
        s[0]++;          // played
        s[4] += gf;      // goals for
        s[5] += ga;      // goals against
        if (gf > ga) {
            s[1]++;      // win
        } else if (gf < ga) {
            s[3]++;      // loss
        } else {
            s[2]++;      // draw
        }
    }

    // ---- player queries ----------------------------------------------------

    /** Players whose name contains the query (case-insensitive, accent-tolerant). */
    public List<Player> searchPlayersByName(String name, int limit) {
        String q = TeamNames.key(name);
        List<Player> out = new ArrayList<>();
        for (Player p : data.players()) {
            if (q.isEmpty() || TeamNames.key(p.name()).contains(q)) {
                out.add(p);
            }
        }
        out.sort(byOverallDescending());
        return cap(out, limit);
    }

    /**
     * Players filtered by any combination of nationality, club and position,
     * sorted by overall rating (highest first).
     */
    public List<Player> findPlayers(String nationality, String club, String position, int limit) {
        String nat = nationality == null ? "" : TeamNames.key(nationality);
        String clubKey = club == null ? "" : TeamNames.key(club);
        String pos = position == null ? "" : position.trim().toLowerCase();
        List<Player> out = new ArrayList<>();
        for (Player p : data.players()) {
            if (!nat.isEmpty() && !p.nationalityKey().equals(nat)) {
                continue;
            }
            if (!clubKey.isEmpty() && !TeamNames.matches(p.clubKey(), clubKey)) {
                continue;
            }
            if (!pos.isEmpty()) {
                String pp = p.position() == null ? "" : p.position().toLowerCase();
                if (!pp.equals(pos)) {
                    continue;
                }
            }
            out.add(p);
        }
        out.sort(byOverallDescending());
        return cap(out, limit);
    }

    // ---- statistical analysis ---------------------------------------------

    /** Average goals per scored match, optionally filtered by competition/season. */
    public double averageGoalsPerMatch(String competition, Integer season) {
        String compKey = competition == null ? "" : TeamNames.key(competition);
        long totalGoals = 0;
        int counted = 0;
        for (Match m : data.matches()) {
            if (!compKey.isEmpty() && !TeamNames.key(m.competition()).contains(compKey)) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            if (!m.hasScore()) {
                continue;
            }
            totalGoals += m.totalGoals();
            counted++;
        }
        return counted == 0 ? 0.0 : (double) totalGoals / counted;
    }

    /** Matches with the largest goal margin, optionally filtered, largest first. */
    public List<Match> biggestWins(String competition, Integer season, int limit) {
        List<Match> filtered = findMatches(null, competition, season, null, null);
        filtered.removeIf(m -> !m.hasScore() || m.homeGoal().equals(m.awayGoal()));
        filtered.sort(Comparator
                .comparingInt((Match m) -> Math.abs(m.homeGoal() - m.awayGoal())).reversed()
                .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        return cap(filtered, limit);
    }

    // ---- helpers -----------------------------------------------------------

    /** The most common raw spelling for a team key, for display. */
    private String canonicalName(String team) {
        String key = TeamNames.key(team);
        Map<String, Integer> counts = new HashMap<>();
        String best = team == null ? "" : team.trim();
        int bestCount = -1;
        for (Match m : data.matches()) {
            if (m.homeTeamKey().equals(key)) {
                int c = counts.merge(m.homeTeam(), 1, Integer::sum);
                if (c > bestCount) { bestCount = c; best = m.homeTeam(); }
            }
            if (m.awayTeamKey().equals(key)) {
                int c = counts.merge(m.awayTeam(), 1, Integer::sum);
                if (c > bestCount) { bestCount = c; best = m.awayTeam(); }
            }
        }
        return best;
    }

    private static Comparator<Match> byDateDescending() {
        return Comparator.comparing(
                (Match m) -> m.date() == null ? LocalDate.MIN : m.date()).reversed();
    }

    private static Comparator<Player> byOverallDescending() {
        return Comparator.comparing(
                (Player p) -> p.overall() == null ? Integer.MIN_VALUE : p.overall()).reversed();
    }

    private static <T> List<T> cap(List<T> list, int limit) {
        if (limit > 0 && list.size() > limit) {
            return new ArrayList<>(list.subList(0, limit));
        }
        return list;
    }
}
