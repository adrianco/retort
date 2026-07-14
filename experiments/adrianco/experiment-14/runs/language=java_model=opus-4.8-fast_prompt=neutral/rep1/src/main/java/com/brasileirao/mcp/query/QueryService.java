/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : QueryService.java
 *  Purpose : Implement every query capability required by the specification on
 *            top of the in-memory KnowledgeGraph.
 *
 *  Context : This is the analytical heart of the server. It answers the five
 *            categories from the spec:
 *              1. Match queries      - searchMatches()
 *              2. Team queries       - teamRecord(), headToHead()
 *              3. Player queries     - searchPlayers()
 *              4. Competition queries- standings()
 *              5. Statistics         - averageGoals(), biggestWins(),
 *                                      bestRecords()
 *            Results are returned as small immutable records so they can be
 *            asserted in unit tests and formatted independently by the MCP
 *            layer. All team-name matching goes through TeamNames so the many
 *            spellings collapse to one club. Standings, records and stats are
 *            computed live from match results (points = 3/1/0).
 *
 *  Used by : McpServer (formatting) and the test suite (assertions).
 * ============================================================================
 */
package com.brasileirao.mcp.query;

import com.brasileirao.mcp.data.KnowledgeGraph;
import com.brasileirao.mcp.model.Match;
import com.brasileirao.mcp.model.Player;
import com.brasileirao.mcp.util.TeamNames;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Read-only query/analytics API over the knowledge graph. */
public final class QueryService {

    private final KnowledgeGraph graph;

    public QueryService(KnowledgeGraph graph) {
        this.graph = graph;
    }

    public KnowledgeGraph graph() {
        return graph;
    }

    // ================================================================ 1. Matches

    /** Criteria for {@link #searchMatches(MatchQuery)}. Any field may be null. */
    public static final class MatchQuery {
        public String team;          // either side
        public String homeTeam;      // home side only
        public String awayTeam;      // away side only
        public String opponent;      // combined with team -> head to head pairing
        public String competition;   // partial/accent-insensitive competition name
        public Integer season;
        public LocalDate dateFrom;
        public LocalDate dateTo;
        public int limit = 50;
    }

    /** Return matches matching every supplied criterion, newest first. */
    public List<Match> searchMatches(MatchQuery q) {
        String team = canon(q.team);
        String opponent = canon(q.opponent);
        String homeTeam = canon(q.homeTeam);
        String awayTeam = canon(q.awayTeam);
        String competition = q.competition == null ? null : normalize(q.competition);

        // Start from the smallest candidate set we can.
        List<Match> candidates;
        if (team != null) {
            candidates = graph.matchesForTeam(q.team);
        } else if (homeTeam != null) {
            candidates = graph.matchesForTeam(q.homeTeam);
        } else if (awayTeam != null) {
            candidates = graph.matchesForTeam(q.awayTeam);
        } else {
            candidates = graph.matches();
        }

        List<Match> out = new ArrayList<>();
        for (Match m : candidates) {
            if (team != null && !m.involves(team)) {
                continue;
            }
            if (opponent != null && !m.involves(opponent)) {
                continue;
            }
            if (homeTeam != null && !m.homeTeam().equals(homeTeam)) {
                continue;
            }
            if (awayTeam != null && !m.awayTeam().equals(awayTeam)) {
                continue;
            }
            if (competition != null && !normalize(m.competition()).contains(competition)) {
                continue;
            }
            if (q.season != null && !q.season.equals(m.season())) {
                continue;
            }
            if (q.dateFrom != null && (m.date() == null || m.date().isBefore(q.dateFrom))) {
                continue;
            }
            if (q.dateTo != null && (m.date() == null || m.date().isAfter(q.dateTo))) {
                continue;
            }
            out.add(m);
        }
        out.sort(matchChronological().reversed());
        if (q.limit > 0 && out.size() > q.limit) {
            return out.subList(0, q.limit);
        }
        return out;
    }

    // ================================================================ 2. Teams

    public record TeamRecord(String team, String competition, Integer season, String scope,
                             int matches, int wins, int draws, int losses,
                             int goalsFor, int goalsAgainst) {
        public double winRate() {
            return matches == 0 ? 0.0 : (wins * 100.0) / matches;
        }

        public int points() {
            return wins * 3 + draws;
        }

        public int goalDifference() {
            return goalsFor - goalsAgainst;
        }
    }

    /** Win/draw/loss and goal record for a team, optionally scoped. */
    public TeamRecord teamRecord(String teamName, Integer season, String competition, Scope scope) {
        String team = canon(teamName);
        String comp = competition == null ? null : normalize(competition);
        int w = 0, d = 0, l = 0, gf = 0, ga = 0, n = 0;
        if (team != null) {
            for (Match m : graph.matchesForTeam(teamName)) {
                if (!m.hasResult() || !m.involves(team)) {
                    continue;
                }
                if (season != null && !season.equals(m.season())) {
                    continue;
                }
                if (comp != null && !normalize(m.competition()).contains(comp)) {
                    continue;
                }
                boolean home = m.homeTeam().equals(team);
                if (scope == Scope.HOME && !home) {
                    continue;
                }
                if (scope == Scope.AWAY && home) {
                    continue;
                }
                int forGoals = home ? m.homeGoals() : m.awayGoals();
                int againstGoals = home ? m.awayGoals() : m.homeGoals();
                gf += forGoals;
                ga += againstGoals;
                n++;
                if (forGoals > againstGoals) {
                    w++;
                } else if (forGoals < againstGoals) {
                    l++;
                } else {
                    d++;
                }
            }
        }
        String display = team == null ? teamName : displayFor(team);
        return new TeamRecord(display, competition, season,
                scope == null ? "all" : scope.name().toLowerCase(Locale.ROOT), n, w, d, l, gf, ga);
    }

    public enum Scope {ALL, HOME, AWAY}

    public record HeadToHead(String teamA, String teamB, int aWins, int bWins, int draws,
                             int goalsA, int goalsB, List<Match> matches) {
        public int total() {
            return aWins + bWins + draws;
        }
    }

    /** Aggregate head-to-head record between two teams across all competitions. */
    public HeadToHead headToHead(String teamAName, String teamBName) {
        String a = canon(teamAName);
        String b = canon(teamBName);
        List<Match> meetings = new ArrayList<>();
        int aWins = 0, bWins = 0, draws = 0, ga = 0, gb = 0;
        if (a != null && b != null) {
            for (Match m : graph.matchesForTeam(teamAName)) {
                if (!m.involves(a) || !m.involves(b)) {
                    continue;
                }
                meetings.add(m);
                if (!m.hasResult()) {
                    continue;
                }
                int aGoals = m.homeTeam().equals(a) ? m.homeGoals() : m.awayGoals();
                int bGoals = m.homeTeam().equals(b) ? m.homeGoals() : m.awayGoals();
                ga += aGoals;
                gb += bGoals;
                if (aGoals > bGoals) {
                    aWins++;
                } else if (bGoals > aGoals) {
                    bWins++;
                } else {
                    draws++;
                }
            }
        }
        meetings.sort(matchChronological().reversed());
        return new HeadToHead(displayFor(a), displayFor(b), aWins, bWins, draws, ga, gb, meetings);
    }

    // ================================================================ 3. Players

    /** Criteria for {@link #searchPlayers(PlayerQuery)}. Any field may be null. */
    public static final class PlayerQuery {
        public String name;
        public String nationality;
        public String club;
        public String position;
        public Integer minOverall;
        public int limit = 25;
    }

    /** Players matching every supplied criterion, sorted by overall rating desc. */
    public List<Player> searchPlayers(PlayerQuery q) {
        List<Player> source;
        if (q.club != null && !q.club.isBlank()) {
            source = graph.playersForClub(q.club);
        } else if (q.nationality != null && !q.nationality.isBlank()) {
            source = graph.playersForNationality(q.nationality);
        } else {
            source = graph.players();
        }

        String name = q.name == null ? null : normalize(q.name);
        String nationality = q.nationality == null ? null : normalize(q.nationality);
        String club = q.club == null ? null : TeamNames.canonical(q.club);
        String position = q.position == null ? null : normalize(q.position);

        List<Player> out = new ArrayList<>();
        for (Player p : source) {
            if (name != null && (p.name() == null || !normalize(p.name()).contains(name))) {
                continue;
            }
            if (nationality != null && (p.nationality() == null
                    || !normalize(p.nationality()).contains(nationality))) {
                continue;
            }
            if (club != null && !club.equals(p.clubCanonical())) {
                continue;
            }
            if (position != null && (p.position() == null
                    || !normalize(p.position()).equals(position))) {
                continue;
            }
            if (q.minOverall != null && (p.overall() == null || p.overall() < q.minOverall)) {
                continue;
            }
            out.add(p);
        }
        out.sort(Comparator.comparing((Player p) -> p.overall() == null ? -1 : p.overall())
                .reversed()
                .thenComparing(p -> p.name() == null ? "" : p.name()));
        if (q.limit > 0 && out.size() > q.limit) {
            return out.subList(0, q.limit);
        }
        return out;
    }

    // ================================================================ 4. Standings

    public record StandingRow(int position, String team, int points, int played,
                              int wins, int draws, int losses,
                              int goalsFor, int goalsAgainst) {
        public int goalDifference() {
            return goalsFor - goalsAgainst;
        }
    }

    /**
     * Final table for one competition and season, computed from match results.
     * The competition string is resolved to the single best-matching canonical
     * competition to avoid merging, e.g., Série A with the historical dataset.
     */
    public List<StandingRow> standings(String competition, int season) {
        String resolved = resolveCompetition(competition, season);
        Map<String, int[]> table = new LinkedHashMap<>(); // canon -> [P,W,D,L,GF,GA]
        Map<String, String> display = new LinkedHashMap<>();
        for (Match m : graph.matches()) {
            if (!m.hasResult() || !season(m, season)) {
                continue;
            }
            if (resolved != null && !m.competition().equals(resolved)) {
                continue;
            }
            accumulate(table, display, m.homeTeam(), m.homeTeamDisplay(),
                    m.homeGoals(), m.awayGoals());
            accumulate(table, display, m.awayTeam(), m.awayTeamDisplay(),
                    m.awayGoals(), m.homeGoals());
        }

        List<String> teams = new ArrayList<>(table.keySet());
        teams.sort((x, y) -> {
            int[] a = table.get(x);
            int[] b = table.get(y);
            int pa = a[1] * 3 + a[2];
            int pb = b[1] * 3 + b[2];
            if (pa != pb) {
                return Integer.compare(pb, pa);
            }
            int gda = a[4] - a[5];
            int gdb = b[4] - b[5];
            if (gda != gdb) {
                return Integer.compare(gdb, gda);
            }
            if (a[4] != b[4]) {
                return Integer.compare(b[4], a[4]);
            }
            return display.get(x).compareToIgnoreCase(display.get(y));
        });

        List<StandingRow> rows = new ArrayList<>();
        int pos = 1;
        for (String t : teams) {
            int[] s = table.get(t);
            rows.add(new StandingRow(pos++, display.get(t), s[1] * 3 + s[2],
                    s[0], s[1], s[2], s[3], s[4], s[5]));
        }
        return rows;
    }

    private static void accumulate(Map<String, int[]> table, Map<String, String> display,
                                   String team, String label, int forGoals, int againstGoals) {
        int[] s = table.computeIfAbsent(team, k -> new int[6]);
        display.putIfAbsent(team, label);
        s[0]++;
        s[4] += forGoals;
        s[5] += againstGoals;
        if (forGoals > againstGoals) {
            s[1]++;
        } else if (forGoals < againstGoals) {
            s[3]++;
        } else {
            s[2]++;
        }
    }

    // ================================================================ 5. Statistics

    public record GoalStats(String competition, Integer season, int matches,
                            int totalGoals, int homeWins, int awayWins, int draws) {
        public double averageGoals() {
            return matches == 0 ? 0.0 : (double) totalGoals / matches;
        }

        public double homeWinRate() {
            return matches == 0 ? 0.0 : (homeWins * 100.0) / matches;
        }
    }

    /** Aggregate goal/result statistics over a (optionally filtered) match set. */
    public GoalStats averageGoals(String competition, Integer season) {
        String comp = competition == null ? null : normalize(competition);
        int n = 0, goals = 0, hw = 0, aw = 0, dr = 0;
        for (Match m : graph.matches()) {
            if (!m.hasResult()) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            if (comp != null && !normalize(m.competition()).contains(comp)) {
                continue;
            }
            n++;
            goals += m.homeGoals() + m.awayGoals();
            if (m.homeGoals() > m.awayGoals()) {
                hw++;
            } else if (m.awayGoals() > m.homeGoals()) {
                aw++;
            } else {
                dr++;
            }
        }
        return new GoalStats(competition, season, n, goals, hw, aw, dr);
    }

    /** Matches with the largest goal margin, optionally filtered, biggest first. */
    public List<Match> biggestWins(String competition, Integer season, int limit) {
        String comp = competition == null ? null : normalize(competition);
        List<Match> list = new ArrayList<>();
        for (Match m : graph.matches()) {
            if (!m.hasResult()) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            if (comp != null && !normalize(m.competition()).contains(comp)) {
                continue;
            }
            list.add(m);
        }
        list.sort(Comparator.comparingInt((Match m) -> Math.abs(m.homeGoals() - m.awayGoals()))
                .reversed()
                .thenComparing(matchChronological().reversed()));
        if (limit > 0 && list.size() > limit) {
            return list.subList(0, limit);
        }
        return list;
    }

    /**
     * Best team record by win rate (minimum match threshold) over a scope,
     * optionally filtered by competition/season. Useful for "best home/away record".
     */
    public List<TeamRecord> bestRecords(String competition, Integer season, Scope scope,
                                        int minMatches, int limit) {
        Map<String, String> teams = new LinkedHashMap<>();
        String comp = competition == null ? null : normalize(competition);
        for (Match m : graph.matches()) {
            if (comp != null && !normalize(m.competition()).contains(comp)) {
                continue;
            }
            if (season != null && !season.equals(m.season())) {
                continue;
            }
            teams.putIfAbsent(m.homeTeam(), m.homeTeamDisplay());
            teams.putIfAbsent(m.awayTeam(), m.awayTeamDisplay());
        }
        List<TeamRecord> records = new ArrayList<>();
        for (String t : teams.keySet()) {
            TeamRecord r = teamRecord(t, season, competition, scope);
            if (r.matches() >= minMatches) {
                records.add(r);
            }
        }
        records.sort(Comparator.comparingDouble(TeamRecord::winRate)
                .reversed()
                .thenComparing(TeamRecord::goalDifference, Comparator.reverseOrder()));
        if (limit > 0 && records.size() > limit) {
            return records.subList(0, limit);
        }
        return records;
    }

    // ================================================================ helpers

    /** Resolve a free-text competition name to a single canonical competition. */
    public String resolveCompetition(String competition, Integer season) {
        if (competition == null || competition.isBlank()) {
            return null;
        }
        String norm = normalize(competition);
        String best = null;
        int bestCount = -1;
        for (String comp : graph.competitions()) {
            String cn = normalize(comp);
            if (cn.equals(norm)) {
                return comp; // exact wins immediately
            }
            if (cn.contains(norm) || norm.contains(cn)) {
                int count = 0;
                for (Match m : graph.matches()) {
                    if (m.competition().equals(comp) && (season == null || season(m, season))) {
                        count++;
                    }
                }
                if (count > bestCount) {
                    bestCount = count;
                    best = comp;
                }
            }
        }
        return best;
    }

    private static boolean season(Match m, int season) {
        return m.season() != null && m.season() == season;
    }

    private String displayFor(String canonical) {
        if (canonical == null) {
            return null;
        }
        List<Match> ms = graph.matchesForTeamCanonical(canonical);
        for (Match m : ms) {
            if (m.homeTeam().equals(canonical)) {
                return m.homeTeamDisplay();
            }
            if (m.awayTeam().equals(canonical)) {
                return m.awayTeamDisplay();
            }
        }
        return canonical;
    }

    private static Comparator<Match> matchChronological() {
        return Comparator.comparing((Match m) -> m.date(),
                        Comparator.nullsFirst(Comparator.naturalOrder()))
                .thenComparing(m -> m.season() == null ? 0 : m.season());
    }

    private static String canon(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String c = TeamNames.canonical(raw);
        return c.isEmpty() ? null : c;
    }

    private static String normalize(String s) {
        return TeamNames.stripAccents(s).toLowerCase(Locale.ROOT).trim();
    }
}
