package com.brazilsoccer.mcp;

/** A player from the FIFA dataset. */
public final class Player {

    final String name;
    final int age;
    final String nationality;
    final int overall;
    final int potential;
    final String club;
    final String position;
    final String jerseyNumber;

    final String nameKey;        // normalized for searching
    final String nationalityKey;
    final String clubKey;

    Player(String name, int age, String nationality, int overall, int potential,
           String club, String position, String jerseyNumber) {
        this.name = name;
        this.age = age;
        this.nationality = nationality;
        this.overall = overall;
        this.potential = potential;
        this.club = club;
        this.position = position;
        this.jerseyNumber = jerseyNumber;
        this.nameKey = TeamNames.normalize(name);
        this.nationalityKey = TeamNames.normalize(nationality);
        this.clubKey = TeamNames.normalize(club);
    }
}
