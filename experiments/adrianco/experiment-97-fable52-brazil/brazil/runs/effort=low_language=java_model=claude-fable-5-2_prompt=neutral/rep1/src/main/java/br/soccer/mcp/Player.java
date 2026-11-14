package br.soccer.mcp;

import java.util.Map;

/** One row of the FIFA player database. */
final class Player {
    long id;
    String name, nationality, club, position, height, weight, value, wage, preferredFoot, jersey;
    int age, overall, potential;
    /** All raw columns, for attribute lookups (Finishing, Dribbling, ...). */
    Map<String, String> raw;
    /** Canonical team key of the club when it is a club known from the match data, else null. */
    String clubTeamKey;
}
