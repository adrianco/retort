/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    Player.java
 * Purpose: Immutable record of a footballer drawn from the FIFA player dataset.
 *          Provides accent/case-insensitive helpers for name, club and
 *          nationality matching used by the player query layer.
 * Part of: model package (core domain entity).
 * ============================================================================
 */
package com.example.brsoccer.model;

import java.text.Normalizer;

/** A FIFA-database player. */
public record Player(
        int id,
        String name,
        Integer age,
        String nationality,
        Integer overall,
        Integer potential,
        String club,
        String position,
        Integer jerseyNumber) {

    public boolean isBrazilian() {
        return nationality != null && nationality.equalsIgnoreCase("Brazil");
    }

    public boolean nameMatches(String query) {
        return fold(name).contains(fold(query));
    }

    public boolean playsFor(String clubQuery) {
        return club != null && fold(club).contains(fold(clubQuery));
    }

    public boolean hasNationality(String query) {
        return nationality != null && fold(nationality).contains(fold(query));
    }

    private static String fold(String s) {
        if (s == null) {
            return "";
        }
        String n = Normalizer.normalize(s, Normalizer.Form.NFD)
                .replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
        return n.toLowerCase().trim();
    }
}
