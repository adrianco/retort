package com.brazilsoccer.query;

/** Running win/draw/loss and goal totals for one team across a set of matches. */
public final class TeamTally {

    private final String team;
    private int played;
    private int won;
    private int drawn;
    private int lost;
    private int goalsFor;
    private int goalsAgainst;

    public TeamTally(String team) {
        this.team = team;
    }

    /** Records one result from this team's point of view. */
    public void addResult(int goalsScored, int goalsConceded) {
        played++;
        goalsFor += goalsScored;
        goalsAgainst += goalsConceded;
        if (goalsScored > goalsConceded) {
            won++;
        } else if (goalsScored == goalsConceded) {
            drawn++;
        } else {
            lost++;
        }
    }

    public String team() {
        return team;
    }

    public int played() {
        return played;
    }

    public int won() {
        return won;
    }

    public int drawn() {
        return drawn;
    }

    public int lost() {
        return lost;
    }

    public int goalsFor() {
        return goalsFor;
    }

    public int goalsAgainst() {
        return goalsAgainst;
    }

    public int goalDifference() {
        return goalsFor - goalsAgainst;
    }

    /** League points: three for a win, one for a draw. */
    public int points() {
        return won * 3 + drawn;
    }

    /** Percentage of matches won, 0 when no matches have been played. */
    public double winRate() {
        return played == 0 ? 0.0 : 100.0 * won / played;
    }
}
