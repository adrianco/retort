/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : Match.java
 *  Purpose : Immutable value object for a single match, unified across all the
 *            different match CSV schemas.
 *
 *  Context : Each source CSV has its own columns (Brasileirão has state codes
 *            and rounds, Libertadores has a "stage", the historical file uses
 *            Portuguese headers, BR-Football has a "tournament" column, etc.).
 *            KnowledgeGraph maps every one of them into this single shape so
 *            the query layer can treat them uniformly. Team names are kept both
 *            in their raw display form and as a canonical matching key.
 *
 *  Used by : KnowledgeGraph, QueryService
 * ============================================================================
 */
package com.brasileirao.mcp.model;

import java.time.LocalDate;

/** A unified, immutable representation of one match from any source dataset. */
public final class Match {

    private final String competition;   // canonical competition, e.g. "Brasileirão Série A"
    private final String source;        // originating file name
    private final String homeTeamRaw;
    private final String awayTeamRaw;
    private final String homeTeam;       // canonical key
    private final String awayTeam;       // canonical key
    private final String homeTeamDisplay;
    private final String awayTeamDisplay;
    private final Integer homeGoals;
    private final Integer awayGoals;
    private final Integer season;
    private final String round;          // round/stage label (nullable)
    private final LocalDate date;        // nullable
    private final String stage;          // tournament stage (nullable)
    private final String venue;          // stadium (nullable)

    public Match(String competition, String source, String homeTeamRaw, String awayTeamRaw,
                 Integer homeGoals, Integer awayGoals, Integer season, String round,
                 LocalDate date, String stage, String venue) {
        this.competition = competition;
        this.source = source;
        this.homeTeamRaw = homeTeamRaw;
        this.awayTeamRaw = awayTeamRaw;
        this.homeTeam = com.brasileirao.mcp.util.TeamNames.canonical(homeTeamRaw);
        this.awayTeam = com.brasileirao.mcp.util.TeamNames.canonical(awayTeamRaw);
        this.homeTeamDisplay = com.brasileirao.mcp.util.TeamNames.display(homeTeamRaw);
        this.awayTeamDisplay = com.brasileirao.mcp.util.TeamNames.display(awayTeamRaw);
        this.homeGoals = homeGoals;
        this.awayGoals = awayGoals;
        this.season = season;
        this.round = round;
        this.date = date;
        this.stage = stage;
        this.venue = venue;
    }

    public String competition() {
        return competition;
    }

    public String source() {
        return source;
    }

    public String homeTeamRaw() {
        return homeTeamRaw;
    }

    public String awayTeamRaw() {
        return awayTeamRaw;
    }

    public String homeTeam() {
        return homeTeam;
    }

    public String awayTeam() {
        return awayTeam;
    }

    public String homeTeamDisplay() {
        return homeTeamDisplay;
    }

    public String awayTeamDisplay() {
        return awayTeamDisplay;
    }

    public Integer homeGoals() {
        return homeGoals;
    }

    public Integer awayGoals() {
        return awayGoals;
    }

    public Integer season() {
        return season;
    }

    public String round() {
        return round;
    }

    public LocalDate date() {
        return date;
    }

    public String stage() {
        return stage;
    }

    public String venue() {
        return venue;
    }

    /** True when both goal counts are present (a result we can reason about). */
    public boolean hasResult() {
        return homeGoals != null && awayGoals != null;
    }

    /** True if the given canonical team key played in this match (home or away). */
    public boolean involves(String canonicalTeam) {
        return homeTeam.equals(canonicalTeam) || awayTeam.equals(canonicalTeam);
    }

    /** Canonical key of the winner, or {@code null} for a draw or unknown result. */
    public String winner() {
        if (!hasResult()) {
            return null;
        }
        if (homeGoals > awayGoals) {
            return homeTeam;
        }
        if (awayGoals > homeGoals) {
            return awayTeam;
        }
        return null;
    }

    /** A compact one-line description suitable for natural-language answers. */
    public String describe() {
        StringBuilder sb = new StringBuilder();
        if (date != null) {
            sb.append(date).append(": ");
        } else if (season != null) {
            sb.append(season).append(": ");
        }
        sb.append(homeTeamDisplay).append(' ');
        if (hasResult()) {
            sb.append(homeGoals).append('-').append(awayGoals);
        } else {
            sb.append("vs");
        }
        sb.append(' ').append(awayTeamDisplay);
        sb.append(" (").append(competition);
        if (round != null && !round.isBlank()) {
            sb.append(" Round ").append(round);
        } else if (stage != null && !stage.isBlank()) {
            sb.append(' ').append(stage);
        }
        sb.append(')');
        return sb.toString();
    }
}
