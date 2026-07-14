/*
 * ============================================================================
 * TestData.java
 * ============================================================================
 * Context:
 *   Shared, lazily-initialized DataStore for the test suite. Loading the full
 *   corpus (~42k rows) takes a moment, so it is parsed once and reused across
 *   all test classes rather than per-test. Maven runs tests from the project
 *   root, so DataStore auto-detects ./data/kaggle.
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.DataStore;

/** Provides a single cached DataStore instance for all tests. */
public final class TestData {

    private static DataStore store;

    private TestData() {}

    public static synchronized DataStore store() {
        if (store == null) {
            try {
                store = DataStore.load();
            } catch (Exception e) {
                throw new RuntimeException("Failed to load test data from data/kaggle", e);
            }
        }
        return store;
    }
}
