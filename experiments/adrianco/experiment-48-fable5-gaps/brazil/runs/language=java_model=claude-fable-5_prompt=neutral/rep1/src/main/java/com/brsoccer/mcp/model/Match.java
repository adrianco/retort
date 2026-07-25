package com.brsoccer.mcp.model;

import java.time.LocalDate;

/** A single match from any of the loaded datasets, with normalized team keys. */
public class Match {
    public final String competition;
    public final LocalDate date;
    public final int season;
    public final String round;   // nullable (league round or cup round)
    public final String stage;   // nullable (Libertadores stage)
    public final String venue;   // nullable (stadium)
    public final String homeRaw;
    public final String awayRaw;
    public final String homeKey;
    public final String awayKey;
    public final int homeGoals;
    public final int awayGoals;
    public final String source;

    // Extended stats (BR-Football-Dataset), merged onto duplicates when available.
    public Integer homeCorners, awayCorners, homeShots, awayShots;

    public Match(String competition, LocalDate date, int season, String round, String stage,
                 String venue, String homeRaw, String awayRaw, String homeKey, String awayKey,
                 int homeGoals, int awayGoals, String source) {
        this.competition = competition;
        this.date = date;
        this.season = season;
        this.round = round;
        this.stage = stage;
        this.venue = venue;
        this.homeRaw = homeRaw;
        this.awayRaw = awayRaw;
        this.homeKey = homeKey;
        this.awayKey = awayKey;
        this.homeGoals = homeGoals;
        this.awayGoals = awayGoals;
        this.source = source;
    }

    public int margin() {
        return Math.abs(homeGoals - awayGoals);
    }

    public int totalGoals() {
        return homeGoals + awayGoals;
    }
}
