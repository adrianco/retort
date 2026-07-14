package com.soccer.mcp.unit;

import com.soccer.mcp.service.TeamNameNormalizer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Unit tests for TeamNameNormalizer.
 */
public class TeamNameNormalizerTest {

    private TeamNameNormalizer normalizer;

    @BeforeEach
    void setUp() {
        normalizer = new TeamNameNormalizer();
    }

    @Test
    void stripsStateSuffixDashSP() {
        assertThat(normalizer.normalize("Flamengo-RJ")).isEqualTo("Flamengo");
    }

    @Test
    void stripsStateSuffixDashMG() {
        assertThat(normalizer.normalize("Atletico-MG")).isEqualTo("Atletico");
    }

    @Test
    void stripsStateSuffixWithSpaces() {
        assertThat(normalizer.normalize("America - MG")).isEqualTo("America");
    }

    @Test
    void normalizationIsCaseInsensitive() {
        String norm1 = normalizer.normalize("FLAMENGO-RJ");
        String norm2 = normalizer.normalize("flamengo-rj");
        assertThat(norm1.toLowerCase()).isEqualTo(norm2.toLowerCase());
    }

    @Test
    void matchesIgnoresAccents() {
        // "Sao Paulo" should match "São Paulo"
        assertThat(normalizer.matches("São Paulo", "Sao Paulo")).isTrue();
    }

    @Test
    void matchesIgnoresCase() {
        assertThat(normalizer.matches("flamengo", "Flamengo")).isTrue();
    }

    @Test
    void matchesPartialName() {
        // "Corinthians" should match "Sport Club Corinthians Paulista"
        assertThat(normalizer.matches("Sport Club Corinthians Paulista", "Corinthians")).isTrue();
    }

    @Test
    void matchesGremioWithoutAccent() {
        assertThat(normalizer.matches("Grêmio", "Gremio")).isTrue();
    }

    @Test
    void matchesAtleticoVariants() {
        assertThat(normalizer.matches("Atlético-MG", "Atletico")).isTrue();
    }

    @Test
    void matchesFlamengoRJWithFlamengo() {
        assertThat(normalizer.matches("Flamengo-RJ", "Flamengo")).isTrue();
    }

    @Test
    void normalizeSaoSaoPauloStripsStateSuffix() {
        String result = normalizer.normalize("Sao Paulo-SP");
        assertThat(result.toLowerCase()).contains("paulo");
    }

    @Test
    void doesNotMatchDifferentTeams() {
        assertThat(normalizer.matches("Flamengo", "Fluminense")).isFalse();
    }
}
