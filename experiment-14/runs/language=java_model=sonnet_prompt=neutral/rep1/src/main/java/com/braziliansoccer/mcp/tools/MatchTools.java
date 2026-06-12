package com.braziliansoccer.mcp.tools;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.data.Match;
import com.braziliansoccer.mcp.data.TeamNormalizer;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.*;
import java.util.stream.Collectors;

public class MatchTools {

    private final DataLoader loader;

    public MatchTools(DataLoader loader) {
        this.loader = loader;
    }

    /**
     * search_matches: Find matches by team, competition, season, and/or date range.
     * Params: team (optional), team2 (optional), competition (optional), season (optional int),
     *         start_date (optional), end_date (optional), limit (optional, default 20)
     */
    public String searchMatches(JsonNode params) {
        String team = getStr(params, "team");
        String team2 = getStr(params, "team2");
        String competition = getStr(params, "competition");
        int season = getInt(params, "season");
        String startDate = getStr(params, "start_date");
        String endDate = getStr(params, "end_date");
        int limit = params.has("limit") ? params.get("limit").asInt(20) : 20;

        List<Match> matches = loader.getAllMatches().stream()
            .filter(m -> team.isEmpty() || TeamNormalizer.matches(m.homeTeam, team) || TeamNormalizer.matches(m.awayTeam, team))
            .filter(m -> team2.isEmpty() || TeamNormalizer.matches(m.homeTeam, team2) || TeamNormalizer.matches(m.awayTeam, team2))
            .filter(m -> competition.isEmpty() || m.competition != null && m.competition.toLowerCase().contains(competition.toLowerCase()))
            .filter(m -> season == 0 || m.season == season)
            .filter(m -> startDate.isEmpty() || compareDates(m.datetime, startDate) >= 0)
            .filter(m -> endDate.isEmpty() || compareDates(m.datetime, endDate) <= 0)
            .sorted(Comparator.comparing((Match m) -> m.datetime == null ? "" : m.datetime).reversed())
            .limit(limit)
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(matches.size()).append(" match(es)");
        if (!team.isEmpty()) sb.append(" involving ").append(team);
        if (!team2.isEmpty()) sb.append(" and ").append(team2);
        if (season != 0) sb.append(" in season ").append(season);
        if (!competition.isEmpty()) sb.append(" (").append(competition).append(")");
        sb.append(":\n\n");

        for (Match m : matches) {
            sb.append(formatMatch(m)).append("\n");
        }
        return sb.toString().trim();
    }

    /**
     * head_to_head: Compare two teams head-to-head.
     * Params: team1 (required), team2 (required), competition (optional), season (optional)
     */
    public String headToHead(JsonNode params) {
        String team1 = getStr(params, "team1");
        String team2 = getStr(params, "team2");
        if (team1.isEmpty() || team2.isEmpty()) {
            return "Error: team1 and team2 are required parameters.";
        }
        String competition = getStr(params, "competition");
        int season = getInt(params, "season");

        String norm1 = TeamNormalizer.normalize(team1);
        String norm2 = TeamNormalizer.normalize(team2);

        List<Match> matches = loader.getAllMatches().stream()
            .filter(m -> {
                String hn = TeamNormalizer.normalize(m.homeTeam);
                String an = TeamNormalizer.normalize(m.awayTeam);
                boolean pair = (hn.equalsIgnoreCase(norm1) && an.equalsIgnoreCase(norm2))
                    || (hn.equalsIgnoreCase(norm2) && an.equalsIgnoreCase(norm1));
                // Also do fuzzy match
                if (!pair) {
                    pair = (TeamNormalizer.matches(m.homeTeam, team1) && TeamNormalizer.matches(m.awayTeam, team2))
                        || (TeamNormalizer.matches(m.homeTeam, team2) && TeamNormalizer.matches(m.awayTeam, team1));
                }
                return pair;
            })
            .filter(m -> competition.isEmpty() || m.competition != null && m.competition.toLowerCase().contains(competition.toLowerCase()))
            .filter(m -> season == 0 || m.season == season)
            .sorted(Comparator.comparing((Match m) -> m.datetime == null ? "" : m.datetime).reversed())
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No head-to-head matches found between " + team1 + " and " + team2 + ".";
        }

        int team1Wins = 0, team2Wins = 0, draws = 0;
        int team1Goals = 0, team2Goals = 0;

        for (Match m : matches) {
            boolean team1IsHome = TeamNormalizer.matches(m.homeTeam, team1);
            if (team1IsHome) {
                team1Goals += m.homeGoals;
                team2Goals += m.awayGoals;
                if (m.homeGoals > m.awayGoals) team1Wins++;
                else if (m.awayGoals > m.homeGoals) team2Wins++;
                else draws++;
            } else {
                team1Goals += m.awayGoals;
                team2Goals += m.homeGoals;
                if (m.awayGoals > m.homeGoals) team1Wins++;
                else if (m.homeGoals > m.awayGoals) team2Wins++;
                else draws++;
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Head-to-Head: ").append(team1).append(" vs ").append(team2).append("\n");
        sb.append("Total matches: ").append(matches.size()).append("\n");
        sb.append(team1).append(" wins: ").append(team1Wins).append("\n");
        sb.append(team2).append(" wins: ").append(team2Wins).append("\n");
        sb.append("Draws: ").append(draws).append("\n");
        sb.append("Goals: ").append(team1).append(" ").append(team1Goals)
            .append(" - ").append(team2Goals).append(" ").append(team2).append("\n\n");
        sb.append("Recent matches (most recent first):\n");

        int shown = Math.min(matches.size(), 20);
        for (int i = 0; i < shown; i++) {
            sb.append(formatMatch(matches.get(i))).append("\n");
        }
        if (matches.size() > 20) {
            sb.append("... and ").append(matches.size() - 20).append(" more matches.\n");
        }
        return sb.toString().trim();
    }

    /**
     * team_stats: Get statistics for a team.
     * Params: team (required), competition (optional), season (optional)
     */
    public String teamStats(JsonNode params) {
        String team = getStr(params, "team");
        if (team.isEmpty()) return "Error: team parameter is required.";
        String competition = getStr(params, "competition");
        int season = getInt(params, "season");

        List<Match> matches = loader.getAllMatches().stream()
            .filter(m -> TeamNormalizer.matches(m.homeTeam, team) || TeamNormalizer.matches(m.awayTeam, team))
            .filter(m -> competition.isEmpty() || m.competition != null && m.competition.toLowerCase().contains(competition.toLowerCase()))
            .filter(m -> season == 0 || m.season == season)
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No matches found for team: " + team;
        }

        int homeWins = 0, homeDraws = 0, homeLosses = 0;
        int awayWins = 0, awayDraws = 0, awayLosses = 0;
        int goalsFor = 0, goalsAgainst = 0;
        int homeGF = 0, homeGA = 0, awayGF = 0, awayGA = 0;

        for (Match m : matches) {
            boolean isHome = TeamNormalizer.matches(m.homeTeam, team);
            if (isHome) {
                homeGF += m.homeGoals; homeGA += m.awayGoals;
                if (m.homeGoals > m.awayGoals) homeWins++;
                else if (m.homeGoals == m.awayGoals) homeDraws++;
                else homeLosses++;
            } else {
                awayGF += m.awayGoals; awayGA += m.homeGoals;
                if (m.awayGoals > m.homeGoals) awayWins++;
                else if (m.awayGoals == m.homeGoals) awayDraws++;
                else awayLosses++;
            }
        }
        goalsFor = homeGF + awayGF;
        goalsAgainst = homeGA + awayGA;
        int wins = homeWins + awayWins;
        int draws = homeDraws + awayDraws;
        int losses = homeLosses + awayLosses;
        int total = wins + draws + losses;
        int points = wins * 3 + draws;

        StringBuilder sb = new StringBuilder();
        sb.append("Statistics for ").append(team);
        if (season != 0) sb.append(" (").append(season).append(")");
        if (!competition.isEmpty()) sb.append(" [").append(competition).append("]");
        sb.append("\n\n");
        sb.append("Overall Record:\n");
        sb.append("  Matches: ").append(total).append("\n");
        sb.append("  Wins: ").append(wins).append(", Draws: ").append(draws)
            .append(", Losses: ").append(losses).append("\n");
        sb.append("  Points: ").append(points).append("\n");
        sb.append("  Goals For: ").append(goalsFor).append(", Goals Against: ").append(goalsAgainst)
            .append(", GD: ").append(goalsFor - goalsAgainst).append("\n");
        if (total > 0) {
            sb.append("  Win rate: ").append(String.format("%.1f%%", 100.0 * wins / total)).append("\n");
        }
        sb.append("\nHome Record (").append(homeWins + homeDraws + homeLosses).append(" games):\n");
        sb.append("  W").append(homeWins).append(" D").append(homeDraws)
            .append(" L").append(homeLosses).append(", GF:").append(homeGF)
            .append(" GA:").append(homeGA).append("\n");
        sb.append("\nAway Record (").append(awayWins + awayDraws + awayLosses).append(" games):\n");
        sb.append("  W").append(awayWins).append(" D").append(awayDraws)
            .append(" L").append(awayLosses).append(", GF:").append(awayGF)
            .append(" GA:").append(awayGA).append("\n");

        // Competitions breakdown
        Map<String, long[]> compStats = new LinkedHashMap<>();
        for (Match m : matches) {
            String comp = m.competition != null ? m.competition : "Unknown";
            compStats.putIfAbsent(comp, new long[]{0, 0, 0, 0});
            long[] s = compStats.get(comp);
            s[0]++; // total
            boolean isHome = TeamNormalizer.matches(m.homeTeam, team);
            if ((isHome && m.homeGoals > m.awayGoals) || (!isHome && m.awayGoals > m.homeGoals)) s[1]++;
            else if (m.homeGoals == m.awayGoals) s[2]++;
            else s[3]++;
        }
        sb.append("\nBy Competition:\n");
        compStats.forEach((comp, s) ->
            sb.append("  ").append(comp).append(": ")
                .append(s[0]).append("G W").append(s[1])
                .append(" D").append(s[2]).append(" L").append(s[3]).append("\n"));

        return sb.toString().trim();
    }

    /**
     * standings: Calculate league standings for a competition/season.
     * Params: competition (required), season (required)
     */
    public String standings(JsonNode params) {
        String competition = getStr(params, "competition");
        int season = getInt(params, "season");
        if (competition.isEmpty() || season == 0) {
            return "Error: competition and season are required.";
        }

        List<Match> matches = loader.getAllMatches().stream()
            .filter(m -> m.competition != null && m.competition.toLowerCase().contains(competition.toLowerCase()))
            .filter(m -> m.season == season)
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No matches found for " + competition + " season " + season + ".";
        }

        Map<String, int[]> table = new LinkedHashMap<>(); // team -> [P, W, D, L, GF, GA, Pts]

        for (Match m : matches) {
            String home = TeamNormalizer.normalize(m.homeTeam);
            String away = TeamNormalizer.normalize(m.awayTeam);
            table.putIfAbsent(home, new int[7]);
            table.putIfAbsent(away, new int[7]);
            int[] h = table.get(home);
            int[] a = table.get(away);
            h[0]++; a[0]++; // Played
            h[4] += m.homeGoals; h[5] += m.awayGoals;
            a[4] += m.awayGoals; a[5] += m.homeGoals;
            if (m.homeGoals > m.awayGoals) {
                h[1]++; h[6] += 3; a[3]++;
            } else if (m.homeGoals == m.awayGoals) {
                h[2]++; h[6]++; a[2]++; a[6]++;
            } else {
                a[1]++; a[6] += 3; h[3]++;
            }
        }

        List<Map.Entry<String, int[]>> sorted = new ArrayList<>(table.entrySet());
        sorted.sort((e1, e2) -> {
            int[] s1 = e1.getValue(), s2 = e2.getValue();
            if (s2[6] != s1[6]) return s2[6] - s1[6]; // Points
            int gd1 = s1[4] - s1[5], gd2 = s2[4] - s2[5];
            if (gd2 != gd1) return gd2 - gd1; // GD
            return s2[4] - s1[4]; // GF
        });

        StringBuilder sb = new StringBuilder();
        sb.append(season).append(" ").append(competition).append(" Standings\n");
        sb.append("  Total matches: ").append(matches.size()).append("\n\n");
        sb.append(String.format("%-3s %-25s %3s %3s %3s %3s %3s %3s %3s%n",
            "Pos", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"));
        sb.append("-".repeat(55)).append("\n");

        for (int i = 0; i < sorted.size(); i++) {
            Map.Entry<String, int[]> e = sorted.get(i);
            int[] s = e.getValue();
            sb.append(String.format("%-3d %-25s %3d %3d %3d %3d %3d %3d %3d%n",
                i + 1, e.getKey(), s[0], s[1], s[2], s[3], s[4], s[5], s[6]));
        }
        return sb.toString().trim();
    }

    /**
     * match_statistics: Get aggregate statistics.
     * Params: competition (optional), season (optional), stat_type (optional: "biggest_wins", "goals_avg", "home_away")
     */
    public String matchStatistics(JsonNode params) {
        String competition = getStr(params, "competition");
        int season = getInt(params, "season");
        String statType = getStr(params, "stat_type");

        List<Match> matches = loader.getAllMatches().stream()
            .filter(m -> competition.isEmpty() || m.competition != null && m.competition.toLowerCase().contains(competition.toLowerCase()))
            .filter(m -> season == 0 || m.season == season)
            .collect(Collectors.toList());

        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }

        StringBuilder sb = new StringBuilder();
        String scope = competition.isEmpty() ? "all competitions" : competition;
        if (season != 0) scope += " " + season;
        sb.append("Statistics for ").append(scope).append(" (").append(matches.size()).append(" matches):\n\n");

        // Goals stats
        long totalGoals = matches.stream().mapToLong(m -> m.homeGoals + m.awayGoals).sum();
        long homeWins = matches.stream().filter(m -> "home".equals(m.winner)).count();
        long awayWins = matches.stream().filter(m -> "away".equals(m.winner)).count();
        long draws = matches.stream().filter(m -> "draw".equals(m.winner)).count();

        sb.append("Goals:\n");
        sb.append("  Total goals: ").append(totalGoals).append("\n");
        sb.append("  Average goals/match: ").append(String.format("%.2f", (double) totalGoals / matches.size())).append("\n");
        sb.append("\nResults:\n");
        sb.append("  Home wins: ").append(homeWins)
            .append(" (").append(String.format("%.1f%%", 100.0 * homeWins / matches.size())).append(")\n");
        sb.append("  Away wins: ").append(awayWins)
            .append(" (").append(String.format("%.1f%%", 100.0 * awayWins / matches.size())).append(")\n");
        sb.append("  Draws: ").append(draws)
            .append(" (").append(String.format("%.1f%%", 100.0 * draws / matches.size())).append(")\n");

        // Biggest wins
        sb.append("\nTop 10 Biggest Wins:\n");
        matches.stream()
            .sorted(Comparator.comparingInt((Match m) -> Math.abs(m.homeGoals - m.awayGoals)).reversed())
            .limit(10)
            .forEach(m -> sb.append("  ").append(formatMatch(m)).append("\n"));

        // Highest scoring matches
        sb.append("\nTop 5 Highest Scoring Matches:\n");
        matches.stream()
            .sorted(Comparator.comparingInt((Match m) -> m.homeGoals + m.awayGoals).reversed())
            .limit(5)
            .forEach(m -> sb.append("  ").append(formatMatch(m)).append("\n"));

        return sb.toString().trim();
    }

    private String formatMatch(Match m) {
        String score = m.homeTeam + " " + m.homeGoals + "-" + m.awayGoals + " " + m.awayTeam;
        String date = m.datetime != null ? m.datetime.split(" ")[0] : "?";
        String comp = m.competition != null ? m.competition : "";
        String rnd = (m.round != null && !m.round.isEmpty()) ? " Rd" + m.round : "";
        String stage = (m.stage != null && !m.stage.isEmpty()) ? " [" + m.stage + "]" : "";
        return date + ": " + score + " (" + comp + rnd + stage + " " + m.season + ")";
    }

    private String getStr(JsonNode n, String key) {
        return n != null && n.has(key) && !n.get(key).isNull() ? n.get(key).asText("").trim() : "";
    }

    private int getInt(JsonNode n, String key) {
        return n != null && n.has(key) && !n.get(key).isNull() ? n.get(key).asInt(0) : 0;
    }

    private int compareDates(String date1, String date2) {
        if (date1 == null) return -1;
        if (date2 == null) return 1;
        // Simple string compare works for ISO dates; Brazilian format needs normalization
        String d1 = normDate(date1);
        String d2 = normDate(date2);
        return d1.compareTo(d2);
    }

    private String normDate(String date) {
        if (date == null) return "";
        date = date.trim().split(" ")[0]; // remove time part
        if (date.matches("\\d{2}/\\d{2}/\\d{4}")) {
            String[] p = date.split("/");
            return p[2] + "-" + p[1] + "-" + p[0];
        }
        return date;
    }
}
