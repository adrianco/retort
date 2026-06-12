/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    PlayerQuery.java
 * Purpose: Fluent, all-optional filter for the FIFA player dataset: by name,
 *          nationality, club, position and minimum overall rating, with an
 *          optional result limit. Results are returned highest-rated first.
 * Part of: query package (input to SoccerDatabase.searchPlayers).
 * ============================================================================
 */
package com.example.brsoccer.query;

/** A mutable, fluent set of optional player-filtering criteria. */
public final class PlayerQuery {

    private String name;
    private String nationality;
    private String club;
    private String position;
    private Integer minOverall;
    private int limit = 50;

    public PlayerQuery name(String name) {
        this.name = name;
        return this;
    }

    public PlayerQuery nationality(String nationality) {
        this.nationality = nationality;
        return this;
    }

    public PlayerQuery club(String club) {
        this.club = club;
        return this;
    }

    public PlayerQuery position(String position) {
        this.position = position;
        return this;
    }

    public PlayerQuery minOverall(Integer minOverall) {
        this.minOverall = minOverall;
        return this;
    }

    public PlayerQuery limit(int limit) {
        this.limit = limit;
        return this;
    }

    public String name() {
        return name;
    }

    public String nationality() {
        return nationality;
    }

    public String club() {
        return club;
    }

    public String position() {
        return position;
    }

    public Integer minOverall() {
        return minOverall;
    }

    public int limit() {
        return limit;
    }
}
