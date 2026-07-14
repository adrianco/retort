package com.soccer.mcp.model;

public class Standing {
    private int position;
    private final TeamStats stats;

    public Standing(int position, TeamStats stats) {
        this.position = position;
        this.stats = stats;
    }

    public int getPosition() { return position; }
    public void setPosition(int position) { this.position = position; }
    public TeamStats getStats() { return stats; }
    public String getTeam() { return stats.getTeam(); }
    public int getPoints() { return stats.getPoints(); }

    @Override
    public String toString() {
        return String.format("%2d. %-30s %3d pts  W:%2d D:%2d L:%2d  GF:%3d GA:%3d GD:%+d",
                position, stats.getTeam(), stats.getPoints(),
                stats.getWins(), stats.getDraws(), stats.getLosses(),
                stats.getGoalsScored(), stats.getGoalsConceded(), stats.getGoalDifference());
    }
}
