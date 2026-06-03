/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    model/Match.java
 * Purpose: Immutable domain model for a single soccer match, unified across
 *          every source CSV (Brasileirão, Copa do Brasil, Libertadores, the
 *          extended BR-Football stats file and the historical 2003-2019 file).
 *          Normalized team-name keys are pre-computed at load time so query
 *          matching is fast and tolerant of naming variations (state suffixes,
 *          accents, full club names).
 * ===========================================================================
 */
package com.brazilsoccer.mcp.model;

import java.time.LocalDate;

/**
 * A single match. Goal fields may be null when a source row is missing scores.
 */
public record Match(
        String competition,
        String homeTeam,
        String awayTeam,
        String homeTeamKey,
        String awayTeamKey,
        Integer homeGoal,
        Integer awayGoal,
        Integer season,
        LocalDate date,
        String round,
        String stage,
        String source) {

    /** True when both goal values are present. */
    public boolean hasScore() {
        return homeGoal != null && awayGoal != null;
    }

    /** Total goals scored in the match, or 0 when the score is unknown. */
    public int totalGoals() {
        return hasScore() ? homeGoal + awayGoal : 0;
    }

    /**
     * Winner of the match as a normalized team key, or null for a draw or an
     * unscored match.
     */
    public String winnerKey() {
        if (!hasScore() || homeGoal.equals(awayGoal)) {
            return null;
        }
        return homeGoal > awayGoal ? homeTeamKey : awayTeamKey;
    }

    /** True when the match involves the given normalized team key (home or away). */
    public boolean involves(String teamKey) {
        return homeTeamKey.equals(teamKey) || awayTeamKey.equals(teamKey);
    }
}
