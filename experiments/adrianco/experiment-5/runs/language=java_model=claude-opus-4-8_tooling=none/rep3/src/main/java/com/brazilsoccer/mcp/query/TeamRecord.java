/*
 * ============================================================================
 * TeamRecord.java
 * ============================================================================
 * Context:
 *   Aggregated win/draw/loss and goal record for a team over some filtered set
 *   of matches (a season, a competition, home-only, etc.). Used by TeamService,
 *   CompetitionService (standings) and StatsService. Mutable while tallying;
 *   the query services build one up by feeding it match results.
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

/** Mutable accumulator of a team's results; also serves as a result object. */
public final class TeamRecord {

    public final String team;
    public int matches;
    public int wins;
    public int draws;
    public int losses;
    public int goalsFor;
    public int goalsAgainst;

    public TeamRecord(String team) {
        this.team = team;
    }

    /** Tally a single match outcome from this team's perspective. */
    public void add(int scored, int conceded) {
        matches++;
        goalsFor += scored;
        goalsAgainst += conceded;
        if (scored > conceded) wins++;
        else if (scored < conceded) losses++;
        else draws++;
    }

    /** 3 points per win, 1 per draw (standard league scoring). */
    public int points() {
        return wins * 3 + draws;
    }

    public int goalDifference() {
        return goalsFor - goalsAgainst;
    }

    /** Win rate as a 0-100 percentage. */
    public double winRate() {
        return matches == 0 ? 0.0 : (wins * 100.0) / matches;
    }
}
