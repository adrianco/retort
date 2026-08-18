package com.braziliansoccer.mcp;

import java.time.LocalDate;

public record Match(String competition, LocalDate date, String homeTeam, String awayTeam, int homeGoals, int awayGoals,
                    Integer season, String round, String stage, String stadium) {
    public int margin() { return Math.abs(homeGoals - awayGoals); }
    public String scoreLine() { return homeTeam + " " + homeGoals + "-" + awayGoals + " " + awayTeam; }
}
