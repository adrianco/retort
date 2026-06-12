package com.brazilsoccer.mcp;

import java.util.Locale;

/** The competitions represented across the datasets. */
public enum Competition {
    SERIE_A("serie_a", "Brasileirão Série A"),
    SERIE_B("serie_b", "Brasileirão Série B"),
    SERIE_C("serie_c", "Brasileirão Série C"),
    COPA_DO_BRASIL("copa_do_brasil", "Copa do Brasil"),
    LIBERTADORES("libertadores", "Copa Libertadores");

    private final String key;
    private final String displayName;

    Competition(String key, String displayName) {
        this.key = key;
        this.displayName = displayName;
    }

    public String key() {
        return key;
    }

    public String displayName() {
        return displayName;
    }

    /** Resolves a user-supplied competition string, tolerating spelling variants. */
    public static Competition resolve(String input) {
        if (input == null) {
            return null;
        }
        String n = TeamNames.normalize(input).replace("_", " ").trim();
        switch (n) {
            case "serie a":
            case "seriea":
            case "brasileirao":
            case "brasileiro":
            case "campeonato brasileiro":
            case "brazilian serie a":
                return SERIE_A;
            case "serie b":
                return SERIE_B;
            case "serie c":
                return SERIE_C;
            case "copa do brasil":
            case "copadobrasil":
            case "cup":
            case "brazilian cup":
                return COPA_DO_BRASIL;
            case "libertadores":
            case "copa libertadores":
                return LIBERTADORES;
            default:
                return null;
        }
    }

    /** Maps a tournament label from the extended dataset. */
    static Competition fromTournamentLabel(String label) {
        if (label == null) {
            return null;
        }
        String n = label.toLowerCase(Locale.ROOT).trim();
        if (n.contains("serie a")) return SERIE_A;
        if (n.contains("serie b")) return SERIE_B;
        if (n.contains("serie c")) return SERIE_C;
        if (n.contains("copa do brasil")) return COPA_DO_BRASIL;
        if (n.contains("libertadores")) return LIBERTADORES;
        return null;
    }
}
