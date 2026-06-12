package com.braziliansoccer.mcp.service;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TeamNameNormalizerTest {
    private final TeamNameNormalizer normalizer = new TeamNameNormalizer();

    @Test void testNormalizeRemovesStateSuffix() { assertEquals("Palmeiras", normalizer.normalize("Palmeiras-SP")); }
    @Test void testNormalizeNoSuffix() { assertEquals("Flamengo", normalizer.normalize("Flamengo")); }
    @Test void testMatchesCaseInsensitive() { assertTrue(normalizer.matches("Palmeiras-SP", "palmeiras")); }
    @Test void testMatchesReturnsFalseForDifferentTeam() { assertFalse(normalizer.matches("Palmeiras-SP", "Flamengo")); }
}
