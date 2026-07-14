/*
 * ============================================================================
 * Player.java
 * ============================================================================
 * Context:
 *   Immutable representation of a single player row from the FIFA player
 *   database (data/kaggle/fifa_data.csv). Only the fields useful for the MCP
 *   query surface are kept; the raw CSV has ~90 columns of skill ratings that
 *   we do not need to model individually.
 *
 *   clubKey / nationalityKey hold accent-insensitive match keys (see
 *   TeamNames.key) so that "Sao Paulo" matches "São Paulo" etc.
 * ============================================================================
 */
package com.brazilsoccer.mcp.model;

/** Immutable FIFA player record. */
public final class Player {

    private final int id;
    private final String name;
    private final Integer age;
    private final String nationality;
    private final String nationalityKey;
    private final Integer overall;
    private final Integer potential;
    private final String club;
    private final String clubKey;
    private final String position;

    public Player(int id, String name, Integer age, String nationality, String nationalityKey,
                  Integer overall, Integer potential, String club, String clubKey, String position) {
        this.id = id;
        this.name = name;
        this.age = age;
        this.nationality = nationality;
        this.nationalityKey = nationalityKey;
        this.overall = overall;
        this.potential = potential;
        this.club = club;
        this.clubKey = clubKey;
        this.position = position;
    }

    public int id() { return id; }
    public String name() { return name; }
    public Integer age() { return age; }
    public String nationality() { return nationality; }
    public String nationalityKey() { return nationalityKey; }
    public Integer overall() { return overall; }
    public Integer potential() { return potential; }
    public String club() { return club; }
    public String clubKey() { return clubKey; }
    public String position() { return position; }

    /** Human-readable one-line summary used in tool responses. */
    public String describe() {
        StringBuilder sb = new StringBuilder();
        sb.append(name);
        if (overall != null) sb.append(" - Overall: ").append(overall);
        if (position != null && !position.isBlank()) sb.append(", Position: ").append(position);
        if (club != null && !club.isBlank()) sb.append(", Club: ").append(club);
        return sb.toString();
    }
}
