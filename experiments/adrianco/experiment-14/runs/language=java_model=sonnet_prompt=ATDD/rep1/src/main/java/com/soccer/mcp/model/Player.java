package com.soccer.mcp.model;

public class Player {
    private final String name;
    private final int age;
    private final String nationality;
    private final int overall;
    private final int potential;
    private final String club;
    private final String position;

    public Player(String name, int age, String nationality, int overall, int potential,
                  String club, String position) {
        this.name = name;
        this.age = age;
        this.nationality = nationality;
        this.overall = overall;
        this.potential = potential;
        this.club = club;
        this.position = position;
    }

    public String getName() { return name; }
    public int getAge() { return age; }
    public String getNationality() { return nationality; }
    public int getOverall() { return overall; }
    public int getPotential() { return potential; }
    public String getClub() { return club; }
    public String getPosition() { return position; }

    @Override
    public String toString() {
        return String.format("%s (%s, %s) - Overall: %d, Potential: %d, Club: %s",
                name, position, nationality, overall, potential, club);
    }
}
