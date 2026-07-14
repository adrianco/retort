package com.brsoccer.mcp.service;

import com.brsoccer.mcp.data.TeamNameNormalizer;
import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;

import java.util.List;

public class TeamService {

    private final MatchService matches;

    public TeamService(MatchService matches) {
        this.matches = matches;
    }

    public TeamStats stats(String team, Competition competition, Integer season) {
        String norm = TeamNameNormalizer.normalize(team);
        TeamStats s = new TeamStats(norm);
        for (Match m : matches.filter(team, competition, season)) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            s.matches++;
            boolean home = norm.equals(m.getHomeTeamNormalized());
            int gf = home ? m.getHomeGoals() : m.getAwayGoals();
            int ga = home ? m.getAwayGoals() : m.getHomeGoals();
            s.goalsFor += gf;
            s.goalsAgainst += ga;
            if (gf > ga) s.wins++;
            else if (gf < ga) s.losses++;
            else s.draws++;
        }
        return s;
    }

    public TeamStats homeStats(String team, Competition competition, Integer season) {
        String norm = TeamNameNormalizer.normalize(team);
        TeamStats s = new TeamStats(norm + " (home)");
        for (Match m : matches.filter(team, competition, season)) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            if (!norm.equals(m.getHomeTeamNormalized())) continue;
            s.matches++;
            s.goalsFor += m.getHomeGoals();
            s.goalsAgainst += m.getAwayGoals();
            if (m.getHomeGoals() > m.getAwayGoals()) s.wins++;
            else if (m.getHomeGoals() < m.getAwayGoals()) s.losses++;
            else s.draws++;
        }
        return s;
    }

    public TeamStats awayStats(String team, Competition competition, Integer season) {
        String norm = TeamNameNormalizer.normalize(team);
        TeamStats s = new TeamStats(norm + " (away)");
        for (Match m : matches.filter(team, competition, season)) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            if (!norm.equals(m.getAwayTeamNormalized())) continue;
            s.matches++;
            s.goalsFor += m.getAwayGoals();
            s.goalsAgainst += m.getHomeGoals();
            if (m.getAwayGoals() > m.getHomeGoals()) s.wins++;
            else if (m.getAwayGoals() < m.getHomeGoals()) s.losses++;
            else s.draws++;
        }
        return s;
    }

    public HeadToHead headToHead(String teamA, String teamB) {
        String a = TeamNameNormalizer.normalize(teamA);
        String b = TeamNameNormalizer.normalize(teamB);
        List<Match> ms = matches.findBetween(teamA, teamB);
        HeadToHead h = new HeadToHead(a, b);
        for (Match m : ms) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            h.matches++;
            int hg = m.getHomeGoals(), ag = m.getAwayGoals();
            boolean homeIsA = a.equals(m.getHomeTeamNormalized());
            int gA = homeIsA ? hg : ag;
            int gB = homeIsA ? ag : hg;
            h.goalsA += gA;
            h.goalsB += gB;
            if (gA > gB) h.winsA++;
            else if (gB > gA) h.winsB++;
            else h.draws++;
        }
        return h;
    }

    public static class HeadToHead {
        public final String teamA;
        public final String teamB;
        public int matches;
        public int winsA;
        public int winsB;
        public int draws;
        public int goalsA;
        public int goalsB;

        public HeadToHead(String teamA, String teamB) {
            this.teamA = teamA;
            this.teamB = teamB;
        }
    }
}
