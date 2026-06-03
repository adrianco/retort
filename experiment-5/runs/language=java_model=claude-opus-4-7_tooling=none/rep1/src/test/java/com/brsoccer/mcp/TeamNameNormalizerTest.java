package com.brsoccer.mcp;

import com.brsoccer.mcp.data.TeamNameNormalizer;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Team name normalization")
class TeamNameNormalizerTest {

    @Nested
    @DisplayName("Scenario: Normalize names with state suffix")
    class WithStateSuffix {
        @Test
        @DisplayName("Given 'Palmeiras-SP' When normalized Then equals 'palmeiras'")
        void stateSuffixWithHyphen() {
            assertEquals("palmeiras", TeamNameNormalizer.normalize("Palmeiras-SP"));
        }

        @Test
        @DisplayName("Given 'Flamengo-RJ' When normalized Then equals 'flamengo'")
        void flamengo() {
            assertEquals("flamengo", TeamNameNormalizer.normalize("Flamengo-RJ"));
        }

        @Test
        @DisplayName("Given 'América - MG' When normalized Then state suffix is stripped to 'america'")
        void americaMineiroAlias() {
            assertEquals("america", TeamNameNormalizer.normalize("América - MG"));
        }
    }

    @Nested
    @DisplayName("Scenario: Normalize names with diacritics")
    class Diacritics {
        @Test
        @DisplayName("Given 'São Paulo' Then accents stripped")
        void saoPaulo() {
            assertEquals("sao paulo", TeamNameNormalizer.normalize("São Paulo"));
        }

        @Test
        @DisplayName("Given 'Grêmio' Then accents stripped")
        void gremio() {
            assertEquals("gremio", TeamNameNormalizer.normalize("Grêmio"));
        }
    }

    @Nested
    @DisplayName("Scenario: Loose match")
    class Match {
        @Test
        @DisplayName("'flamengo' matches a query of 'Flamengo'")
        void matchExact() {
            assertTrue(TeamNameNormalizer.matches("flamengo", "Flamengo"));
        }

        @Test
        @DisplayName("'flamengo' matches a query containing accents")
        void matchAccents() {
            assertTrue(TeamNameNormalizer.matches("sao paulo", "São Paulo"));
        }
    }
}
