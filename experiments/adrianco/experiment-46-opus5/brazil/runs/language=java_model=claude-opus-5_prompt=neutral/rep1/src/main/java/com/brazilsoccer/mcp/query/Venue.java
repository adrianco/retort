package com.brazilsoccer.mcp.query;

import java.util.Locale;

/** Home / away filter shared by the team oriented queries. */
public enum Venue {
    ALL, HOME, AWAY;

    public static Venue parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return ALL;
        }
        return switch (raw.trim().toLowerCase(Locale.ROOT)) {
            case "home", "casa", "mandante" -> HOME;
            case "away", "fora", "visitante" -> AWAY;
            default -> ALL;
        };
    }

    public String label() {
        return switch (this) {
            case ALL -> "overall";
            case HOME -> "home";
            case AWAY -> "away";
        };
    }
}
