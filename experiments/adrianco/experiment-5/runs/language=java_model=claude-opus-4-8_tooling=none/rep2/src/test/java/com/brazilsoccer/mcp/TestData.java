/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    test/TestData.java
 * Purpose: Shared test fixture that loads the real Kaggle datasets once and
 *          caches them for all integration-style tests, so the suite exercises
 *          the actual data the spec ships with (rather than synthetic stubs).
 * ===========================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.SoccerData;
import com.brazilsoccer.mcp.query.SoccerQueries;

import java.nio.file.Path;

public final class TestData {

    private static SoccerData data;

    private TestData() {
    }

    public static synchronized SoccerData data() {
        if (data == null) {
            data = SoccerData.load(Path.of("data"));
        }
        return data;
    }

    public static SoccerQueries queries() {
        return new SoccerQueries(data());
    }
}
