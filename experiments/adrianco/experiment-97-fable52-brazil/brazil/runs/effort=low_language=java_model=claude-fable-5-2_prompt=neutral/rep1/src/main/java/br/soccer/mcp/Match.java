package br.soccer.mcp;

import java.time.LocalDate;

/** One match, unified across the five match CSV files. Team fields hold canonical team keys. */
final class Match {
    String source;        // CSV file name
    String competition;   // one of DataStore.SERIE_A, ... constants
    int season;
    LocalDate date;       // may be null
    String time;          // may be null
    String home;          // canonical key
    String away;          // canonical key
    String homeRaw;
    String awayRaw;
    Integer homeGoals;    // null when the match has no recorded score
    Integer awayGoals;
    String round;         // may be null
    String stage;         // may be null (e.g. "final", "group stage")
    String arena;         // may be null
    Integer homeCorners, awayCorners, homeShots, awayShots, homeAttacks, awayAttacks;
    /** False when another file covers the same competition+season more completely (duplicate coverage). */
    boolean primary = true;

    boolean played() { return homeGoals != null && awayGoals != null; }
    boolean involves(String team) { return home.equals(team) || away.equals(team); }
    int margin() { return Math.abs(homeGoals - awayGoals); }
    int totalGoals() { return homeGoals + awayGoals; }
}
