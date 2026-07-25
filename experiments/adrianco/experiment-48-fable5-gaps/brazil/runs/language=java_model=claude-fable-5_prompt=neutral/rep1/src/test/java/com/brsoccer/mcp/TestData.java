package com.brsoccer.mcp;

import com.brsoccer.mcp.data.DataStore;
import com.brsoccer.mcp.query.QueryService;
import com.brsoccer.mcp.tools.McpTools;

import java.nio.file.Path;

/** Loads the datasets once for the whole test run. */
public final class TestData {

    private static DataStore store;
    private static QueryService query;
    private static McpTools tools;

    public static synchronized DataStore store() {
        if (store == null) {
            try {
                DataStore s = new DataStore();
                s.loadAll(Path.of("data/kaggle"));
                store = s;
                query = new QueryService(s);
                tools = new McpTools(query);
            } catch (Exception e) {
                throw new RuntimeException("Failed to load test data", e);
            }
        }
        return store;
    }

    public static QueryService query() {
        store();
        return query;
    }

    public static McpTools tools() {
        store();
        return tools;
    }

    private TestData() {}
}
