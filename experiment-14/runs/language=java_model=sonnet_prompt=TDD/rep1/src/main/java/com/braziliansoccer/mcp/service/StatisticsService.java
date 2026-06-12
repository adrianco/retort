package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Match;
import java.util.*;
import java.util.stream.*;

public class StatisticsService {
    public record TeamRecord(int wins, int draws, int losses, int goalsFor, int goalsAgainst) {}
    public record HeadToHead(int team1Wins, int team2Wins, int draws) {}
    public record StandingEntry(String team, int points, int wins, int draws, int losses, int goalsFor, int goalsAgainst) {}

    private final List<Match> matches;
    private final TeamNameNormalizer normalizer = new TeamNameNormalizer();

    public StatisticsService(List<Match> matches) { this.matches = matches; }

    private List<Match> filter(List<Match> source, String competition, Integer season) {
        return source.stream()
            .filter(m -> competition == null || m.competition().equalsIgnoreCase(competition))
            .filter(m -> season == null || m.season() == season)
            .collect(Collectors.toList());
    }

    public TeamRecord getTeamRecord(String team, String competition, Integer season) {
        List<Match> filtered = filter(matches, competition, season);
        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
        for (Match m : filtered) {
            boolean isHome = normalizer.matches(m.homeTeam(), team);
            boolean isAway = normalizer.matches(m.awayTeam(), team);
            if (!isHome && !isAway) continue;
            int gf = isHome ? m.homeGoals() : m.awayGoals();
            int ga = isHome ? m.awayGoals() : m.homeGoals();
            goalsFor += gf;
            goalsAgainst += ga;
            if (gf > ga) wins++;
            else if (gf == ga) draws++;
            else losses++;
        }
        return new TeamRecord(wins, draws, losses, goalsFor, goalsAgainst);
    }

    public TeamRecord getHomeRecord(String team, String competition, Integer season) {
        List<Match> filtered = filter(matches, competition, season);
        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
        for (Match m : filtered) {
            if (!normalizer.matches(m.homeTeam(), team)) continue;
            goalsFor += m.homeGoals();
            goalsAgainst += m.awayGoals();
            if (m.homeGoals() > m.awayGoals()) wins++;
            else if (m.homeGoals() == m.awayGoals()) draws++;
            else losses++;
        }
        return new TeamRecord(wins, draws, losses, goalsFor, goalsAgainst);
    }

    public HeadToHead getHeadToHead(String team1, String team2) {
        int t1wins = 0, t2wins = 0, draws = 0;
        for (Match m : matches) {
            boolean t1Home = normalizer.matches(m.homeTeam(), team1) && normalizer.matches(m.awayTeam(), team2);
            boolean t2Home = normalizer.matches(m.homeTeam(), team2) && normalizer.matches(m.awayTeam(), team1);
            if (!t1Home && !t2Home) continue;
            int t1g = t1Home ? m.homeGoals() : m.awayGoals();
            int t2g = t1Home ? m.awayGoals() : m.homeGoals();
            if (t1g > t2g) t1wins++;
            else if (t1g == t2g) draws++;
            else t2wins++;
        }
        return new HeadToHead(t1wins, t2wins, draws);
    }

    public List<StandingEntry> getStandings(int season, String competition) {
        List<Match> filtered = filter(matches, competition, season);
        Map<String, int[]> table = new LinkedHashMap<>();
        for (Match m : filtered) {
            String home = m.homeTeam(), away = m.awayTeam();
            table.putIfAbsent(home, new int[6]);
            table.putIfAbsent(away, new int[6]);
            int[] h = table.get(home), a = table.get(away);
            h[3] += m.homeGoals();
            h[4] += m.awayGoals();
            a[3] += m.awayGoals();
            a[4] += m.homeGoals();
            if (m.homeGoals() > m.awayGoals()) {
                h[0]++;
                a[2]++;
            } else if (m.homeGoals() == m.awayGoals()) {
                h[1]++;
                a[1]++;
            } else {
                h[2]++;
                a[0]++;
            }
        }
        return table.entrySet().stream().map(e -> {
            int[] v = e.getValue();
            return new StandingEntry(e.getKey(), v[0] * 3 + v[1], v[0], v[1], v[2], v[3], v[4]);
        }).sorted(Comparator.comparingInt(StandingEntry::points).reversed()).collect(Collectors.toList());
    }

    public List<Match> getBiggestWins(int limit) {
        return matches.stream()
            .sorted(Comparator.comparingInt(m -> -Math.abs(m.homeGoals() - m.awayGoals())))
            .limit(limit)
            .collect(Collectors.toList());
    }

    public double getAverageGoalsPerMatch(String competition) {
        List<Match> filtered = matches.stream()
            .filter(m -> competition == null || m.competition().equalsIgnoreCase(competition))
            .collect(Collectors.toList());
        if (filtered.isEmpty()) return 0.0;
        return filtered.stream().mapToInt(m -> m.homeGoals() + m.awayGoals()).sum() / (double) filtered.size();
    }
}
