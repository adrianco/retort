package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.graph.TeamRegistry;
import com.brazilsoccer.mcp.model.Team;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * The classic Brazilian derbies ("clássicos"), used by the {@code find_derbies} tool.
 *
 * <p>Pairs are declared with human names and resolved through the {@link TeamRegistry} at
 * start-up, so the list does not depend on the internal club ids.
 */
public final class Rivalries {

    /** A derby between two resolved clubs. */
    public record Derby(String name, String teamAId, String teamBId) {
    }

    private static final String[][] DEFINITIONS = {
            {"Fla-Flu", "Flamengo", "Fluminense"},
            {"Clássico dos Milhões", "Flamengo", "Vasco da Gama"},
            {"Clássico da Rivalidade", "Flamengo", "Botafogo"},
            {"Clássico Vovô", "Botafogo", "Fluminense"},
            {"Clássico dos Gigantes", "Fluminense", "Vasco da Gama"},
            {"Clássico da Amizade", "Botafogo", "Vasco da Gama"},
            {"Derby Paulista", "Corinthians", "Palmeiras"},
            {"Majestoso", "Corinthians", "São Paulo"},
            {"Choque-Rei", "Palmeiras", "São Paulo"},
            {"Clássico Alvinegro", "Corinthians", "Santos"},
            {"San-São", "Santos", "São Paulo"},
            {"Clássico da Saudade", "Palmeiras", "Santos"},
            {"Gre-Nal", "Grêmio", "Internacional"},
            {"Clássico Mineiro", "Atlético Mineiro", "Cruzeiro"},
            {"Clássico das Multidões (MG)", "Atlético Mineiro", "América Mineiro"},
            {"Atletiba", "Athletico Paranaense", "Coritiba"},
            {"Ba-Vi", "Bahia", "Vitória"},
            {"Clássico dos Clássicos", "Sport Recife", "Náutico"},
            {"Clássico das Multidões (PE)", "Sport Recife", "Santa Cruz"},
            {"Clássico dos Fantasmas", "Náutico", "Santa Cruz"},
            {"Clássico-Rei", "Ceará", "Fortaleza"},
            {"Clássico Vovô (GO)", "Goiás", "Atlético Goianiense"},
    };

    private final List<Derby> derbies = new ArrayList<>();

    public Rivalries(TeamRegistry registry) {
        for (String[] definition : DEFINITIONS) {
            Optional<Team> a = registry.resolve(definition[1]);
            Optional<Team> b = registry.resolve(definition[2]);
            if (a.isPresent() && b.isPresent() && !a.get().id().equals(b.get().id())) {
                derbies.add(new Derby(definition[0], a.get().id(), b.get().id()));
            }
        }
    }

    public List<Derby> all() {
        return List.copyOf(derbies);
    }

    /** Derbies involving one club. */
    public List<Derby> involving(String teamId) {
        return derbies.stream().filter(d -> d.teamAId().equals(teamId) || d.teamBId().equals(teamId)).toList();
    }

    /** The derby name for a pair of clubs, if the pairing is a classic one. */
    public Optional<Derby> between(String teamAId, String teamBId) {
        return derbies.stream()
                .filter(d -> (d.teamAId().equals(teamAId) && d.teamBId().equals(teamBId))
                        || (d.teamAId().equals(teamBId) && d.teamBId().equals(teamAId)))
                .findFirst();
    }
}
