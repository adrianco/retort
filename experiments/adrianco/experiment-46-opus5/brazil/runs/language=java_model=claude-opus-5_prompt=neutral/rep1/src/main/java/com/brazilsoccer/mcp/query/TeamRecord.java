package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.model.Match;

import java.util.Collection;

/**
 * Win / draw / loss and goal totals for one club over an arbitrary set of matches.
 * Points use the standard Brazilian three-points-for-a-win rule.
 */
public record TeamRecord(int played, int wins, int draws, int losses, int goalsFor, int goalsAgainst) {

    public static final TeamRecord EMPTY = new TeamRecord(0, 0, 0, 0, 0, 0);

    /** Aggregates the given matches from {@code teamId}'s point of view. */
    public static TeamRecord of(Collection<Match> matches, String teamId, Venue venue) {
        int played = 0;
        int wins = 0;
        int draws = 0;
        int losses = 0;
        int goalsFor = 0;
        int goalsAgainst = 0;
        for (Match match : matches) {
            if (!match.isPlayed() || !match.involves(teamId)) {
                continue;
            }
            boolean home = match.isHome(teamId);
            if ((venue == Venue.HOME && !home) || (venue == Venue.AWAY && home)) {
                continue;
            }
            played++;
            int gf = match.goalsFor(teamId);
            int ga = match.goalsAgainst(teamId);
            goalsFor += gf;
            goalsAgainst += ga;
            if (gf > ga) {
                wins++;
            } else if (gf < ga) {
                losses++;
            } else {
                draws++;
            }
        }
        return new TeamRecord(played, wins, draws, losses, goalsFor, goalsAgainst);
    }

    public int points() {
        return wins * 3 + draws;
    }

    public int goalDifference() {
        return goalsFor - goalsAgainst;
    }

    public double winRate() {
        return played == 0 ? 0 : (double) wins / played;
    }

    public double pointsPerGame() {
        return played == 0 ? 0 : (double) points() / played;
    }

    public double goalsForPerGame() {
        return played == 0 ? 0 : (double) goalsFor / played;
    }

    public TeamRecord plus(TeamRecord other) {
        return new TeamRecord(played + other.played, wins + other.wins, draws + other.draws,
                losses + other.losses, goalsFor + other.goalsFor, goalsAgainst + other.goalsAgainst);
    }
}
