package com.braziliansoccer.mcp.model;

public record Match(
    String competition, String date, String homeTeam, String awayTeam,
    int homeGoals, int awayGoals, int season, String round, String stage
) {}
