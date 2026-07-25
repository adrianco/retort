package com.brazilsoccer.mcp.model;

/**
 * Optional extended in-match statistics, only available for matches sourced from
 * {@code BR-Football-Dataset.csv}. Any field may be {@code null} when the source did not
 * provide it.
 */
public record MatchStats(
        Integer homeCorners,
        Integer awayCorners,
        Integer homeAttacks,
        Integer awayAttacks,
        Integer homeShots,
        Integer awayShots,
        String halfTimeHomeResult,
        String halfTimeAwayResult) {

    public boolean hasAnyValue() {
        return homeCorners != null || awayCorners != null || homeAttacks != null || awayAttacks != null
                || homeShots != null || awayShots != null || halfTimeHomeResult != null;
    }
}
