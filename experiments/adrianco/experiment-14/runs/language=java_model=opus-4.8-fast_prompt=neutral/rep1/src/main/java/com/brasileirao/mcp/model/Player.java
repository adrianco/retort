/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : Player.java
 *  Purpose : Immutable value object for a FIFA-database player.
 *
 *  Context : Sourced from data/kaggle/fifa_data.csv (18,207 players). Only the
 *            columns useful for the required player queries are retained: name,
 *            age, nationality, overall/potential rating, club, position and a
 *            couple of physical attributes. The club name is also stored as a
 *            canonical key so "players at Flamengo" matches the same clubs used
 *            in the match data.
 *
 *  Used by : KnowledgeGraph, QueryService
 * ============================================================================
 */
package com.brasileirao.mcp.model;

/** A unified, immutable representation of one FIFA-database player. */
public final class Player {

    private final long id;
    private final String name;
    private final Integer age;
    private final String nationality;
    private final Integer overall;
    private final Integer potential;
    private final String club;
    private final String clubCanonical;
    private final String position;
    private final Integer jerseyNumber;
    private final String height;
    private final String weight;

    public Player(long id, String name, Integer age, String nationality, Integer overall,
                  Integer potential, String club, String position, Integer jerseyNumber,
                  String height, String weight) {
        this.id = id;
        this.name = name;
        this.age = age;
        this.nationality = nationality;
        this.overall = overall;
        this.potential = potential;
        this.club = club;
        this.clubCanonical = com.brasileirao.mcp.util.TeamNames.canonical(club);
        this.position = position;
        this.jerseyNumber = jerseyNumber;
        this.height = height;
        this.weight = weight;
    }

    public long id() {
        return id;
    }

    public String name() {
        return name;
    }

    public Integer age() {
        return age;
    }

    public String nationality() {
        return nationality;
    }

    public Integer overall() {
        return overall;
    }

    public Integer potential() {
        return potential;
    }

    public String club() {
        return club;
    }

    public String clubCanonical() {
        return clubCanonical;
    }

    public String position() {
        return position;
    }

    public Integer jerseyNumber() {
        return jerseyNumber;
    }

    public String height() {
        return height;
    }

    public String weight() {
        return weight;
    }

    /** A compact one-line description suitable for natural-language answers. */
    public String describe() {
        StringBuilder sb = new StringBuilder();
        sb.append(name);
        if (overall != null) {
            sb.append(" - Overall: ").append(overall);
        }
        if (position != null && !position.isBlank()) {
            sb.append(", Position: ").append(position);
        }
        if (club != null && !club.isBlank()) {
            sb.append(", Club: ").append(club);
        }
        if (nationality != null && !nationality.isBlank()) {
            sb.append(", Nationality: ").append(nationality);
        }
        return sb.toString();
    }
}
