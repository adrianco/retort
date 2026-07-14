/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    SoccerDatabase.java
 * Purpose: The in-memory knowledge base and query engine over all loaded
 *          matches and players. Provides match search, head-to-head records,
 *          team records, computed competition standings, aggregate statistics
 *          (average goals, home-win rate, biggest wins, top-scoring teams) and
 *          player search. All team matching is name-variation tolerant via
 *          TeamNames; all string matching is accent/case-insensitive.
 * Part of: query package (core engine consumed by the MCP tool layer).
 * ============================================================================
 */
package com.example.brsoccer.query;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.model.Player;
import com.example.brsoccer.model.TeamNames;

import java.text.Normalizer;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeSet;

/** Queryable in-memory store of Brazilian soccer matches and players. */
public final class SoccerDatabase {

    private final List<Match> matches;
    private final List<Player> players;

    public SoccerDatabase(List<Match> matches, List<Player> players) {
        this.matches = List.copyOf(matches);
        this.players = List.copyOf(players);
    }

    public int matchCount() {
        return matches.size();
    }

    public int playerCount() {
        return players.size();
    }

    /** Distinct competition names present in the data, sorted alphabetically. */
    public List<String> competitions() {
        TreeSet<String> set = new TreeSet<>();
        for (Match m : matches) {
            if (m.competition() != null) {
                set.add(m.competition());
            }
        }
        return new ArrayList<>(set);
    }

    // ------------------------------------------------------------------ matches

    /** All matches satisfying the query, ordered by date ascending (nulls last). */
    public List<Match> findMatches(MatchQuery q) {
        List<Match> result = new ArrayList<>();
        for (Match m : matches) {
            if (accepts(m, q)) {
                result.add(m);
            }
        }
        result.sort(byDateAscending());
        return result;
    }

    private boolean accepts(Match m, MatchQuery q) {
        if (q.competition() != null && !competitionMatches(m.competition(), q.competition())) {
            return false;
        }
        if (q.season() != null && !q.season().equals(m.season())) {
            return false;
        }
        if (q.team() != null && !teamMatchesVenue(m, q.team(), q.venue())) {
            return false;
        }
        if (q.opponent() != null && !m.involves(q.opponent())) {
            return false;
        }
        if (q.from() != null && (m.date() == null || m.date().isBefore(q.from()))) {
            return false;
        }
        if (q.to() != null && (m.date() == null || m.date().isAfter(q.to()))) {
            return false;
        }
        return true;
    }

    private boolean teamMatchesVenue(Match m, String team, Venue venue) {
        String key = TeamNames.canonicalKey(team);
        boolean isHome = TeamNames.canonicalKey(m.homeTeam()).equals(key);
        boolean isAway = TeamNames.canonicalKey(m.awayTeam()).equals(key);
        return switch (venue == null ? Venue.ANY : venue) {
            case HOME -> isHome;
            case AWAY -> isAway;
            case ANY -> isHome || isAway;
        };
    }

    // ------------------------------------------------------------- head to head

    public HeadToHead headToHead(String teamA, String teamB) {
        List<Match> between = new ArrayList<>();
        for (Match m : matches) {
            if (m.isBetween(teamA, teamB)) {
                between.add(m);
            }
        }
        between.sort(byDateDescending());
        int aWins = 0;
        int bWins = 0;
        int draws = 0;
        for (Match m : between) {
            Optional<String> winner = m.winner();
            if (winner.isEmpty()) {
                draws++;
            } else if (TeamNames.matches(winner.get(), teamA)) {
                aWins++;
            } else {
                bWins++;
            }
        }
        return new HeadToHead(TeamNames.displayName(teamA), TeamNames.displayName(teamB),
                aWins, bWins, draws, between);
    }

    // ------------------------------------------------------------- team records

    public TeamRecord teamRecord(String team, Integer season, String competition, Venue venue) {
        MatchQuery q = new MatchQuery().team(team).venue(venue == null ? Venue.ANY : venue);
        if (season != null) {
            q.season(season);
        }
        if (competition != null) {
            q.competition(competition);
        }
        return accumulate(TeamNames.displayName(team), team, findMatches(q));
    }

    private TeamRecord accumulate(String displayName, String teamKeySource, List<Match> ms) {
        String key = TeamNames.canonicalKey(teamKeySource);
        int wins = 0;
        int draws = 0;
        int losses = 0;
        int gf = 0;
        int ga = 0;
        for (Match m : ms) {
            boolean home = TeamNames.canonicalKey(m.homeTeam()).equals(key);
            int forGoals = home ? m.homeGoal() : m.awayGoal();
            int againstGoals = home ? m.awayGoal() : m.homeGoal();
            gf += forGoals;
            ga += againstGoals;
            if (forGoals > againstGoals) {
                wins++;
            } else if (forGoals < againstGoals) {
                losses++;
            } else {
                draws++;
            }
        }
        return new TeamRecord(displayName, ms.size(), wins, draws, losses, gf, ga);
    }

    // --------------------------------------------------------------- standings

    /** Standings computed from match results, ordered by points, GD, then goals for. */
    public List<StandingRow> standings(String competition, int season) {
        List<Match> seasonMatches = findMatches(new MatchQuery().competition(competition).season(season));
        Map<String, List<Match>> byTeam = new LinkedHashMap<>();
        for (Match m : seasonMatches) {
            byTeam.computeIfAbsent(TeamNames.canonicalKey(m.homeTeam()), k -> new ArrayList<>()).add(m);
            byTeam.computeIfAbsent(TeamNames.canonicalKey(m.awayTeam()), k -> new ArrayList<>()).add(m);
        }
        List<TeamRecord> records = new ArrayList<>();
        for (Map.Entry<String, List<Match>> e : byTeam.entrySet()) {
            // Use the first match's spelling of this team as its display name.
            String display = displayNameFor(e.getKey(), e.getValue());
            records.add(accumulate(display, display, e.getValue()));
        }
        records.sort(Comparator
                .comparingInt(TeamRecord::points).reversed()
                .thenComparing(Comparator.comparingInt(TeamRecord::goalDifference).reversed())
                .thenComparing(Comparator.comparingInt(TeamRecord::goalsFor).reversed())
                .thenComparing(TeamRecord::team));
        List<StandingRow> table = new ArrayList<>();
        for (int i = 0; i < records.size(); i++) {
            table.add(new StandingRow(i + 1, records.get(i)));
        }
        return table;
    }

    private String displayNameFor(String key, List<Match> teamMatches) {
        for (Match m : teamMatches) {
            if (TeamNames.canonicalKey(m.homeTeam()).equals(key)) {
                return TeamNames.displayName(m.homeTeam());
            }
            if (TeamNames.canonicalKey(m.awayTeam()).equals(key)) {
                return TeamNames.displayName(m.awayTeam());
            }
        }
        return key;
    }

    // -------------------------------------------------------------- statistics

    public double averageGoalsPerMatch(MatchQuery q) {
        List<Match> ms = findMatches(q);
        if (ms.isEmpty()) {
            return 0.0;
        }
        int total = 0;
        for (Match m : ms) {
            total += m.totalGoals();
        }
        return (double) total / ms.size();
    }

    /** Home-team win rate as a percentage (0-100) over the filtered matches. */
    public double homeWinRate(MatchQuery q) {
        List<Match> ms = findMatches(q);
        if (ms.isEmpty()) {
            return 0.0;
        }
        long homeWins = ms.stream().filter(Match::isHomeWin).count();
        return (homeWins * 100.0) / ms.size();
    }

    /** The matches with the largest winning margin (descending), up to {@code limit}. */
    public List<Match> biggestWins(MatchQuery q, int limit) {
        List<Match> ms = new ArrayList<>(findMatches(q));
        ms.sort(Comparator.comparingInt(Match::goalMargin).reversed()
                .thenComparing(Comparator.comparingInt(Match::totalGoals).reversed()));
        return ms.subList(0, Math.min(limit, ms.size()));
    }

    /** Teams ranked by goals scored within a competition/season, up to {@code limit}. */
    public List<TeamRecord> topScoringTeams(String competition, Integer season, int limit) {
        List<StandingRow> table = standings(competition, season == null ? 0 : season);
        List<TeamRecord> records = new ArrayList<>();
        for (StandingRow row : table) {
            records.add(row.record());
        }
        records.sort(Comparator.comparingInt(TeamRecord::goalsFor).reversed()
                .thenComparing(TeamRecord::team));
        return records.subList(0, Math.min(limit, records.size()));
    }

    // ------------------------------------------------------------------ players

    public List<Player> searchPlayers(PlayerQuery q) {
        List<Player> result = new ArrayList<>();
        for (Player p : players) {
            if (q.name() != null && !p.nameMatches(q.name())) {
                continue;
            }
            if (q.nationality() != null && !p.hasNationality(q.nationality())) {
                continue;
            }
            if (q.club() != null && !p.playsFor(q.club())) {
                continue;
            }
            if (q.position() != null && !positionMatches(p.position(), q.position())) {
                continue;
            }
            if (q.minOverall() != null && (p.overall() == null || p.overall() < q.minOverall())) {
                continue;
            }
            result.add(p);
        }
        result.sort(Comparator.comparing((Player p) -> p.overall() == null ? -1 : p.overall())
                .reversed()
                .thenComparing(p -> p.name() == null ? "" : p.name()));
        if (q.limit() > 0 && result.size() > q.limit()) {
            return new ArrayList<>(result.subList(0, q.limit()));
        }
        return result;
    }

    // -------------------------------------------------------------------- utils

    private static boolean positionMatches(String actual, String query) {
        return actual != null && fold(actual).equals(fold(query));
    }

    private static boolean competitionMatches(String actual, String query) {
        if (actual == null) {
            return false;
        }
        String a = fold(actual);
        String q = fold(query);
        if (a.contains(q)) {
            return true;
        }
        // "Série A" is the Brasileirão top flight; treat the two labels as one,
        // without pulling in the lower divisions (Série B / Série C).
        return competitionGroup(a).equals(competitionGroup(q));
    }

    private static String competitionGroup(String folded) {
        if (folded.equals("serie a") || folded.equals("brasileirao")
                || folded.contains("campeonato brasileiro")) {
            return "brasileirao";
        }
        return folded;
    }

    private static String fold(String s) {
        if (s == null) {
            return "";
        }
        return Normalizer.normalize(s, Normalizer.Form.NFD)
                .replaceAll("\\p{InCombiningDiacriticalMarks}+", "")
                .toLowerCase().trim();
    }

    private static Comparator<Match> byDateAscending() {
        return Comparator.comparing(Match::date, Comparator.nullsLast(Comparator.naturalOrder()));
    }

    private static Comparator<Match> byDateDescending() {
        return Comparator.comparing(Match::date,
                Comparator.nullsLast(Comparator.reverseOrder()));
    }
}
