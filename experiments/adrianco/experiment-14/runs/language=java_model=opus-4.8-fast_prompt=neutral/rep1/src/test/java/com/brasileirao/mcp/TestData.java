/*
 * ============================================================================
 *  Brazilian Soccer MCP Server - Tests
 * ----------------------------------------------------------------------------
 *  File    : TestData.java
 *  Purpose : Shared, lazily-loaded knowledge graph for the test suite.
 *  Context : Loading the six CSV files takes a few hundred milliseconds; the
 *            tests share a single instance so the whole suite stays fast and
 *            exercises the real datasets (not fixtures), matching the spec's
 *            "all CSV files loadable and queryable" requirement.
 * ============================================================================
 */
package com.brasileirao.mcp;

import com.brasileirao.mcp.data.KnowledgeGraph;
import com.brasileirao.mcp.query.QueryService;

import java.nio.file.Path;
import java.nio.file.Paths;

final class TestData {

    private static KnowledgeGraph graph;
    private static QueryService query;

    private TestData() {
    }

    static synchronized KnowledgeGraph graph() {
        if (graph == null) {
            try {
                graph = KnowledgeGraph.load(dataDir());
            } catch (Exception e) {
                throw new RuntimeException("Failed to load datasets for tests", e);
            }
        }
        return graph;
    }

    static synchronized QueryService query() {
        if (query == null) {
            query = new QueryService(graph());
        }
        return query;
    }

    static Path dataDir() {
        Path p = Paths.get("data", "kaggle");
        if (!p.toFile().isDirectory()) {
            p = Paths.get("..", "data", "kaggle");
        }
        return p;
    }
}
