package com.braziliansoccer.mcp;

public record TeamStats(String team, int matches, int wins, int draws, int losses, int goalsFor, int goalsAgainst) {
    public int points() { return wins * 3 + draws; }
    public double winRate() { return matches == 0 ? 0.0 : wins * 100.0 / matches; }
}
