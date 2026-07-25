package com.brsoccer.mcp.model;

import java.util.Map;

/** A player from the FIFA dataset. */
public class Player {
    public final String id;
    public final String name;
    public final Integer age;
    public final String nationality;
    public final Integer overall;
    public final Integer potential;
    public final String club;
    public final String position;
    public final String jerseyNumber;
    public final String height;
    public final String weight;
    public final String value;
    public final String wage;
    public final String preferredFoot;
    /** Selected skill attributes (Finishing, Dribbling, ...), insertion-ordered. */
    public final Map<String, Integer> attributes;

    public Player(String id, String name, Integer age, String nationality, Integer overall,
                  Integer potential, String club, String position, String jerseyNumber,
                  String height, String weight, String value, String wage, String preferredFoot,
                  Map<String, Integer> attributes) {
        this.id = id;
        this.name = name;
        this.age = age;
        this.nationality = nationality;
        this.overall = overall;
        this.potential = potential;
        this.club = club;
        this.position = position;
        this.jerseyNumber = jerseyNumber;
        this.height = height;
        this.weight = weight;
        this.value = value;
        this.wage = wage;
        this.preferredFoot = preferredFoot;
        this.attributes = attributes;
    }
}
