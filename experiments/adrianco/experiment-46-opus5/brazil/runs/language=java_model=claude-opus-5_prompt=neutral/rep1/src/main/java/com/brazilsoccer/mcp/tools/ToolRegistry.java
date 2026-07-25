package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.graph.KnowledgeGraph;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The catalogue of tools exposed by the MCP server.
 *
 * <p>The registry is transport agnostic: tests call {@link #call(String, Map)} directly, while
 * {@code McpServerFactory} adapts each entry to an MCP tool specification.
 */
public final class ToolRegistry {

    private final ToolContext context;
    private final Map<String, SoccerTool> tools = new LinkedHashMap<>();

    public ToolRegistry(KnowledgeGraph graph) {
        this.context = new ToolContext(graph);
        List<SoccerTool> all = new ArrayList<>();
        all.addAll(GraphTools.create(context));
        all.addAll(MatchTools.create(context));
        all.addAll(TeamTools.create(context));
        all.addAll(CompetitionTools.create(context));
        all.addAll(PlayerTools.create(context));
        all.addAll(StatsTools.create(context));
        all.forEach(tool -> tools.put(tool.name(), tool));
    }

    public List<SoccerTool> tools() {
        return List.copyOf(tools.values());
    }

    public Optional<SoccerTool> tool(String name) {
        return Optional.ofNullable(tools.get(name));
    }

    public ToolContext context() {
        return context;
    }

    /** Runs a tool by name; throws {@link ToolException} for unknown tools or bad arguments. */
    public String call(String name, Map<String, Object> arguments) {
        SoccerTool tool = tools.get(name);
        if (tool == null) {
            throw new ToolException("Unknown tool '" + name + "'. Available tools: "
                    + String.join(", ", tools.keySet()) + ".");
        }
        return tool.call(arguments);
    }
}
