package com.brazilsoccer.mcp;

/** A single match, normalized from one of the source datasets. */
public final class Match {

    final Competition competition;
    final int season;            // -1 if unknown
    final String date;           // ISO yyyy-MM-dd, or null
    final String round;          // round/stage label, or null

    final String homeDisplay;
    final String awayDisplay;
    final String homeBaseKey;    // accent/state-insensitive base name
    final String awayBaseKey;
    final String homeIdentity;   // base + state, distinguishes same-named clubs
    final String awayIdentity;

    final int homeGoals;
    final int awayGoals;

    Match(Competition competition, int season, String date, String round,
          String homeDisplay, String awayDisplay,
          String homeBaseKey, String awayBaseKey,
          String homeIdentity, String awayIdentity,
          int homeGoals, int awayGoals) {
        this.competition = competition;
        this.season = season;
        this.date = date;
        this.round = round;
        this.homeDisplay = homeDisplay;
        this.awayDisplay = awayDisplay;
        this.homeBaseKey = homeBaseKey;
        this.awayBaseKey = awayBaseKey;
        this.homeIdentity = homeIdentity;
        this.awayIdentity = awayIdentity;
        this.homeGoals = homeGoals;
        this.awayGoals = awayGoals;
    }

    boolean involvesBase(String baseKey) {
        return matchesSide(homeBaseKey, homeIdentity, baseKey)
                || matchesSide(awayBaseKey, awayIdentity, baseKey);
    }

    boolean homeIs(String baseKey) {
        return matchesSide(homeBaseKey, homeIdentity, baseKey);
    }

    boolean awayIs(String baseKey) {
        return matchesSide(awayBaseKey, awayIdentity, baseKey);
    }

    private static boolean matchesSide(String baseKey, String identity, String query) {
        if (query.isEmpty()) {
            return false;
        }
        return baseKey.equals(query) || baseKey.contains(query) || identity.contains(query);
    }

    /** Stable de-duplication key across overlapping datasets. */
    String dedupeKey() {
        return competition + "|" + season + "|" + homeIdentity + "|" + awayIdentity;
    }
}
