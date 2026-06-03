package com.soccer.mcp.query;

import com.soccer.mcp.model.Match;

import java.util.List;

public final class HeadToHead {
    private final String teamA;
    private final String teamB;
    private final int teamAWins;
    private final int teamBWins;
    private final int draws;
    private final int teamAGoals;
    private final int teamBGoals;
    private final List<Match> matches;

    public HeadToHead(String teamA, String teamB, int teamAWins, int teamBWins,
                      int draws, int teamAGoals, int teamBGoals, List<Match> matches) {
        this.teamA = teamA;
        this.teamB = teamB;
        this.teamAWins = teamAWins;
        this.teamBWins = teamBWins;
        this.draws = draws;
        this.teamAGoals = teamAGoals;
        this.teamBGoals = teamBGoals;
        this.matches = matches;
    }

    public String teamA() { return teamA; }
    public String teamB() { return teamB; }
    public int teamAWins() { return teamAWins; }
    public int teamBWins() { return teamBWins; }
    public int draws() { return draws; }
    public int teamAGoals() { return teamAGoals; }
    public int teamBGoals() { return teamBGoals; }
    public List<Match> matches() { return matches; }
    public int totalMatches() { return matches.size(); }
}
