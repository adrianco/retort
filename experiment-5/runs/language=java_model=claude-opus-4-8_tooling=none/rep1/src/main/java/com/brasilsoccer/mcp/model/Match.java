/*
 * ============================================================================
 * Match - immutable record of a single soccer match
 * ============================================================================
 * Context:
 *   Unified representation of a match coming from any of the five match CSV
 *   datasets (Brasileirao, Copa do Brasil, Libertadores, BR-Football extended
 *   stats, and the historical 2003-2019 Brasileirao). Each source has slightly
 *   different columns; the loader normalises them all into this shape.
 *
 *   Team names are stored in three forms (see TeamNames):
 *     - homeTeam   / awayTeam    : faithful display name, state suffix kept.
 *     - homeKey    / awayKey     : base key (suffix stripped) for cross-dataset
 *       matching, so "Palmeiras-SP", "Palmeiras" and "palmeiras" compare equal.
 *     - homeFullKey/ awayFullKey : suffix-qualified key that keeps same-base
 *       clubs distinct ("atletico-mg" vs "atletico-pr") for standings.
 *
 *   `competition` is the canonical competition name and `source` identifies the
 *   originating dataset, which lets standings logic pick one authoritative
 *   source per (competition, season) and avoid double-counting overlapping data.
 * ============================================================================
 */
package com.brasilsoccer.mcp.model;

import java.time.LocalDate;
import java.util.Optional;

public record Match(
        String competition,
        String source,
        LocalDate date,
        Integer season,
        String round,
        String stage,
        String stadium,
        String homeTeam,
        String awayTeam,
        String homeKey,
        String awayKey,
        String homeFullKey,
        String awayFullKey,
        int homeGoal,
        int awayGoal) {

    /** Total goals in the match. */
    public int totalGoals() {
        return homeGoal + awayGoal;
    }

    /** Absolute goal difference (margin of victory). */
    public int margin() {
        return Math.abs(homeGoal - awayGoal);
    }

    public boolean isDraw() {
        return homeGoal == awayGoal;
    }

    public boolean homeWin() {
        return homeGoal > awayGoal;
    }

    public boolean awayWin() {
        return awayGoal > homeGoal;
    }

    /** True if the given canonical team key played in this match. */
    public boolean involves(String teamKey) {
        return homeKey.equals(teamKey) || awayKey.equals(teamKey);
    }

    public Optional<LocalDate> dateOpt() {
        return Optional.ofNullable(date);
    }

    /**
     * Stable de-duplication key. Two records from different source datasets that
     * describe the same fixture (same teams, date and score) collapse to one.
     */
    public String dedupeKey() {
        return homeKey + "|" + awayKey + "|" + (date == null ? "?" : date)
                + "|" + homeGoal + "-" + awayGoal;
    }
}
