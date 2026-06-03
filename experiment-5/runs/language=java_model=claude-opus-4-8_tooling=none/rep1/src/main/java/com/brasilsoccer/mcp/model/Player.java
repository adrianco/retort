/*
 * ============================================================================
 * Player - immutable record of a FIFA player entry
 * ============================================================================
 * Context:
 *   Subset of the columns from fifa_data.csv (18,207 players). Only the fields
 *   useful for the MCP query surface are retained: identity, nationality, club,
 *   position and the headline FIFA ratings. The full skill matrix is not needed
 *   for the supported queries and is therefore dropped at load time.
 *
 *   `nationalityKey` and `clubKey` are accent-stripped, lowercase forms used for
 *   case/accent-insensitive filtering (e.g. matching "sao paulo" against
 *   "São Paulo").
 * ============================================================================
 */
package com.brasilsoccer.mcp.model;

public record Player(
        int id,
        String name,
        String nameKey,
        int age,
        String nationality,
        String nationalityKey,
        int overall,
        int potential,
        String club,
        String clubKey,
        String position,
        String preferredFoot,
        String height,
        String weight) {
}
