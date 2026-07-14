/*
 * ============================================================================
 * Match.java
 * ============================================================================
 * Context:
 *   Unified, immutable representation of a single soccer match drawn from any
 *   of the bundled CSV datasets. The various source files use different column
 *   layouts, team-naming conventions and date formats; the loaders in
 *   com.brazilsoccer.mcp.data normalize all of them into this common shape so
 *   the query services can treat every competition uniformly.
 *
 * Notes:
 *   - homeTeam / awayTeam hold the cleaned display names (state/country suffix
 *     stripped). homeTeamKey / awayTeamKey hold the accent-insensitive match
 *     keys produced by TeamNames.key(...).
 *   - Goals are nullable (Integer) because a few historical rows omit scores.
 *   - Optional extended statistics (corners, shots) are only present for the
 *     BR-Football dataset and are null elsewhere.
 * ============================================================================
 */
package com.brazilsoccer.mcp.model;

import java.time.LocalDate;

/** Immutable unified match record shared across all datasets. */
public final class Match {

    private final String competition;
    private final int season;
    private final LocalDate date;     // may be null if the source row had no parseable date
    private final String round;       // nullable
    private final String stage;       // nullable (Libertadores only)

    private final String homeTeam;
    private final String awayTeam;
    private final String homeTeamKey;
    private final String awayTeamKey;

    private final Integer homeGoal;   // nullable
    private final Integer awayGoal;   // nullable

    private final String stadium;     // nullable
    private final String source;      // originating CSV file name

    // Optional extended stats (BR-Football dataset); null when unavailable.
    private final Integer homeShots;
    private final Integer awayShots;
    private final Integer homeCorners;
    private final Integer awayCorners;

    public Match(String competition, int season, LocalDate date, String round, String stage,
                 String homeTeam, String awayTeam, String homeTeamKey, String awayTeamKey,
                 Integer homeGoal, Integer awayGoal, String stadium, String source,
                 Integer homeShots, Integer awayShots, Integer homeCorners, Integer awayCorners) {
        this.competition = competition;
        this.season = season;
        this.date = date;
        this.round = round;
        this.stage = stage;
        this.homeTeam = homeTeam;
        this.awayTeam = awayTeam;
        this.homeTeamKey = homeTeamKey;
        this.awayTeamKey = awayTeamKey;
        this.homeGoal = homeGoal;
        this.awayGoal = awayGoal;
        this.stadium = stadium;
        this.source = source;
        this.homeShots = homeShots;
        this.awayShots = awayShots;
        this.homeCorners = homeCorners;
        this.awayCorners = awayCorners;
    }

    public String competition() { return competition; }
    public int season() { return season; }
    public LocalDate date() { return date; }
    public String round() { return round; }
    public String stage() { return stage; }
    public String homeTeam() { return homeTeam; }
    public String awayTeam() { return awayTeam; }
    public String homeTeamKey() { return homeTeamKey; }
    public String awayTeamKey() { return awayTeamKey; }
    public Integer homeGoal() { return homeGoal; }
    public Integer awayGoal() { return awayGoal; }
    public String stadium() { return stadium; }
    public String source() { return source; }
    public Integer homeShots() { return homeShots; }
    public Integer awayShots() { return awayShots; }
    public Integer homeCorners() { return homeCorners; }
    public Integer awayCorners() { return awayCorners; }

    /** True when both goal counts are known (so a result can be derived). */
    public boolean hasScore() {
        return homeGoal != null && awayGoal != null;
    }

    /** True if the named team key is the home side. */
    public boolean isHome(String teamKey) {
        return homeTeamKey.equals(teamKey);
    }

    /** True if the named team key participated (home or away). */
    public boolean involves(String teamKey) {
        return homeTeamKey.equals(teamKey) || awayTeamKey.equals(teamKey);
    }

    /** Total goals in the match, or 0 if the score is unknown. */
    public int totalGoals() {
        return hasScore() ? homeGoal + awayGoal : 0;
    }

    /** Human-readable one-line summary, e.g. "2019-10-27: Flamengo 5-0 Gremio". */
    public String describe() {
        String score = hasScore() ? homeGoal + "-" + awayGoal : "?-?";
        String d = date != null ? date.toString() : "????-??-??";
        return d + ": " + homeTeam + " " + score + " " + awayTeam;
    }
}
