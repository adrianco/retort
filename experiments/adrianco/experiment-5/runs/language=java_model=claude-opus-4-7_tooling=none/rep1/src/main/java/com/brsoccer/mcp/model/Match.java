package com.brsoccer.mcp.model;

import java.time.LocalDate;
import java.util.Objects;

public class Match {
    private final Competition competition;
    private final LocalDate date;
    private final String homeTeam;
    private final String homeTeamNormalized;
    private final String homeTeamState;
    private final String awayTeam;
    private final String awayTeamNormalized;
    private final String awayTeamState;
    private final Integer homeGoals;
    private final Integer awayGoals;
    private final Integer season;
    private final Integer round;
    private final String stage;
    private final String stadium;
    private final Integer homeCorners;
    private final Integer awayCorners;
    private final Integer homeShots;
    private final Integer awayShots;

    private Match(Builder b) {
        this.competition = b.competition;
        this.date = b.date;
        this.homeTeam = b.homeTeam;
        this.homeTeamNormalized = b.homeTeamNormalized;
        this.homeTeamState = b.homeTeamState;
        this.awayTeam = b.awayTeam;
        this.awayTeamNormalized = b.awayTeamNormalized;
        this.awayTeamState = b.awayTeamState;
        this.homeGoals = b.homeGoals;
        this.awayGoals = b.awayGoals;
        this.season = b.season;
        this.round = b.round;
        this.stage = b.stage;
        this.stadium = b.stadium;
        this.homeCorners = b.homeCorners;
        this.awayCorners = b.awayCorners;
        this.homeShots = b.homeShots;
        this.awayShots = b.awayShots;
    }

    public Competition getCompetition() { return competition; }
    public LocalDate getDate() { return date; }
    public String getHomeTeam() { return homeTeam; }
    public String getHomeTeamNormalized() { return homeTeamNormalized; }
    public String getHomeTeamState() { return homeTeamState; }
    public String getAwayTeam() { return awayTeam; }
    public String getAwayTeamNormalized() { return awayTeamNormalized; }
    public String getAwayTeamState() { return awayTeamState; }
    public Integer getHomeGoals() { return homeGoals; }
    public Integer getAwayGoals() { return awayGoals; }
    public Integer getSeason() { return season; }
    public Integer getRound() { return round; }
    public String getStage() { return stage; }
    public String getStadium() { return stadium; }
    public Integer getHomeCorners() { return homeCorners; }
    public Integer getAwayCorners() { return awayCorners; }
    public Integer getHomeShots() { return homeShots; }
    public Integer getAwayShots() { return awayShots; }

    public boolean isHomeWin() {
        return homeGoals != null && awayGoals != null && homeGoals > awayGoals;
    }

    public boolean isAwayWin() {
        return homeGoals != null && awayGoals != null && awayGoals > homeGoals;
    }

    public boolean isDraw() {
        return homeGoals != null && awayGoals != null && homeGoals.equals(awayGoals);
    }

    public int totalGoals() {
        return (homeGoals == null ? 0 : homeGoals) + (awayGoals == null ? 0 : awayGoals);
    }

    public boolean involvesTeam(String normalizedName) {
        return Objects.equals(homeTeamNormalized, normalizedName)
            || Objects.equals(awayTeamNormalized, normalizedName);
    }

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private Competition competition;
        private LocalDate date;
        private String homeTeam;
        private String homeTeamNormalized;
        private String homeTeamState;
        private String awayTeam;
        private String awayTeamNormalized;
        private String awayTeamState;
        private Integer homeGoals;
        private Integer awayGoals;
        private Integer season;
        private Integer round;
        private String stage;
        private String stadium;
        private Integer homeCorners;
        private Integer awayCorners;
        private Integer homeShots;
        private Integer awayShots;

        public Builder competition(Competition v) { this.competition = v; return this; }
        public Builder date(LocalDate v) { this.date = v; return this; }
        public Builder homeTeam(String v) { this.homeTeam = v; return this; }
        public Builder homeTeamNormalized(String v) { this.homeTeamNormalized = v; return this; }
        public Builder homeTeamState(String v) { this.homeTeamState = v; return this; }
        public Builder awayTeam(String v) { this.awayTeam = v; return this; }
        public Builder awayTeamNormalized(String v) { this.awayTeamNormalized = v; return this; }
        public Builder awayTeamState(String v) { this.awayTeamState = v; return this; }
        public Builder homeGoals(Integer v) { this.homeGoals = v; return this; }
        public Builder awayGoals(Integer v) { this.awayGoals = v; return this; }
        public Builder season(Integer v) { this.season = v; return this; }
        public Builder round(Integer v) { this.round = v; return this; }
        public Builder stage(String v) { this.stage = v; return this; }
        public Builder stadium(String v) { this.stadium = v; return this; }
        public Builder homeCorners(Integer v) { this.homeCorners = v; return this; }
        public Builder awayCorners(Integer v) { this.awayCorners = v; return this; }
        public Builder homeShots(Integer v) { this.homeShots = v; return this; }
        public Builder awayShots(Integer v) { this.awayShots = v; return this; }

        public Match build() { return new Match(this); }
    }
}
