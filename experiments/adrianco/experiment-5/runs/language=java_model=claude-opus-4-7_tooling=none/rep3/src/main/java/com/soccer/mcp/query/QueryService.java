package com.soccer.mcp.query;

import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.model.Match;
import com.soccer.mcp.model.Player;
import com.soccer.mcp.util.TeamNames;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

public final class QueryService {

    private final DataStore store;

    public QueryService(DataStore store) {
        this.store = store;
    }

    // --- Match queries ---

    public List<Match> findMatchesByTeam(String team) {
        String n = TeamNames.normalize(team);
        return store.matches().stream()
                .filter(m -> TeamNames.normalize(m.homeTeam()).equals(n)
                          || TeamNames.normalize(m.awayTeam()).equals(n))
                .sorted(Comparator.comparing((Match m) -> m.date(),
                        Comparator.nullsLast(Comparator.naturalOrder())))
                .collect(Collectors.toList());
    }

    public List<Match> findMatchesBetween(String teamA, String teamB) {
        String a = TeamNames.normalize(teamA);
        String b = TeamNames.normalize(teamB);
        return store.matches().stream()
                .filter(m -> {
                    String h = TeamNames.normalize(m.homeTeam());
                    String aw = TeamNames.normalize(m.awayTeam());
                    return (h.equals(a) && aw.equals(b)) || (h.equals(b) && aw.equals(a));
                })
                .sorted(Comparator.comparing((Match m) -> m.date(),
                        Comparator.nullsLast(Comparator.naturalOrder())))
                .collect(Collectors.toList());
    }

    public List<Match> findMatchesByCompetition(String competition) {
        String n = competition.toLowerCase(Locale.ROOT);
        return store.matches().stream()
                .filter(m -> m.competition() != null
                          && m.competition().toLowerCase(Locale.ROOT).contains(n))
                .collect(Collectors.toList());
    }

    public List<Match> findMatchesBySeason(int season) {
        return store.matches().stream()
                .filter(m -> m.season() != null && m.season() == season)
                .collect(Collectors.toList());
    }

    public List<Match> findMatchesByDateRange(LocalDate from, LocalDate to) {
        return store.matches().stream()
                .filter(m -> m.date() != null
                        && (from == null || !m.date().isBefore(from))
                        && (to == null || !m.date().isAfter(to)))
                .collect(Collectors.toList());
    }

    /** Combination filter — any field can be null to skip. */
    public List<Match> findMatches(String team, String competition, Integer season,
                                   LocalDate from, LocalDate to) {
        String nTeam = team == null ? null : TeamNames.normalize(team);
        String nComp = competition == null ? null : competition.toLowerCase(Locale.ROOT);
        return store.matches().stream()
                .filter(m -> {
                    if (nTeam != null) {
                        String h = TeamNames.normalize(m.homeTeam());
                        String a = TeamNames.normalize(m.awayTeam());
                        if (!h.equals(nTeam) && !a.equals(nTeam)) return false;
                    }
                    if (nComp != null) {
                        if (m.competition() == null
                                || !m.competition().toLowerCase(Locale.ROOT).contains(nComp)) {
                            return false;
                        }
                    }
                    if (season != null) {
                        if (m.season() == null || !m.season().equals(season)) return false;
                    }
                    if (from != null) {
                        if (m.date() == null || m.date().isBefore(from)) return false;
                    }
                    if (to != null) {
                        if (m.date() == null || m.date().isAfter(to)) return false;
                    }
                    return true;
                })
                .collect(Collectors.toList());
    }

    // --- Team queries ---

    public TeamStats teamStats(String team) {
        return teamStats(team, null, null, null);
    }

    /**
     * Aggregate team statistics with optional filters.
     *
     * @param venue null = all, "home" = home only, "away" = away only
     */
    public TeamStats teamStats(String team, Integer season, String competition, String venue) {
        String n = TeamNames.normalize(team);
        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, played = 0;
        String nComp = competition == null ? null : competition.toLowerCase(Locale.ROOT);

        for (Match m : store.matches()) {
            if (season != null && (m.season() == null || !m.season().equals(season))) continue;
            if (nComp != null && (m.competition() == null
                    || !m.competition().toLowerCase(Locale.ROOT).contains(nComp))) continue;

            boolean isHome = TeamNames.normalize(m.homeTeam()).equals(n);
            boolean isAway = TeamNames.normalize(m.awayTeam()).equals(n);
            if (!isHome && !isAway) continue;
            if ("home".equalsIgnoreCase(venue) && !isHome) continue;
            if ("away".equalsIgnoreCase(venue) && !isAway) continue;

            played++;
            if (isHome) {
                gf += m.homeGoals();
                ga += m.awayGoals();
                if (m.isHomeWin()) wins++;
                else if (m.isAwayWin()) losses++;
                else draws++;
            } else {
                gf += m.awayGoals();
                ga += m.homeGoals();
                if (m.isAwayWin()) wins++;
                else if (m.isHomeWin()) losses++;
                else draws++;
            }
        }
        return new TeamStats(team, played, wins, draws, losses, gf, ga);
    }

    public HeadToHead headToHead(String teamA, String teamB) {
        String a = TeamNames.normalize(teamA);
        String b = TeamNames.normalize(teamB);
        List<Match> matches = findMatchesBetween(teamA, teamB);
        int aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
        for (Match m : matches) {
            boolean aIsHome = TeamNames.normalize(m.homeTeam()).equals(a);
            int aScore = aIsHome ? m.homeGoals() : m.awayGoals();
            int bScore = aIsHome ? m.awayGoals() : m.homeGoals();
            aGoals += aScore;
            bGoals += bScore;
            if (aScore > bScore) aWins++;
            else if (bScore > aScore) bWins++;
            else draws++;
        }
        return new HeadToHead(teamA, teamB, aWins, bWins, draws, aGoals, bGoals, matches);
    }

    // --- Competition / standings ---

    /** Compute standings for a season. Returns sorted list of TeamStats. */
    public List<TeamStats> standings(String competition, int season) {
        Map<String, int[]> tally = new HashMap<>(); // [played, wins, draws, losses, gf, ga]
        Map<String, String> displayName = new HashMap<>();
        String nComp = competition == null ? null : competition.toLowerCase(Locale.ROOT);
        for (Match m : store.matches()) {
            if (nComp != null && (m.competition() == null
                    || !m.competition().toLowerCase(Locale.ROOT).contains(nComp))) continue;
            if (m.season() == null || m.season() != season) continue;

            String hKey = TeamNames.normalize(m.homeTeam());
            String aKey = TeamNames.normalize(m.awayTeam());
            displayName.putIfAbsent(hKey, m.homeTeam());
            displayName.putIfAbsent(aKey, m.awayTeam());

            int[] hStats = tally.computeIfAbsent(hKey, k -> new int[6]);
            int[] aStats = tally.computeIfAbsent(aKey, k -> new int[6]);

            hStats[0]++; aStats[0]++;
            hStats[4] += m.homeGoals(); hStats[5] += m.awayGoals();
            aStats[4] += m.awayGoals(); aStats[5] += m.homeGoals();
            if (m.isHomeWin()) { hStats[1]++; aStats[3]++; }
            else if (m.isAwayWin()) { hStats[3]++; aStats[1]++; }
            else { hStats[2]++; aStats[2]++; }
        }
        List<TeamStats> result = new ArrayList<>();
        for (Map.Entry<String, int[]> e : tally.entrySet()) {
            int[] s = e.getValue();
            result.add(new TeamStats(displayName.get(e.getKey()),
                    s[0], s[1], s[2], s[3], s[4], s[5]));
        }
        result.sort(Comparator
                .comparingInt(TeamStats::points).reversed()
                .thenComparingInt(TeamStats::goalDifference).reversed()
                .thenComparingInt(TeamStats::goalsFor).reversed());
        return result;
    }

    /** Champion of competition+season (top of standings). */
    public TeamStats champion(String competition, int season) {
        List<TeamStats> standings = standings(competition, season);
        if (standings.isEmpty()) return null;
        return standings.get(0);
    }

    // --- Player queries ---

    public List<Player> findPlayersByName(String name) {
        String q = name.toLowerCase(Locale.ROOT).trim();
        String qStripped = TeamNames.stripAccents(q);
        return store.players().stream()
                .filter(p -> {
                    if (p.name() == null) return false;
                    String lower = p.name().toLowerCase(Locale.ROOT);
                    String stripped = TeamNames.stripAccents(lower);
                    return lower.contains(q) || stripped.contains(qStripped);
                })
                .collect(Collectors.toList());
    }

    public List<Player> findPlayersByNationality(String nationality) {
        String q = nationality.toLowerCase(Locale.ROOT).trim();
        return store.players().stream()
                .filter(p -> p.nationality() != null
                        && p.nationality().toLowerCase(Locale.ROOT).equals(q))
                .collect(Collectors.toList());
    }

    public List<Player> findPlayersByClub(String club) {
        String q = TeamNames.normalize(club);
        return store.players().stream()
                .filter(p -> p.club() != null && TeamNames.normalize(p.club()).contains(q))
                .collect(Collectors.toList());
    }

    public List<Player> findPlayersByPosition(String position) {
        String q = position.toUpperCase(Locale.ROOT).trim();
        return store.players().stream()
                .filter(p -> p.position() != null
                        && p.position().toUpperCase(Locale.ROOT).equals(q))
                .collect(Collectors.toList());
    }

    public List<Player> topRatedPlayers(int limit) {
        return store.players().stream()
                .filter(p -> p.overall() != null)
                .sorted(Comparator.comparingInt(Player::overall).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<Player> topRatedBrazilianPlayers(int limit) {
        return store.players().stream()
                .filter(p -> "Brazil".equalsIgnoreCase(p.nationality()))
                .filter(p -> p.overall() != null)
                .sorted(Comparator.comparingInt(Player::overall).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    // --- Statistical analysis ---

    public double averageGoalsPerMatch(String competition) {
        List<Match> matches = competition == null
                ? store.matches()
                : findMatchesByCompetition(competition);
        if (matches.isEmpty()) return 0.0;
        long total = matches.stream().mapToLong(Match::totalGoals).sum();
        return (double) total / matches.size();
    }

    public double homeWinRate(String competition) {
        List<Match> matches = competition == null
                ? store.matches()
                : findMatchesByCompetition(competition);
        if (matches.isEmpty()) return 0.0;
        long homeWins = matches.stream().filter(Match::isHomeWin).count();
        return (double) homeWins / matches.size();
    }

    public List<Match> biggestWins(int limit) {
        return store.matches().stream()
                .sorted(Comparator.comparingInt((Match m) ->
                        Math.abs(m.homeGoals() - m.awayGoals())).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    /** Aggregated stats for each team across all matches in store. */
    public Map<String, TeamStats> allTeamStats() {
        Map<String, int[]> tally = new HashMap<>();
        Map<String, String> displayName = new LinkedHashMap<>();
        for (Match m : store.matches()) {
            String hKey = TeamNames.normalize(m.homeTeam());
            String aKey = TeamNames.normalize(m.awayTeam());
            displayName.putIfAbsent(hKey, m.homeTeam());
            displayName.putIfAbsent(aKey, m.awayTeam());

            int[] hStats = tally.computeIfAbsent(hKey, k -> new int[6]);
            int[] aStats = tally.computeIfAbsent(aKey, k -> new int[6]);
            hStats[0]++; aStats[0]++;
            hStats[4] += m.homeGoals(); hStats[5] += m.awayGoals();
            aStats[4] += m.awayGoals(); aStats[5] += m.homeGoals();
            if (m.isHomeWin()) { hStats[1]++; aStats[3]++; }
            else if (m.isAwayWin()) { hStats[3]++; aStats[1]++; }
            else { hStats[2]++; aStats[2]++; }
        }
        Map<String, TeamStats> result = new LinkedHashMap<>();
        for (Map.Entry<String, int[]> e : tally.entrySet()) {
            int[] s = e.getValue();
            result.put(e.getKey(), new TeamStats(displayName.get(e.getKey()),
                    s[0], s[1], s[2], s[3], s[4], s[5]));
        }
        return result;
    }
}
