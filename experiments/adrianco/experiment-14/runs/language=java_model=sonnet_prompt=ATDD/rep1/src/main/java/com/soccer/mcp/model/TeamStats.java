package com.soccer.mcp.model;

public class TeamStats {
    private final String team;
    private int wins;
    private int draws;
    private int losses;
    private int goalsScored;
    private int goalsConceded;
    private int matchesPlayed;

    public TeamStats(String team) {
        this.team = team;
        this.wins = 0;
        this.draws = 0;
        this.losses = 0;
        this.goalsScored = 0;
        this.goalsConceded = 0;
        this.matchesPlayed = 0;
    }

    public void addMatch(boolean isHome, int homeGoals, int awayGoals) {
        matchesPlayed++;
        int scored = isHome ? homeGoals : awayGoals;
        int conceded = isHome ? awayGoals : homeGoals;
        goalsScored += scored;
        goalsConceded += conceded;
        if (scored > conceded) wins++;
        else if (scored == conceded) draws++;
        else losses++;
    }

    public String getTeam() { return team; }
    public int getWins() { return wins; }
    public int getDraws() { return draws; }
    public int getLosses() { return losses; }
    public int getGoalsScored() { return goalsScored; }
    public int getGoalsConceded() { return goalsConceded; }
    public int getMatchesPlayed() { return matchesPlayed; }
    public int getGoalDifference() { return goalsScored - goalsConceded; }
    public int getPoints() { return 3 * wins + draws; }

    @Override
    public String toString() {
        return String.format("%s: %d matches, %d wins, %d draws, %d losses, " +
                        "%d goals scored, %d goals conceded, %d goal difference, %d points",
                team, matchesPlayed, wins, draws, losses,
                goalsScored, goalsConceded, getGoalDifference(), getPoints());
    }
}
