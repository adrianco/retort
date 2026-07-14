/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    Match.java
 * Purpose: Immutable record of a single soccer match unified across all five
 *          match datasets (Brasileirão, Copa do Brasil, Libertadores, the
 *          extended BR-Football statistics file and the historical 2003-2019
 *          file). Stores raw team names plus derived result helpers (win/draw,
 *          goal totals, head-to-head matching) used by the query layer.
 * Part of: model package (core domain entity).
 * ============================================================================
 */
package com.example.brsoccer.model;

import java.time.LocalDate;
import java.util.Optional;

/**
 * A single match. {@code round} doubles as the cup round / tournament stage and
 * may be null. Team names are stored as found in the source data; matching is
 * always done through {@link TeamNames} so suffixes/accents do not matter.
 */
public record Match(
        String competition,
        Integer season,
        LocalDate date,
        String round,
        String homeTeam,
        String awayTeam,
        int homeGoal,
        int awayGoal) {

    public boolean isHomeWin() {
        return homeGoal > awayGoal;
    }

    public boolean isAwayWin() {
        return awayGoal > homeGoal;
    }

    public boolean isDraw() {
        return homeGoal == awayGoal;
    }

    public int totalGoals() {
        return homeGoal + awayGoal;
    }

    /** Signed difference (home minus away). */
    public int goalDifference() {
        return homeGoal - awayGoal;
    }

    /** Absolute winning margin. */
    public int goalMargin() {
        return Math.abs(homeGoal - awayGoal);
    }

    /** The winning team's name, or empty for a draw. */
    public Optional<String> winner() {
        if (isHomeWin()) {
            return Optional.of(homeTeam);
        }
        if (isAwayWin()) {
            return Optional.of(awayTeam);
        }
        return Optional.empty();
    }

    /** The losing team's name, or empty for a draw. */
    public Optional<String> loser() {
        if (isHomeWin()) {
            return Optional.of(awayTeam);
        }
        if (isAwayWin()) {
            return Optional.of(homeTeam);
        }
        return Optional.empty();
    }

    /** True if the given team (any spelling) played in this match. */
    public boolean involves(String team) {
        String key = TeamNames.canonicalKey(team);
        return TeamNames.canonicalKey(homeTeam).equals(key)
                || TeamNames.canonicalKey(awayTeam).equals(key);
    }

    /** True if this match was contested between the two given teams (any order). */
    public boolean isBetween(String teamA, String teamB) {
        return involves(teamA) && involves(teamB)
                && !TeamNames.matches(teamA, teamB);
    }
}
