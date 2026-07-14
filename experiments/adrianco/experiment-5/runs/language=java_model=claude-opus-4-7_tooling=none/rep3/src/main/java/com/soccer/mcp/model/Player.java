package com.soccer.mcp.model;

public final class Player {
    private final String id;
    private final String name;
    private final Integer age;
    private final String nationality;
    private final Integer overall;
    private final Integer potential;
    private final String club;
    private final String position;
    private final String jerseyNumber;
    private final String height;
    private final String weight;
    private final String preferredFoot;

    public Player(String id, String name, Integer age, String nationality,
                  Integer overall, Integer potential, String club, String position,
                  String jerseyNumber, String height, String weight, String preferredFoot) {
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
        this.preferredFoot = preferredFoot;
    }

    public String id() { return id; }
    public String name() { return name; }
    public Integer age() { return age; }
    public String nationality() { return nationality; }
    public Integer overall() { return overall; }
    public Integer potential() { return potential; }
    public String club() { return club; }
    public String position() { return position; }
    public String jerseyNumber() { return jerseyNumber; }
    public String height() { return height; }
    public String weight() { return weight; }
    public String preferredFoot() { return preferredFoot; }
}
