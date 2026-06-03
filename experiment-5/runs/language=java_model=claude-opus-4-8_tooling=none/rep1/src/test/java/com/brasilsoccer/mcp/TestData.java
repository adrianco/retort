/*
 * ============================================================================
 * TestData - shared, lazily-loaded KnowledgeBase for the test suite
 * ============================================================================
 * Context:
 *   Loading the six CSV datasets takes a moment, so the whole test suite shares
 *   a single KnowledgeBase instance built once from the real data under
 *   data/kaggle (relative to the project root, which is the working directory
 *   during a Maven test run).
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;

import java.nio.file.Path;

public final class TestData {

    private static KnowledgeBase instance;

    private TestData() {
    }

    public static synchronized KnowledgeBase kb() {
        if (instance == null) {
            try {
                instance = KnowledgeBase.load(Path.of("data", "kaggle"));
            } catch (Exception e) {
                throw new RuntimeException("Failed to load test data from data/kaggle", e);
            }
        }
        return instance;
    }
}
