package com.brsoccer.mcp.service;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class CompetitionService {

    private final MatchService matches;

    public CompetitionService(MatchService matches) {
        this.matches = matches;
    }

    /**
     * Computes a league table from match results: 3 pts per win, 1 per draw, 0 per loss.
     */
    public List<TeamStats> standings(Competition competition, int season) {
        Map<String, TeamStats> table = new HashMap<>();
        for (Match m : matches.filter(null, competition, season)) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            String home = m.getHomeTeamNormalized();
            String away = m.getAwayTeamNormalized();
            if (home == null || away == null) continue;
            TeamStats h = table.computeIfAbsent(home, TeamStats::new);
            TeamStats a = table.computeIfAbsent(away, TeamStats::new);
            h.matches++; a.matches++;
            h.goalsFor += m.getHomeGoals(); h.goalsAgainst += m.getAwayGoals();
            a.goalsFor += m.getAwayGoals(); a.goalsAgainst += m.getHomeGoals();
            if (m.getHomeGoals() > m.getAwayGoals()) { h.wins++; a.losses++; }
            else if (m.getHomeGoals() < m.getAwayGoals()) { a.wins++; h.losses++; }
            else { h.draws++; a.draws++; }
        }
        List<TeamStats> sorted = new ArrayList<>(table.values());
        sorted.sort(Comparator.<TeamStats>comparingInt(TeamStats::points).reversed()
            .thenComparingInt(TeamStats::goalDifference).reversed()
            .thenComparingInt(s -> s.goalsFor).reversed());
        return sorted;
    }

    public TeamStats champion(Competition competition, int season) {
        List<TeamStats> standings = standings(competition, season);
        return standings.isEmpty() ? null : standings.get(0);
    }

    public List<Match> bracket(Competition competition, int season) {
        return matches.filter(null, competition, season);
    }
}
