package com.brazilsoccer.mcp.tools;

import java.util.Map;
import java.util.function.Function;

/**
 * A transport independent tool definition.
 *
 * <p>Keeping the tools free of MCP types means the whole catalogue can be exercised by tests
 * without a protocol session, while {@code McpServerFactory} adapts each definition to an MCP
 * {@code SyncToolSpecification}.
 */
public record SoccerTool(String name,
                         String title,
                         String description,
                         Map<String, Object> inputSchema,
                         Function<ToolArguments, String> handler) {

    /** Runs the tool; {@link ToolException} messages are meant to be shown to the caller. */
    public String call(Map<String, Object> arguments) {
        return handler.apply(ToolArguments.of(arguments));
    }
}
