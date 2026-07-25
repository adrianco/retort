package com.brazilsoccer.mcp.graph;

import com.brazilsoccer.mcp.graph.TeamNameNormalizer.NormalizedName;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Name normalisation is the backbone of the whole graph: it decides which spellings collapse into
 * one club node and which namesakes stay apart.
 */
class TeamNameNormalizerTest {

    @ParameterizedTest(name = "[{index}] {0} -> {1}")
    @CsvSource({
            "Palmeiras-SP, palmeiras, SP",
            "'Palmeiras - SP', palmeiras, SP",
            "Palmeiras, palmeiras, SP",
            "Flamengo-RJ, flamengo, RJ",
            "'São Paulo', sao paulo, SP",
            "Sao Paulo-SP, sao paulo, SP",
            "'Grêmio - RS', gremio, RS",
            "'Vasco Da Gama RJ', vasco, RJ",
            "'Vasco da Gama-RJ', vasco, RJ",
            "Vasco, vasco, RJ",
            "'EC Bahia', bahia, BA",
            "'Sport Club do Recife', sport, PE",
            "'Sport Recife', sport, PE",
            "Sport-PE, sport, PE",
            "'Nautico Capibaribe', nautico, PE",
            "'Ceará Sporting Club', ceara, CE",
            "'Santa Cruz FC', santa cruz, PE",
            "'Clube Do Remo', remo, PA",
            "'Red Bull Bragantino-SP', bragantino, SP",
    })
    @DisplayName("spelling variants of the same club normalise to the same base name")
    void normalisesSpellingVariants(String raw, String expectedBase, String expectedState) {
        NormalizedName normalized = TeamNameNormalizer.normalize(raw, null);

        assertThat(normalized.base()).isEqualTo(expectedBase);
        assertThat(normalized.state()).isEqualTo(expectedState);
    }

    @ParameterizedTest(name = "[{index}] {0} -> {1}/{2}")
    @CsvSource({
            "'Atlético-MG', atletico, MG",
            "'Atletico Mineiro', atletico, MG",
            "'Atlético Mineiro - MG', atletico, MG",
            "'Athletico-PR', atletico, PR",
            "'Athletico Paranaense', atletico, PR",
            "'Atletico Paranaense - PR', atletico, PR",
            "Athletico, atletico, PR",
            "'Atlético-GO', atletico, GO",
            "'Atletico Goianiense', atletico, GO",
    })
    @DisplayName("the Atlético family keeps its state, because three clubs share the base name")
    void keepsStateForNamesakes(String raw, String expectedBase, String expectedState) {
        NormalizedName normalized = TeamNameNormalizer.normalize(raw, null);

        assertThat(normalized.base()).isEqualTo(expectedBase);
        assertThat(normalized.state()).isEqualTo(expectedState);
    }

    @Test
    @DisplayName("an explicit state always wins over the alias table")
    void explicitStateWinsOverAlias() {
        assertThat(TeamNameNormalizer.normalize("Santos AP", null).state()).isEqualTo("AP");
        assertThat(TeamNameNormalizer.normalize("Santos", null).state()).isEqualTo("SP");
        assertThat(TeamNameNormalizer.normalize("Santos - SP", null).state()).isEqualTo("SP");
    }

    @Test
    @DisplayName("a state column can supply the state when the name has none")
    void usesStateHint() {
        NormalizedName normalized = TeamNameNormalizer.normalize("Ponte Preta", "SP");

        assertThat(normalized.base()).isEqualTo("ponte preta");
        assertThat(normalized.state()).isEqualTo("SP");
    }

    @Test
    @DisplayName("parenthetical remarks are dropped, country and state names are kept")
    void handlesParentheses() {
        assertThat(TeamNameNormalizer.normalize("Nacional (URU)", null).state()).isEqualTo("URU");
        assertThat(TeamNameNormalizer.normalize("América FC (Minas Gerais)", null))
                .satisfies(name -> {
                    assertThat(name.base()).isEqualTo("america");
                    assertThat(name.state()).isEqualTo("MG");
                });
        assertThat(TeamNameNormalizer.normalize(
                "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", null))
                .satisfies(name -> {
                    assertThat(name.base()).isEqualTo("boavista");
                    assertThat(name.state()).isEqualTo("RJ");
                });
    }

    @Test
    @DisplayName("longer names that merely start with a known club stay separate")
    void doesNotOverMerge() {
        assertThat(TeamNameNormalizer.normalize("Gremio Novorizontino", null).base())
                .isEqualTo("gremio novorizontino");
        assertThat(TeamNameNormalizer.normalize("Grêmio Prudente", null).base()).isEqualTo("gremio prudente");
        assertThat(TeamNameNormalizer.normalize("Flamengo do Piauí - PI", null))
                .satisfies(name -> {
                    assertThat(name.base()).isEqualTo("flamengo piaui");
                    assertThat(name.state()).isEqualTo("PI");
                });
    }

    @Test
    @DisplayName("the display name keeps its accents but loses the state suffix")
    void producesReadableDisplayName() {
        assertThat(TeamNameNormalizer.normalize("Atlético - MG", null).display()).isEqualTo("Atlético");
        assertThat(TeamNameNormalizer.normalize("São Paulo-SP", null).display()).isEqualTo("São Paulo");
        assertThat(TeamNameNormalizer.preferredDisplayName("atletico", "PR")).isEqualTo("Athletico Paranaense");
    }
}
