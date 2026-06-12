/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    MatchQuery.java
 * Purpose: Fluent, all-optional filter describing which matches to return:
 *          by team (optionally restricted to home/away), opponent, competition,
 *          season and/or date range. Unset criteria are simply ignored, so a
 *          blank query matches every loaded match.
 * Part of: query package (input to SoccerDatabase match/statistics queries).
 * ============================================================================
 */
package com.example.brsoccer.query;

import java.time.LocalDate;

/** A mutable, fluent set of optional match-filtering criteria. */
public final class MatchQuery {

    private String team;
    private String opponent;
    private String competition;
    private Integer season;
    private LocalDate from;
    private LocalDate to;
    private Venue venue = Venue.ANY;

    public MatchQuery team(String team) {
        this.team = team;
        return this;
    }

    public MatchQuery opponent(String opponent) {
        this.opponent = opponent;
        return this;
    }

    public MatchQuery competition(String competition) {
        this.competition = competition;
        return this;
    }

    public MatchQuery season(Integer season) {
        this.season = season;
        return this;
    }

    public MatchQuery from(LocalDate from) {
        this.from = from;
        return this;
    }

    public MatchQuery to(LocalDate to) {
        this.to = to;
        return this;
    }

    public MatchQuery venue(Venue venue) {
        this.venue = venue == null ? Venue.ANY : venue;
        return this;
    }

    public String team() {
        return team;
    }

    public String opponent() {
        return opponent;
    }

    public String competition() {
        return competition;
    }

    public Integer season() {
        return season;
    }

    public LocalDate from() {
        return from;
    }

    public LocalDate to() {
        return to;
    }

    public Venue venue() {
        return venue;
    }
}
