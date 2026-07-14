package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.TeamNormalizer;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class TeamNormalizerTest {

    @Test
    void testNormalizeStatePrefix() {
        assertEquals("Palmeiras", TeamNormalizer.normalize("Palmeiras-SP"));
        assertEquals("Flamengo", TeamNormalizer.normalize("Flamengo-RJ"));
        assertEquals("Corinthians", TeamNormalizer.normalize("Corinthians-SP"));
    }

    @Test
    void testNormalizeAlreadyClean() {
        assertEquals("Flamengo", TeamNormalizer.normalize("Flamengo"));
        assertEquals("Palmeiras", TeamNormalizer.normalize("Palmeiras"));
    }

    @Test
    void testNormalizeSaoPaulo() {
        assertEquals("São Paulo", TeamNormalizer.normalize("São Paulo-SP"));
        assertEquals("São Paulo", TeamNormalizer.normalize("Sao Paulo-SP"));
        assertEquals("São Paulo", TeamNormalizer.normalize("Sao Paulo"));
    }

    @Test
    void testNormalizeGremio() {
        assertEquals("Grêmio", TeamNormalizer.normalize("Grêmio-RS"));
        assertEquals("Grêmio", TeamNormalizer.normalize("Gremio-RS"));
        assertEquals("Grêmio", TeamNormalizer.normalize("Gremio"));
    }

    @Test
    void testNormalizeAtleticoMineiro() {
        assertEquals("Atlético Mineiro", TeamNormalizer.normalize("Atletico-MG"));
        assertEquals("Atlético Mineiro", TeamNormalizer.normalize("Atlético-MG"));
        assertEquals("Atlético Mineiro", TeamNormalizer.normalize("Atlético Mineiro-MG"));
    }

    @Test
    void testNormalizeAthleticoParanaense() {
        assertEquals("Athletico Paranaense", TeamNormalizer.normalize("Athletico-PR"));
        assertEquals("Athletico Paranaense", TeamNormalizer.normalize("Atletico Paranaense-PR"));
    }

    @Test
    void testNormalizeInternacional() {
        assertEquals("Internacional", TeamNormalizer.normalize("Internacional-RS"));
        assertEquals("Internacional", TeamNormalizer.normalize("Inter-RS"));
    }

    @Test
    void testMatchesCaseInsensitive() {
        assertTrue(TeamNormalizer.matches("Flamengo-RJ", "Flamengo"));
        assertTrue(TeamNormalizer.matches("Palmeiras-SP", "palmeiras"));
        assertTrue(TeamNormalizer.matches("Flamengo", "FLAMENGO"));
    }

    @Test
    void testMatchesPartial() {
        assertTrue(TeamNormalizer.matches("Sport Club Corinthians Paulista", "Corinthians"));
        assertTrue(TeamNormalizer.matches("Corinthians", "Corinthians"));
    }

    @Test
    void testMatchesNoFalsePositives() {
        assertFalse(TeamNormalizer.matches("Flamengo", "Santos"));
        assertFalse(TeamNormalizer.matches("Palmeiras", "Corinthians"));
    }

    @Test
    void testNormalizeNull() {
        assertEquals("", TeamNormalizer.normalize(null));
    }

    @Test
    void testNormalizeWithSpacesAndDash() {
        // Copa format "América - MG"
        String result = TeamNormalizer.normalize("América - MG");
        assertNotNull(result);
        assertFalse(result.isEmpty());
    }
}
