package com.soccer.mcp.model;

import java.time.LocalDate;

public class Match {
    private final String competition;
    private final LocalDate date;
    private final String homeTeam;
    private final String awayTeam;
    private final int homeGoals;
    private final int awayGoals;
    private final Integer season;
    private final String round;
    private final String stage;
    private final String arena;

    public Match(String competition, LocalDate date, String homeTeam, String awayTeam,
                 int homeGoals, int awayGoals, Integer season, String round, String stage, String arena) {
        this.competition = competition;
        this.date = date;
        this.homeTeam = homeTeam;
        this.awayTeam = awayTeam;
        this.homeGoals = homeGoals;
        this.awayGoals = awayGoals;
        this.season = season;
        this.round = round;
        this.stage = stage;
        this.arena = arena;
    }

    public String getCompetition() { return competition; }
    public LocalDate getDate() { return date; }
    public String getHomeTeam() { return homeTeam; }
    public String getAwayTeam() { return awayTeam; }
    public int getHomeGoals() { return homeGoals; }
    public int getAwayGoals() { return awayGoals; }
    public Integer getSeason() { return season; }
    public String getRound() { return round; }
    public String getStage() { return stage; }
    public String getArena() { return arena; }

    public int getGoalDifference() {
        return homeGoals - awayGoals;
    }

    public String getResult() {
        if (homeGoals > awayGoals) return homeTeam + " wins";
        if (awayGoals > homeGoals) return awayTeam + " wins";
        return "Draw";
    }

    @Override
    public String toString() {
        String dateStr = date != null ? date.toString() : "unknown";
        return String.format("[%s] %s %d-%d %s (%s, Round %s)",
                competition, homeTeam, homeGoals, awayGoals, awayTeam, dateStr, round);
    }
}
