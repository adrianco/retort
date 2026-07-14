/*
 * ============================================================================
 * Results - immutable value objects returned by the KnowledgeBase queries
 * ============================================================================
 * Context:
 *   Plain data carriers (Java records) that decouple the query engine from the
 *   presentation layer. The KnowledgeBase computes these; the MCP server (and
 *   the tests) render / assert on them. Keeping them dumb and immutable makes
 *   the BDD tests straightforward: given data, when queried, then assert fields.
 * ============================================================================
 */
package com.brasilsoccer.mcp.query;

import com.brasilsoccer.mcp.model.Match;
import com.brasilsoccer.mcp.model.Player;

import java.util.List;

public final class Results {

    private Results() {
    }

    /** Result of a match search, optionally with a head-to-head summary. */
    public record MatchSearch(List<Match> matches, int totalFound, HeadToHead headToHead) {
    }

    /** Aggregate head-to-head record between two teams. */
    public record HeadToHead(
            String team1, String team2,
            int team1Wins, int team2Wins, int draws,
            int team1Goals, int team2Goals,
            List<Match> matches) {
        public int total() {
            return team1Wins + team2Wins + draws;
        }
    }

    /** A team's win/loss/draw record over a filtered set of matches. */
    public record TeamRecord(
            String team, Integer season, String competition, String venue,
            int played, int wins, int draws, int losses,
            int goalsFor, int goalsAgainst) {
        public int points() {
            return wins * 3 + draws;
        }

        public int goalDifference() {
            return goalsFor - goalsAgainst;
        }

        public double winRate() {
            return played == 0 ? 0.0 : (double) wins / played * 100.0;
        }
    }

    /** One row of a calculated league table. */
    public record StandingRow(
            int position, String team,
            int played, int wins, int draws, int losses,
            int goalsFor, int goalsAgainst, int goalDifference, int points) {
    }

    /** A full calculated league table for a competition + season. */
    public record Standings(String competition, int season, String source, List<StandingRow> rows) {
    }

    /** Aggregate statistics over a set of matches. */
    public record LeagueStats(
            String competition, Integer season, String source,
            int matches, int totalGoals, double avgGoalsPerMatch,
            int homeWins, int awayWins, int draws,
            double homeWinRate, double awayWinRate, double drawRate) {
    }

    /** Result of a player search. */
    public record PlayerSearch(List<Player> players, int totalFound) {
    }

    /** High-level description of everything loaded. */
    public record Summary(
            int totalMatches, int totalPlayers,
            List<String> competitions, List<Integer> seasons) {
    }
}
