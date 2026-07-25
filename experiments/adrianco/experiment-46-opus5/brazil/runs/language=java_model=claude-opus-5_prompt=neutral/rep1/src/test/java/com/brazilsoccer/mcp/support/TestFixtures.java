package com.brazilsoccer.mcp.support;

import com.brazilsoccer.mcp.data.DataLoader;
import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.tools.ToolRegistry;

import java.util.Map;

/**
 * Loads the real datasets once for the whole test run.
 *
 * <p>The knowledge graph is immutable after loading, so every test (including the Cucumber
 * scenarios) shares the same instance; this keeps the suite fast and mirrors how the server runs
 * in production - load once, answer many queries.
 */
public final class TestFixtures {

    private static KnowledgeGraph graph;
    private static ToolRegistry registry;

    private TestFixtures() {
    }

    public static synchronized KnowledgeGraph graph() {
        if (graph == null) {
            graph = DataLoader.load(DataLoader.resolveDefaultDirectory());
        }
        return graph;
    }

    public static synchronized ToolRegistry registry() {
        if (registry == null) {
            registry = new ToolRegistry(graph());
        }
        return registry;
    }

    /** Convenience wrapper around {@link ToolRegistry#call(String, Map)}. */
    public static String call(String tool, Map<String, Object> arguments) {
        return registry().call(tool, arguments);
    }
}
