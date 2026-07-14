package com.soccer.mcp;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Feature: Team Name Normalization")
class TeamNameNormalizerTest {

    @Nested
    @DisplayName("Scenario: Strip state suffixes")
    class StateSuffixes {
        @Test
        @DisplayName("Given a team name with state suffix, it should strip the suffix")
        void stripsSuffix() {
            assertEquals("palmeiras", TeamNameNormalizer.normalize("Palmeiras-SP"));
            assertEquals("flamengo", TeamNameNormalizer.normalize("Flamengo-RJ"));
            assertEquals("gremio", TeamNameNormalizer.normalize("Grêmio-RS"));
            assertEquals("sport", TeamNameNormalizer.normalize("Sport-PE"));
        }
    }

    @Nested
    @DisplayName("Scenario: Resolve known aliases")
    class Aliases {
        @Test
        @DisplayName("Given a full club name, it should resolve to the common short name")
        void resolvesAliases() {
            assertEquals("corinthians", TeamNameNormalizer.normalize("Sport Club Corinthians Paulista"));
            assertEquals("vasco", TeamNameNormalizer.normalize("Vasco da Gama"));
            assertEquals("sao paulo", TeamNameNormalizer.normalize("São Paulo FC"));
            assertEquals("gremio", TeamNameNormalizer.normalize("Grêmio"));
        }
    }

    @Nested
    @DisplayName("Scenario: Match team names across variations")
    class Matching {
        @Test
        @DisplayName("Given two variations of the same team, matches should return true")
        void matchesVariations() {
            assertTrue(TeamNameNormalizer.matches("Palmeiras-SP", "Palmeiras"));
            assertTrue(TeamNameNormalizer.matches("Flamengo", "Flamengo-RJ"));
            assertTrue(TeamNameNormalizer.matches("São Paulo FC", "Sao Paulo"));
            assertTrue(TeamNameNormalizer.matches("Grêmio-RS", "Gremio"));
            assertTrue(TeamNameNormalizer.matches("Vasco da Gama", "Vasco"));
        }

        @Test
        @DisplayName("Given two different teams, matches should return false")
        void doesNotMatchDifferentTeams() {
            assertFalse(TeamNameNormalizer.matches("Palmeiras", "Flamengo"));
            assertFalse(TeamNameNormalizer.matches("Santos", "São Paulo"));
        }

        @Test
        @DisplayName("Given null or empty names, matches should return false")
        void handlesNullAndEmpty() {
            assertFalse(TeamNameNormalizer.matches(null, "Palmeiras"));
            assertFalse(TeamNameNormalizer.matches("Palmeiras", null));
            assertFalse(TeamNameNormalizer.matches(null, null));
        }
    }

    @Nested
    @DisplayName("Scenario: Normalize edge cases")
    class EdgeCases {
        @Test
        @DisplayName("Given a name without suffix, it should lowercase and trim")
        void noSuffix() {
            assertEquals("palmeiras", TeamNameNormalizer.normalize("Palmeiras"));
            assertEquals("flamengo", TeamNameNormalizer.normalize("  Flamengo  "));
        }

        @Test
        @DisplayName("Given null or blank, it should return empty string")
        void nullOrBlank() {
            assertEquals("", TeamNameNormalizer.normalize(null));
            assertEquals("", TeamNameNormalizer.normalize(""));
            assertEquals("", TeamNameNormalizer.normalize("   "));
        }
    }
}
