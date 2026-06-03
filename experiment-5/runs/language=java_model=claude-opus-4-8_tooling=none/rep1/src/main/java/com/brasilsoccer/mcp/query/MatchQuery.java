/*
 * ============================================================================
 * MatchQuery - filter criteria for searching matches
 * ============================================================================
 * Context:
 *   A small builder describing how to filter the match corpus. All fields are
 *   optional; an empty query matches everything. Team strings are accepted as
 *   raw user input and normalised internally by the KnowledgeBase. `venue`
 *   restricts a single-team search to home or away games.
 * ============================================================================
 */
package com.brasilsoccer.mcp.query;

import java.time.LocalDate;

public final class MatchQuery {

    public enum Venue {ANY, HOME, AWAY}

    public String team;          // either side (or, with team2, one of the pair)
    public String team2;         // when set, restrict to matches between team & team2
    public String competition;   // substring match on canonical competition name
    public Integer season;
    public LocalDate startDate;
    public LocalDate endDate;
    public Venue venue = Venue.ANY;
    public int limit = 50;

    public MatchQuery team(String t) {
        this.team = t;
        return this;
    }

    public MatchQuery team2(String t) {
        this.team2 = t;
        return this;
    }

    public MatchQuery competition(String c) {
        this.competition = c;
        return this;
    }

    public MatchQuery season(Integer s) {
        this.season = s;
        return this;
    }

    public MatchQuery startDate(LocalDate d) {
        this.startDate = d;
        return this;
    }

    public MatchQuery endDate(LocalDate d) {
        this.endDate = d;
        return this;
    }

    public MatchQuery venue(Venue v) {
        this.venue = v == null ? Venue.ANY : v;
        return this;
    }

    public MatchQuery limit(int l) {
        this.limit = l;
        return this;
    }
}
