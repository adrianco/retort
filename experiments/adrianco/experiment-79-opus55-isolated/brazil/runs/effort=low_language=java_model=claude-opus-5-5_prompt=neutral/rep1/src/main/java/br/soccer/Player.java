package br.soccer;

import java.util.Map;

/** A row of the FIFA player database. */
public record Player(long id, String name, int age, String nationality, int overall, int potential,
                     String club, String position, String jersey, String height, String weight,
                     String value, String wage, String foot, Map<String, String> skills) {

    public String summary() {
        return name + " - Overall: " + overall + ", Position: " + (position.isEmpty() ? "n/a" : position)
                + ", Club: " + (club.isEmpty() ? "Free agent" : club);
    }
}
