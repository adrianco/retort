package com.brsoccer.mcp.service;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;

import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class StatsService {

    private final MatchService matches;

    public StatsService(MatchService matches) {
        this.matches = matches;
    }

    public double averageGoalsPerMatch(Competition competition, Integer season) {
        List<Match> ms = matches.filter(null, competition, season).stream()
            .filter(m -> m.getHomeGoals() != null && m.getAwayGoals() != null)
            .collect(Collectors.toList());
        if (ms.isEmpty()) return 0.0;
        int total = ms.stream().mapToInt(Match::totalGoals).sum();
        return (double) total / ms.size();
    }

    public double homeWinRate(Competition competition, Integer season) {
        List<Match> ms = matches.filter(null, competition, season).stream()
            .filter(m -> m.getHomeGoals() != null && m.getAwayGoals() != null)
            .collect(Collectors.toList());
        if (ms.isEmpty()) return 0.0;
        long homeWins = ms.stream().filter(Match::isHomeWin).count();
        return (double) homeWins / ms.size();
    }

    public List<Match> biggestWins(Competition competition, int limit) {
        return matches.filter(null, competition, null).stream()
            .filter(m -> m.getHomeGoals() != null && m.getAwayGoals() != null)
            .sorted(Comparator.<Match>comparingInt(m -> Math.abs(m.getHomeGoals() - m.getAwayGoals())).reversed()
                .thenComparingInt(Match::totalGoals).reversed())
            .limit(limit)
            .collect(Collectors.toList());
    }
}
