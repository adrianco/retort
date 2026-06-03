package com.brsoccer.mcp;

import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Data loading")
class DataLoadingTest {

    @Test
    @DisplayName("Given the data directory When the knowledge base loads Then all 6 CSV files are loadable and queryable")
    void allCsvsLoad() {
        SoccerKnowledgeBase kb = TestData.get();
        assertNotNull(kb.matches().all());
        assertNotNull(kb.players().all());
        // 4180 + 1337 + 1255 + 10296 + 6886 = 23,954 matches expected
        assertTrue(kb.matches().all().size() > 20_000,
            "expected >20k matches, got " + kb.matches().all().size());
        assertTrue(kb.players().all().size() > 15_000,
            "expected >15k players, got " + kb.players().all().size());
    }
}
