package com.soccer.mcp.query;

public final class TeamStats {
    private final String team;
    private final int played;
    private final int wins;
    private final int draws;
    private final int losses;
    private final int goalsFor;
    private final int goalsAgainst;

    public TeamStats(String team, int played, int wins, int draws, int losses,
                     int goalsFor, int goalsAgainst) {
        this.team = team;
        this.played = played;
        this.wins = wins;
        this.draws = draws;
        this.losses = losses;
        this.goalsFor = goalsFor;
        this.goalsAgainst = goalsAgainst;
    }

    public String team() { return team; }
    public int played() { return played; }
    public int wins() { return wins; }
    public int draws() { return draws; }
    public int losses() { return losses; }
    public int goalsFor() { return goalsFor; }
    public int goalsAgainst() { return goalsAgainst; }
    public int goalDifference() { return goalsFor - goalsAgainst; }
    public int points() { return wins * 3 + draws; }

    public double winRate() {
        if (played == 0) return 0.0;
        return (double) wins / played;
    }
}
