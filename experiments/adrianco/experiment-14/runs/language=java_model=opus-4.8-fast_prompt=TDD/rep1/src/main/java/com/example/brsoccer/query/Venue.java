/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    Venue.java
 * Purpose: Restricts a team-centric query to home matches, away matches or
 *          both, so callers can ask e.g. "Corinthians' home record in 2022".
 * Part of: query package.
 * ============================================================================
 */
package com.example.brsoccer.query;

/** Which side of the fixture a team query is restricted to. */
public enum Venue {
    HOME, AWAY, ANY
}
