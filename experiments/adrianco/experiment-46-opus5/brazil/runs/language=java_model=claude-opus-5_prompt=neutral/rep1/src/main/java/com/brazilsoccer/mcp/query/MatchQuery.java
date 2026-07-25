package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.model.Competition;

import java.time.LocalDate;

/**
 * Fluent criteria object for {@link MatchQueryService}. Every field is optional; unset fields do
 * not filter anything.
 */
public final class MatchQuery {

    private String teamId;
    private String opponentId;
    private String homeTeamId;
    private String awayTeamId;
    private Competition competition;
    private Integer season;
    private Integer seasonFrom;
    private Integer seasonTo;
    private LocalDate dateFrom;
    private LocalDate dateTo;
    private String round;
    private Venue venue = Venue.ALL;
    private boolean newestFirst = true;
    private int limit = 20;

    public static MatchQuery create() {
        return new MatchQuery();
    }

    public MatchQuery team(String id) {
        this.teamId = id;
        return this;
    }

    public MatchQuery opponent(String id) {
        this.opponentId = id;
        return this;
    }

    public MatchQuery homeTeam(String id) {
        this.homeTeamId = id;
        return this;
    }

    public MatchQuery awayTeam(String id) {
        this.awayTeamId = id;
        return this;
    }

    public MatchQuery competition(Competition competition) {
        this.competition = competition;
        return this;
    }

    public MatchQuery season(Integer season) {
        this.season = season;
        return this;
    }

    public MatchQuery seasonRange(Integer from, Integer to) {
        this.seasonFrom = from;
        this.seasonTo = to;
        return this;
    }

    public MatchQuery dateRange(LocalDate from, LocalDate to) {
        this.dateFrom = from;
        this.dateTo = to;
        return this;
    }

    public MatchQuery round(String round) {
        this.round = round;
        return this;
    }

    public MatchQuery venue(Venue venue) {
        this.venue = venue == null ? Venue.ALL : venue;
        return this;
    }

    public MatchQuery newestFirst(boolean newestFirst) {
        this.newestFirst = newestFirst;
        return this;
    }

    public MatchQuery limit(int limit) {
        this.limit = limit;
        return this;
    }

    public String teamId() {
        return teamId;
    }

    public String opponentId() {
        return opponentId;
    }

    public String homeTeamId() {
        return homeTeamId;
    }

    public String awayTeamId() {
        return awayTeamId;
    }

    public Competition competition() {
        return competition;
    }

    public Integer season() {
        return season;
    }

    public Integer seasonFrom() {
        return seasonFrom;
    }

    public Integer seasonTo() {
        return seasonTo;
    }

    public LocalDate dateFrom() {
        return dateFrom;
    }

    public LocalDate dateTo() {
        return dateTo;
    }

    public String round() {
        return round;
    }

    public Venue venue() {
        return venue;
    }

    public boolean newestFirst() {
        return newestFirst;
    }

    public int limit() {
        return limit;
    }
}
