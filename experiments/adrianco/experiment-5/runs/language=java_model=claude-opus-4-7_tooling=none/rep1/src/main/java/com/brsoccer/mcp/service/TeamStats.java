package com.brsoccer.mcp.service;

public class TeamStats {
    public final String team;
    public int matches;
    public int wins;
    public int draws;
    public int losses;
    public int goalsFor;
    public int goalsAgainst;

    public TeamStats(String team) {
        this.team = team;
    }

    public int points() { return wins * 3 + draws; }

    public int goalDifference() { return goalsFor - goalsAgainst; }

    public double winRate() {
        return matches == 0 ? 0.0 : (double) wins / matches;
    }
}
