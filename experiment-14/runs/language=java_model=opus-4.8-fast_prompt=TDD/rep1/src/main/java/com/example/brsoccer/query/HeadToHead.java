/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    HeadToHead.java
 * Purpose: Summary of all encounters between two teams: each side's win count,
 *          the number of draws and the full list of matches (most recent first
 *          as produced by the query layer).
 * Part of: query package (output of SoccerDatabase.headToHead).
 * ============================================================================
 */
package com.example.brsoccer.query;

import com.example.brsoccer.model.Match;

import java.util.List;

/** Head-to-head record between {@code teamA} and {@code teamB}. */
public record HeadToHead(
        String teamA,
        String teamB,
        int teamAWins,
        int teamBWins,
        int draws,
        List<Match> matches) {

    public int totalMatches() {
        return matches.size();
    }
}
