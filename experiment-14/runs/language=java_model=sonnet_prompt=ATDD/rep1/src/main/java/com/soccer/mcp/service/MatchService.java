package com.soccer.mcp.service;

import com.soccer.mcp.model.Match;
import com.soccer.mcp.model.Standing;
import com.soccer.mcp.model.TeamStats;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Service for match queries: find matches, compute standings, head-to-head, statistics.
 */
public class MatchService {

    private final List<Match> matches;
    private final TeamNameNormalizer normalizer;

    public MatchService(List<Match> matches, TeamNameNormalizer normalizer) {
        this.matches = matches;
        this.normalizer = normalizer;
    }

    /**
     * Find matches by various filters.
     */
    public List<Match> findMatches(String team, String homeTeam, String awayTeam,
                                    String competition, Integer season,
                                    LocalDate dateFrom, LocalDate dateTo, int limit) {
        return matches.stream()
                .filter(m -> matchesTeam(m, team))
                .filter(m -> matchesHomeTeam(m, homeTeam))
                .filter(m -> matchesAwayTeam(m, awayTeam))
                .filter(m -> matchesCompetition(m, competition))
                .filter(m -> season == null || Objects.equals(m.getSeason(), season))
                .filter(m -> dateFrom == null || (m.getDate() != null && !m.getDate().isBefore(dateFrom)))
                .filter(m -> dateTo == null || (m.getDate() != null && !m.getDate().isAfter(dateTo)))
                .limit(limit)
                .collect(Collectors.toList());
    }

    /**
     * Compute team stats for given competition and optional season.
     */
    public TeamStats getTeamStats(String team, String competition, Integer season) {
        TeamStats stats = new TeamStats(team);
        for (Match m : matches) {
            if (!matchesCompetition(m, competition)) continue;
            if (season != null && !Objects.equals(m.getSeason(), season)) continue;
            boolean isHome = normalizer.matches(m.getHomeTeam(), team);
            boolean isAway = normalizer.matches(m.getAwayTeam(), team);
            if (isHome) {
                stats.addMatch(true, m.getHomeGoals(), m.getAwayGoals());
            } else if (isAway) {
                stats.addMatch(false, m.getHomeGoals(), m.getAwayGoals());
            }
        }
        return stats;
    }

    /**
     * Compute standings table for a competition and optional season.
     */
    public List<Standing> getStandings(Integer season, String competition, int limit) {
        Map<String, TeamStats> statsMap = new LinkedHashMap<>();

        for (Match m : matches) {
            if (!matchesCompetition(m, competition)) continue;
            if (season != null && !Objects.equals(m.getSeason(), season)) continue;

            String homeKey = normalizeKey(m.getHomeTeam());
            String awayKey = normalizeKey(m.getAwayTeam());

            statsMap.computeIfAbsent(homeKey, k -> new TeamStats(m.getHomeTeam()))
                    .addMatch(true, m.getHomeGoals(), m.getAwayGoals());
            statsMap.computeIfAbsent(awayKey, k -> new TeamStats(m.getAwayTeam()))
                    .addMatch(false, m.getHomeGoals(), m.getAwayGoals());
        }

        List<TeamStats> sorted = statsMap.values().stream()
                .sorted(Comparator.comparingInt(TeamStats::getPoints).reversed()
                        .thenComparingInt(TeamStats::getGoalDifference).reversed()
                        .thenComparingInt(TeamStats::getGoalsScored).reversed())
                .collect(Collectors.toList());

        List<Standing> standings = new ArrayList<>();
        int pos = 1;
        for (TeamStats ts : sorted) {
            if (pos > limit) break;
            standings.add(new Standing(pos++, ts));
        }
        return standings;
    }

    /**
     * Compute head-to-head record between two teams.
     */
    public Map<String, Object> getHeadToHead(String team1, String team2, String competition, Integer season) {
        List<Match> h2h = matches.stream()
                .filter(m -> matchesCompetition(m, competition))
                .filter(m -> season == null || Objects.equals(m.getSeason(), season))
                .filter(m -> {
                    boolean t1Home = normalizer.matches(m.getHomeTeam(), team1);
                    boolean t2Away = normalizer.matches(m.getAwayTeam(), team2);
                    boolean t2Home = normalizer.matches(m.getHomeTeam(), team2);
                    boolean t1Away = normalizer.matches(m.getAwayTeam(), team1);
                    return (t1Home && t2Away) || (t2Home && t1Away);
                })
                .collect(Collectors.toList());

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        for (Match m : h2h) {
            boolean team1IsHome = normalizer.matches(m.getHomeTeam(), team1);
            if (team1IsHome) {
                team1Goals += m.getHomeGoals();
                team2Goals += m.getAwayGoals();
                if (m.getHomeGoals() > m.getAwayGoals()) team1Wins++;
                else if (m.getHomeGoals() < m.getAwayGoals()) team2Wins++;
                else draws++;
            } else {
                team1Goals += m.getAwayGoals();
                team2Goals += m.getHomeGoals();
                if (m.getAwayGoals() > m.getHomeGoals()) team1Wins++;
                else if (m.getAwayGoals() < m.getHomeGoals()) team2Wins++;
                else draws++;
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("team1", team1);
        result.put("team2", team2);
        result.put("total", h2h.size());
        result.put("team1Wins", team1Wins);
        result.put("team2Wins", team2Wins);
        result.put("draws", draws);
        result.put("team1Goals", team1Goals);
        result.put("team2Goals", team2Goals);
        result.put("recentMatches", h2h.stream()
                .sorted(Comparator.comparing(Match::getDate, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
                .limit(5)
                .collect(Collectors.toList()));
        return result;
    }

    /**
     * Get statistics: biggest_wins, avg_goals, home_record.
     */
    public String getStatistics(String statType, String competition, Integer season) {
        List<Match> filtered = matches.stream()
                .filter(m -> matchesCompetition(m, competition))
                .filter(m -> season == null || Objects.equals(m.getSeason(), season))
                .collect(Collectors.toList());

        if (filtered.isEmpty()) {
            return "No matches found for the specified filters.";
        }

        switch (statType.toLowerCase()) {
            case "biggest_wins":
                return getBiggestWins(filtered, season);
            case "avg_goals":
                return getAvgGoals(filtered, season);
            case "home_record":
                return getHomeRecord(filtered);
            default:
                return "Unknown statistic type: " + statType + ". Available: biggest_wins, avg_goals, home_record";
        }
    }

    private String getBiggestWins(List<Match> filtered, Integer season) {
        StringBuilder sb = new StringBuilder();
        String title = season != null ? "Biggest Wins (" + season + ")" : "Biggest Wins (All Time)";
        sb.append(title).append("\n");
        sb.append("=".repeat(50)).append("\n");

        filtered.stream()
                .filter(m -> m.getHomeGoals() != m.getAwayGoals())
                .sorted(Comparator.comparingInt((Match m) -> Math.abs(m.getHomeGoals() - m.getAwayGoals())).reversed())
                .limit(10)
                .forEach(m -> {
                    String winner = m.getHomeGoals() > m.getAwayGoals() ? m.getHomeTeam() : m.getAwayTeam();
                    int margin = Math.abs(m.getHomeGoals() - m.getAwayGoals());
                    String dateStr = m.getDate() != null ? m.getDate().toString() : "unknown";
                    sb.append(String.format("%s %d-%d %s (margin: %d, %s)\n",
                            m.getHomeTeam(), m.getHomeGoals(), m.getAwayGoals(), m.getAwayTeam(), margin, dateStr));
                });
        return sb.toString();
    }

    private String getAvgGoals(List<Match> filtered, Integer season) {
        double totalGoals = filtered.stream()
                .mapToInt(m -> m.getHomeGoals() + m.getAwayGoals())
                .sum();
        double avgGoals = filtered.isEmpty() ? 0 : totalGoals / filtered.size();

        StringBuilder sb = new StringBuilder();
        String seasonStr = season != null ? String.valueOf(season) : "All Seasons";
        sb.append("Average Goals per Match (" + seasonStr + ")\n");
        sb.append("=".repeat(50)).append("\n");
        sb.append(String.format("Total matches: %d\n", filtered.size()));
        sb.append(String.format("Total goals: %.0f\n", totalGoals));
        sb.append(String.format("Average goals per match: %.2f\n", avgGoals));
        if (season != null) {
            sb.append(String.format("Season: %d\n", season));
        }
        return sb.toString();
    }

    private String getHomeRecord(List<Match> filtered) {
        long homeWins = filtered.stream().filter(m -> m.getHomeGoals() > m.getAwayGoals()).count();
        long awayWins = filtered.stream().filter(m -> m.getAwayGoals() > m.getHomeGoals()).count();
        long draws = filtered.stream().filter(m -> m.getHomeGoals() == m.getAwayGoals()).count();
        double homeWinRate = filtered.isEmpty() ? 0 : (100.0 * homeWins) / filtered.size();
        double awayWinRate = filtered.isEmpty() ? 0 : (100.0 * awayWins) / filtered.size();
        double drawRate = filtered.isEmpty() ? 0 : (100.0 * draws) / filtered.size();

        StringBuilder sb = new StringBuilder();
        sb.append("Home/Away Record\n");
        sb.append("=".repeat(50)).append("\n");
        sb.append(String.format("Total matches: %d\n", filtered.size()));
        sb.append(String.format("Home wins: %d (%.1f%%)\n", homeWins, homeWinRate));
        sb.append(String.format("Away wins: %d (%.1f%%)\n", awayWins, awayWinRate));
        sb.append(String.format("Draws: %d (%.1f%%)\n", draws, drawRate));
        sb.append(String.format("Home win rate: %.1f%%\n", homeWinRate));
        return sb.toString();
    }

    private boolean matchesTeam(Match m, String team) {
        if (team == null) return true;
        return normalizer.matches(m.getHomeTeam(), team) || normalizer.matches(m.getAwayTeam(), team);
    }

    private boolean matchesHomeTeam(Match m, String homeTeam) {
        if (homeTeam == null) return true;
        return normalizer.matches(m.getHomeTeam(), homeTeam);
    }

    private boolean matchesAwayTeam(Match m, String awayTeam) {
        if (awayTeam == null) return true;
        return normalizer.matches(m.getAwayTeam(), awayTeam);
    }

    private boolean matchesCompetition(Match m, String competition) {
        if (competition == null) return true;
        String comp = m.getCompetition();
        if (comp == null) return false;
        String lowerComp = comp.toLowerCase();
        String lowerQuery = competition.toLowerCase();

        // Handle common aliases
        if (lowerQuery.contains("brasil") || lowerQuery.equals("brasileirao")) {
            return lowerComp.contains("brasileiro") || lowerComp.contains("brasileirao");
        }
        if (lowerQuery.contains("copa") || lowerQuery.contains("cup")) {
            return lowerComp.contains("copa") || lowerComp.contains("cup");
        }
        if (lowerQuery.contains("libertadores")) {
            return lowerComp.contains("libertadores");
        }
        return lowerComp.contains(lowerQuery);
    }

    private String normalizeKey(String teamName) {
        return normalizer.canonical(teamName);
    }
}
