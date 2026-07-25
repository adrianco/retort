package com.brazilsoccer.mcp.model;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Set;

/**
 * A single match node of the knowledge graph.
 *
 * <p>Teams are referenced by their canonical team id (see
 * {@code com.brazilsoccer.mcp.graph.TeamRegistry}) so that the many spellings found across the
 * CSV files collapse onto one node. {@code sources} records which CSV file(s) contributed to the
 * record, because the datasets overlap and are merged during loading.
 */
public record Match(
        String id,
        Competition competition,
        int season,
        String round,
        LocalDate date,
        LocalTime time,
        String homeTeamId,
        String awayTeamId,
        Integer homeGoals,
        Integer awayGoals,
        String arena,
        MatchStats stats,
        Set<String> sources) {

    /** A match is "played" only when both scores are known. */
    public boolean isPlayed() {
        return homeGoals != null && awayGoals != null;
    }

    public int totalGoals() {
        return isPlayed() ? homeGoals + awayGoals : 0;
    }

    public int goalDifference() {
        return isPlayed() ? Math.abs(homeGoals - awayGoals) : 0;
    }

    public boolean involves(String teamId) {
        return homeTeamId.equals(teamId) || awayTeamId.equals(teamId);
    }

    public String opponentOf(String teamId) {
        return homeTeamId.equals(teamId) ? awayTeamId : homeTeamId;
    }

    public boolean isHome(String teamId) {
        return homeTeamId.equals(teamId);
    }

    public Integer goalsFor(String teamId) {
        if (!isPlayed()) {
            return null;
        }
        return isHome(teamId) ? homeGoals : awayGoals;
    }

    public Integer goalsAgainst(String teamId) {
        if (!isPlayed()) {
            return null;
        }
        return isHome(teamId) ? awayGoals : homeGoals;
    }

    /** Outcome from the point of view of the given team, or {@code null} when not played. */
    public Outcome outcomeFor(String teamId) {
        if (!isPlayed()) {
            return null;
        }
        int gf = goalsFor(teamId);
        int ga = goalsAgainst(teamId);
        return gf > ga ? Outcome.WIN : gf < ga ? Outcome.LOSS : Outcome.DRAW;
    }

    /** Id of the winning team, or {@code null} for a draw or an unplayed match. */
    public String winnerTeamId() {
        if (!isPlayed() || homeGoals.intValue() == awayGoals.intValue()) {
            return null;
        }
        return homeGoals > awayGoals ? homeTeamId : awayTeamId;
    }

    public enum Outcome { WIN, DRAW, LOSS }
}
