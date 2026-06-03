/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    model/Player.java
 * Purpose: Immutable domain model for a FIFA-database player row. Holds the
 *          identity, rating and club attributes used by the player-oriented
 *          MCP query tools (search by name, nationality, club; rank by rating).
 * ===========================================================================
 */
package com.brazilsoccer.mcp.model;

/**
 * A player from the FIFA dataset. Numeric fields may be null when a source row
 * lacks a value. {@code clubKey} / {@code nationalityKey} are normalized lower
 * case, accent-free keys used for tolerant matching.
 */
public record Player(
        long id,
        String name,
        Integer age,
        String nationality,
        String nationalityKey,
        Integer overall,
        Integer potential,
        String club,
        String clubKey,
        String position,
        String jerseyNumber,
        String height,
        String weight) {
}
