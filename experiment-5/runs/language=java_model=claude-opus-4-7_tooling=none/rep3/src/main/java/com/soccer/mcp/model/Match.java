package com.soccer.mcp.model;

import java.time.LocalDate;

public final class Match {
    private final String homeTeam;
    private final String homeTeamState;
    private final String awayTeam;
    private final String awayTeamState;
    private final int homeGoals;
    private final int awayGoals;
    private final LocalDate date;
    private final Integer season;
    private final String competition;
    private final String round;
    private final String stage;
    private final String stadium;
    private final Integer homeCorners;
    private final Integer awayCorners;
    private final Integer homeShots;
    private final Integer awayShots;

    private Match(Builder b) {
        this.homeTeam = b.homeTeam;
        this.homeTeamState = b.homeTeamState;
        this.awayTeam = b.awayTeam;
        this.awayTeamState = b.awayTeamState;
        this.homeGoals = b.homeGoals;
        this.awayGoals = b.awayGoals;
        this.date = b.date;
        this.season = b.season;
        this.competition = b.competition;
        this.round = b.round;
        this.stage = b.stage;
        this.stadium = b.stadium;
        this.homeCorners = b.homeCorners;
        this.awayCorners = b.awayCorners;
        this.homeShots = b.homeShots;
        this.awayShots = b.awayShots;
    }

    public String homeTeam() { return homeTeam; }
    public String homeTeamState() { return homeTeamState; }
    public String awayTeam() { return awayTeam; }
    public String awayTeamState() { return awayTeamState; }
    public int homeGoals() { return homeGoals; }
    public int awayGoals() { return awayGoals; }
    public LocalDate date() { return date; }
    public Integer season() { return season; }
    public String competition() { return competition; }
    public String round() { return round; }
    public String stage() { return stage; }
    public String stadium() { return stadium; }
    public Integer homeCorners() { return homeCorners; }
    public Integer awayCorners() { return awayCorners; }
    public Integer homeShots() { return homeShots; }
    public Integer awayShots() { return awayShots; }

    public int totalGoals() { return homeGoals + awayGoals; }
    public boolean isDraw() { return homeGoals == awayGoals; }
    public boolean isHomeWin() { return homeGoals > awayGoals; }
    public boolean isAwayWin() { return awayGoals > homeGoals; }

    /** Returns name of winning team, or null on draw. */
    public String winner() {
        if (isHomeWin()) return homeTeam;
        if (isAwayWin()) return awayTeam;
        return null;
    }

    public static Builder builder() { return new Builder(); }

    public static final class Builder {
        private String homeTeam;
        private String homeTeamState;
        private String awayTeam;
        private String awayTeamState;
        private int homeGoals;
        private int awayGoals;
        private LocalDate date;
        private Integer season;
        private String competition;
        private String round;
        private String stage;
        private String stadium;
        private Integer homeCorners;
        private Integer awayCorners;
        private Integer homeShots;
        private Integer awayShots;

        public Builder homeTeam(String v) { this.homeTeam = v; return this; }
        public Builder homeTeamState(String v) { this.homeTeamState = v; return this; }
        public Builder awayTeam(String v) { this.awayTeam = v; return this; }
        public Builder awayTeamState(String v) { this.awayTeamState = v; return this; }
        public Builder homeGoals(int v) { this.homeGoals = v; return this; }
        public Builder awayGoals(int v) { this.awayGoals = v; return this; }
        public Builder date(LocalDate v) { this.date = v; return this; }
        public Builder season(Integer v) { this.season = v; return this; }
        public Builder competition(String v) { this.competition = v; return this; }
        public Builder round(String v) { this.round = v; return this; }
        public Builder stage(String v) { this.stage = v; return this; }
        public Builder stadium(String v) { this.stadium = v; return this; }
        public Builder homeCorners(Integer v) { this.homeCorners = v; return this; }
        public Builder awayCorners(Integer v) { this.awayCorners = v; return this; }
        public Builder homeShots(Integer v) { this.homeShots = v; return this; }
        public Builder awayShots(Integer v) { this.awayShots = v; return this; }

        public Match build() { return new Match(this); }
    }
}
