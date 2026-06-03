/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    query/QueryResults.java
 * Purpose: Plain immutable value types returned by SoccerQueries: aggregated
 *          team statistics, head-to-head summaries and computed league-table
 *          rows. Kept free of presentation concerns so they can be unit tested
 *          directly and serialized by the MCP layer.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.query;

public final class QueryResults {

    private QueryResults() {
    }

    /** Win/draw/loss and goal aggregates for one team over a set of matches. */
    public record TeamStats(
            String team,
            int matches,
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

        public double winRate() {
            return matches == 0 ? 0.0 : (double) wins / matches;
        }
    }

    /** Head-to-head record between two teams from team A's perspective. */
    public record HeadToHead(
            String teamA,
            String teamB,
            int totalMatches,
            int teamAWins,
            int teamBWins,
            int draws,
            int teamAGoals,
            int teamBGoals) {
    }

    /** One row of a computed league table. */
    public record StandingRow(
            int position,
            String team,
            int played,
            int wins,
            int draws,
            int losses,
            int goalsFor,
            int goalsAgainst,
            int points) {

        public int goalDifference() {
            return goalsFor - goalsAgainst;
        }
    }
}
