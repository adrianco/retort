package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Feature: Team name normalisation")
class TeamNamesTest {
    private final TeamNames t = TestData.STORE.teams;

    @Test
    @DisplayName("Scenario: state suffixes and accents do not matter")
    void suffixVariants() {
        String k = t.canonical("Palmeiras");
        assertEquals(k, t.canonical("Palmeiras-SP"));
        assertEquals(k, t.canonical("Palmeiras - SP"));
        assertEquals(k, t.canonical("palmeiras"));
        assertEquals(t.canonical("São Paulo"), t.canonical("Sao Paulo-SP"));
        assertEquals(t.canonical("São Paulo"), t.canonical("São Paulo FC"));
        assertEquals(t.canonical("Grêmio"), t.canonical("Gremio RS"));
        assertEquals(t.canonical("Flamengo"), t.canonical("Flamengo-RJ"));
    }

    @Test
    @DisplayName("Scenario: full and alternative club names map to the same club")
    void aliases() {
        assertEquals(t.canonical("Corinthians"), t.canonical("Sport Club Corinthians Paulista"));
        assertEquals(t.canonical("Vasco"), t.canonical("Vasco da Gama-RJ"));
        assertEquals(t.canonical("Atlético-MG"), t.canonical("Atletico Mineiro"));
        assertEquals(t.canonical("Atlético-MG"), t.canonical("Atlético - MG"));
        assertEquals(t.canonical("Athletico-PR"), t.canonical("Atlético Paranaense"));
        assertEquals(t.canonical("Athletico-PR"), t.canonical("Athletico"));
        assertEquals(t.canonical("Sport-PE"), t.canonical("Sport Recife"));
        assertEquals(t.canonical("Red Bull Bragantino-SP"), t.canonical("Bragantino"));
        assertEquals(t.canonical("América-MG"), t.canonical("America MG"));
    }

    @Test
    @DisplayName("Scenario: different clubs sharing a name stay distinct")
    void distinctClubs() {
        assertNotEquals(t.canonical("Atlético-MG"), t.canonical("Atlético-GO"));
        assertNotEquals(t.canonical("Atlético-MG"), t.canonical("Athletico-PR"));
        assertNotEquals(t.canonical("Flamengo - RJ"), t.canonical("Flamengo - PI"));
        assertNotEquals(t.canonical("Botafogo"), t.canonical("Botafogo PB"));
        assertNotEquals(t.canonical("América-MG"), t.canonical("América-RN"));
        assertNotEquals(t.canonical("Nacional (URU)"), t.canonical("Nacional (PAR)"));
        assertEquals(t.canonical("Nacional (URU)"), t.canonical("Nacional-URU"));
    }

    @Test
    @DisplayName("Scenario: user queries resolve to known teams")
    void resolve() {
        assertEquals(List.of("flamengo"), t.resolve("Flamengo"));
        assertEquals(List.of("flamengo"), t.resolve("  FLAMENGO-rj "));
        assertTrue(t.resolve("Atlético").size() > 1, "ambiguous name returns several candidates");
        assertTrue(t.resolve("Zzzzz Unknown FC").isEmpty());
        assertEquals("Athletico-PR", t.display(t.canonical("Atletico-PR")));
        assertEquals("Atlético-MG", t.display(t.canonical("Atletico Mineiro")));
    }
}
