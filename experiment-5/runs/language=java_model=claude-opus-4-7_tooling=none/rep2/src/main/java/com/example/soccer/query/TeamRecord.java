package com.example.soccer.query;

public final class TeamRecord {
    public final String team;
    public int matches;
    public int wins;
    public int draws;
    public int losses;
    public int goalsFor;
    public int goalsAgainst;

    public TeamRecord(String team) {
        this.team = team;
    }

    public int points() {
        return wins * 3 + draws;
    }

    public int goalDifference() {
        return goalsFor - goalsAgainst;
    }

    public double winRate() {
        if (matches == 0) return 0;
        return (double) wins / matches;
    }
}
