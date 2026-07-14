/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    TeamRecord.java
 * Purpose: Aggregated win/draw/loss and goal record for a single team over a
 *          filtered set of matches, with derived points (3-1-0), goal
 *          difference and win-rate percentage.
 * Part of: query package (output of SoccerDatabase.teamRecord / standings).
 * ============================================================================
 */
package com.example.brsoccer.query;

/** A team's aggregated performance over some set of matches. */
public record TeamRecord(
        String team,
        int played,
        int wins,
        int draws,
        int losses,
        int goalsFor,
        int goalsAgainst) {

    public int points() {
        return wins * 3 + draws;
    }

    public int goalDifference() {
        return goalsFor - goalsAgainst;
    }

    /** Win rate as a percentage (0-100); 0 when no matches were played. */
    public double winRate() {
        return played == 0 ? 0.0 : (wins * 100.0) / played;
    }
}
