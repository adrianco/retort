package com.brazilsoccer.mcp.model;

import java.util.Locale;
import java.util.Optional;

/**
 * Competitions covered by the bundled datasets.
 *
 * <p>Each constant carries a stable machine id (used as MCP tool argument), a human readable
 * display name and a flag telling whether the competition is a round-robin league (points table
 * can be computed) or a knockout style tournament.
 */
public enum Competition {

    SERIE_A("serie_a", "Brasileirão Série A", true),
    SERIE_B("serie_b", "Brasileirão Série B", true),
    SERIE_C("serie_c", "Brasileirão Série C", true),
    COPA_DO_BRASIL("copa_do_brasil", "Copa do Brasil", false),
    LIBERTADORES("libertadores", "Copa Libertadores", false);

    private final String id;
    private final String displayName;
    private final boolean league;

    Competition(String id, String displayName, boolean league) {
        this.id = id;
        this.displayName = displayName;
        this.league = league;
    }

    public String id() {
        return id;
    }

    public String displayName() {
        return displayName;
    }

    /** True when the competition is played as a points-based round robin. */
    public boolean isLeague() {
        return league;
    }

    /**
     * Lenient parsing of user/LLM supplied competition names. Accepts ids ("serie_a"), display
     * names ("Brasileirão Série A"), and common aliases in English and Portuguese.
     */
    public static Optional<Competition> parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        String key = raw.toLowerCase(Locale.ROOT)
                .replace('ã', 'a').replace('á', 'a').replace('â', 'a')
                .replace('é', 'e').replace('ê', 'e')
                .replace('í', 'i').replace('ó', 'o').replace('ô', 'o')
                .replace('ú', 'u').replace('ç', 'c')
                .replaceAll("[^a-z0-9]+", " ")
                .trim();
        return switch (key) {
            case "serie a", "seriea", "a", "brasileirao", "brasileirao serie a", "campeonato brasileiro",
                 "brasileiro", "brazilian league", "brasileirao a" -> Optional.of(SERIE_A);
            case "serie b", "serieb", "b", "brasileirao serie b", "segunda divisao" -> Optional.of(SERIE_B);
            case "serie c", "seriec", "c", "brasileirao serie c" -> Optional.of(SERIE_C);
            case "copa do brasil", "copadobrasil", "cup", "brazilian cup", "copa brasil", "copa" ->
                    Optional.of(COPA_DO_BRASIL);
            case "libertadores", "copa libertadores", "conmebol libertadores", "copa libertadores da america" ->
                    Optional.of(LIBERTADORES);
            default -> Optional.empty();
        };
    }
}
