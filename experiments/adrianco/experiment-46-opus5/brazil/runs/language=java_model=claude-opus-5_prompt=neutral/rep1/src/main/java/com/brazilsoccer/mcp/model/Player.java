package com.brazilsoccer.mcp.model;

import java.util.Map;

/**
 * A player node of the knowledge graph, loaded from {@code fifa_data.csv}.
 *
 * <p>{@code clubTeamId} links the player to a {@link Team} node using the same canonical id space
 * as the match data, which is what makes cross-file queries (player + match statistics) possible.
 * It is {@code null} for free agents.
 */
public record Player(
        int id,
        String name,
        Integer age,
        String nationality,
        Integer overall,
        Integer potential,
        String club,
        String clubTeamId,
        String position,
        String jerseyNumber,
        String height,
        String weight,
        String value,
        String wage,
        String preferredFoot,
        Map<String, Integer> skills) {

    public boolean hasClub() {
        return club != null && !club.isBlank();
    }

    /** Broad position group used by the {@code position} filter of the player search tool. */
    public PositionGroup positionGroup() {
        if (position == null || position.isBlank()) {
            return PositionGroup.UNKNOWN;
        }
        return switch (position) {
            case "GK" -> PositionGroup.GOALKEEPER;
            case "CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB" -> PositionGroup.DEFENDER;
            case "CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM" ->
                    PositionGroup.MIDFIELDER;
            case "ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW" -> PositionGroup.FORWARD;
            default -> PositionGroup.UNKNOWN;
        };
    }

    public enum PositionGroup {
        GOALKEEPER, DEFENDER, MIDFIELDER, FORWARD, UNKNOWN;

        /** Accepts "gk", "goalkeeper", "defender", "df", "midfielder", "forward", "attacker"... */
        public static PositionGroup parse(String raw) {
            if (raw == null) {
                return UNKNOWN;
            }
            return switch (raw.trim().toLowerCase(java.util.Locale.ROOT)) {
                case "gk", "goalkeeper", "goalie", "keeper" -> GOALKEEPER;
                case "df", "def", "defender", "defenders", "defence", "defense", "zagueiro" -> DEFENDER;
                case "mf", "mid", "midfield", "midfielder", "midfielders", "meia" -> MIDFIELDER;
                case "fw", "att", "attacker", "forward", "forwards", "striker", "atacante" -> FORWARD;
                default -> UNKNOWN;
            };
        }
    }
}
