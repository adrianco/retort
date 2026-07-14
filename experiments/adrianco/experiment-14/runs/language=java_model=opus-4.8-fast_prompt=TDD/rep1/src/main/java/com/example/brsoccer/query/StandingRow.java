/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    StandingRow.java
 * Purpose: One row of a computed league table: final ranking position plus the
 *          underlying team record. Standings are calculated from match results
 *          (3 points per win, 1 per draw) since the datasets contain no table.
 * Part of: query package (output of SoccerDatabase.standings).
 * ============================================================================
 */
package com.example.brsoccer.query;

/** A single ranked entry in a computed competition standings table. */
public record StandingRow(int position, TeamRecord record) {

    public String team() {
        return record.team();
    }

    public int points() {
        return record.points();
    }

    public int played() {
        return record.played();
    }

    public int goalDifference() {
        return record.goalDifference();
    }
}
