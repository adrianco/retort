/*
 * ============================================================================
 * TeamService.java
 * ============================================================================
 * Context:
 *   Implements the spec's "Team Queries" category: win/draw/loss and goal
 *   records for a team, optionally scoped by season, competition and venue
 *   (home / away / all), plus head-to-head comparisons between two teams.
 *
 *   Only matches with a known score contribute to records. Venue filtering and
 *   competition filtering reuse the same accent-insensitive key matching as
 *   MatchService.
 * ============================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.data.Competitions;
import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.model.Match;

import java.util.ArrayList;
import java.util.List;

/** Query service for team records and head-to-head comparisons. */
public final class TeamService {

    /** Venue filter for record queries. */
    public enum Venue { ALL, HOME, AWAY }

    private final DataStore store;

    public TeamService(DataStore store) {
        this.store = store;
    }

    /** Result of a head-to-head comparison between two teams. */
    public static final class HeadToHead {
        public final String teamA;
        public final String teamB;
        public int teamAWins;
        public int teamBWins;
        public int draws;
        public int teamAGoals;
        public int teamBGoals;
        public final List<Match> matches = new ArrayList<>();

        public HeadToHead(String teamA, String teamB) {
            this.teamA = teamA;
            this.teamB = teamB;
        }
    }

    /**
     * Compute a team's aggregate record. The returned record's {@code team}
     * field holds the best display name found for the queried team.
     */
    public TeamRecord record(String team, Integer season, String competition, Venue venue) {
        String teamKey = TeamNames.key(team);
        Venue v = venue == null ? Venue.ALL : venue;

        String display = team;
        TeamRecord rec = new TeamRecord(team);
        for (Match m : store.matches()) {
            if (!m.hasScore()) continue;
            if (season != null && m.season() != season) continue;
            if (competition != null && !Competitions.matches(m.competition(), competition)) continue;

            boolean isHome = MatchService.keyMatches(m.homeTeamKey(), teamKey);
            boolean isAway = MatchService.keyMatches(m.awayTeamKey(), teamKey);
            if (!isHome && !isAway) continue;
            if (v == Venue.HOME && !isHome) continue;
            if (v == Venue.AWAY && !isAway) continue;

            if (isHome) {
                rec.add(m.homeGoal(), m.awayGoal());
                display = m.homeTeam();
            } else {
                rec.add(m.awayGoal(), m.homeGoal());
                display = m.awayTeam();
            }
        }
        // Re-label the record with the discovered display name.
        TeamRecord labelled = new TeamRecord(display);
        labelled.matches = rec.matches;
        labelled.wins = rec.wins;
        labelled.draws = rec.draws;
        labelled.losses = rec.losses;
        labelled.goalsFor = rec.goalsFor;
        labelled.goalsAgainst = rec.goalsAgainst;
        return labelled;
    }

    /** Compute the head-to-head record between two teams (all competitions). */
    public HeadToHead headToHead(String teamA, String teamB, Integer season, String competition) {
        String keyA = TeamNames.key(teamA);
        String keyB = TeamNames.key(teamB);

        String displayA = teamA;
        String displayB = teamB;
        HeadToHead h2h = new HeadToHead(teamA, teamB);
        for (Match m : store.matches()) {
            if (season != null && m.season() != season) continue;
            if (competition != null && !Competitions.matches(m.competition(), competition)) continue;

            boolean homeIsA = MatchService.keyMatches(m.homeTeamKey(), keyA);
            boolean awayIsA = MatchService.keyMatches(m.awayTeamKey(), keyA);
            boolean homeIsB = MatchService.keyMatches(m.homeTeamKey(), keyB);
            boolean awayIsB = MatchService.keyMatches(m.awayTeamKey(), keyB);

            boolean aVsB = (homeIsA && awayIsB) || (awayIsA && homeIsB);
            if (!aVsB) continue;

            h2h.matches.add(m);
            if (homeIsA) { displayA = m.homeTeam(); displayB = m.awayTeam(); }
            else { displayA = m.awayTeam(); displayB = m.homeTeam(); }

            if (!m.hasScore()) continue;
            int aGoals = homeIsA ? m.homeGoal() : m.awayGoal();
            int bGoals = homeIsA ? m.awayGoal() : m.homeGoal();
            h2h.teamAGoals += aGoals;
            h2h.teamBGoals += bGoals;
            if (aGoals > bGoals) h2h.teamAWins++;
            else if (aGoals < bGoals) h2h.teamBWins++;
            else h2h.draws++;
        }

        HeadToHead labelled = new HeadToHead(displayA, displayB);
        labelled.teamAWins = h2h.teamAWins;
        labelled.teamBWins = h2h.teamBWins;
        labelled.draws = h2h.draws;
        labelled.teamAGoals = h2h.teamAGoals;
        labelled.teamBGoals = h2h.teamBGoals;
        labelled.matches.addAll(h2h.matches);
        return labelled;
    }
}
