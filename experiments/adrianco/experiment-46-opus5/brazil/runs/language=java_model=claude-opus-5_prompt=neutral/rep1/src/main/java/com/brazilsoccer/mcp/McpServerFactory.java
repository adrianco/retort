package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.tools.SoccerTool;
import com.brazilsoccer.mcp.tools.ToolException;
import com.brazilsoccer.mcp.tools.ToolRegistry;
import io.modelcontextprotocol.json.McpJsonDefaults;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpServerTransportProvider;

import java.io.InputStream;
import java.io.OutputStream;
import java.time.Duration;
import java.util.List;

/**
 * Adapts the transport independent {@link ToolRegistry} to the MCP Java SDK.
 *
 * <p>Each {@link SoccerTool} becomes a synchronous MCP tool whose handler returns the tool text as
 * a single text content block. {@link ToolException}s (unknown club, bad argument, missing season)
 * are turned into MCP error results so that the model can correct itself, while unexpected
 * failures are reported as errors too instead of killing the session.
 */
public final class McpServerFactory {

    /** Instructions advertised to the client during initialisation. */
    public static final String INSTRUCTIONS = """
            Knowledge graph of Brazilian soccer built from six Kaggle datasets: Brasileirão Série
            A/B/C, Copa do Brasil and Copa Libertadores matches (2003-2023) plus the FIFA player
            database.

            Suggested workflow:
              1. call dataset_info once to learn which competitions and seasons exist;
              2. use list_teams when a club name is ambiguous (Atlético-MG vs Athletico-PR);
              3. answer match questions with search_matches / head_to_head / find_derbies,
                 club questions with team_stats / team_competitions,
                 season questions with standings / competition_summary / compare_seasons,
                 player questions with search_players / player_profile / player_club_summary,
                 and aggregate questions with statistics.

            Club names may be written in any of the spellings found in the source files
            ("Flamengo", "Flamengo-RJ", "Atletico Mineiro"); they are normalised automatically.
            The datasets contain no goal scorer information, so individual scoring records cannot
            be answered.
            """;

    private McpServerFactory() {
    }

    /** Wraps every registered tool in an MCP tool specification. */
    public static List<McpServerFeatures.SyncToolSpecification> toolSpecifications(ToolRegistry registry) {
        return registry.tools().stream().map(McpServerFactory::toSpecification).toList();
    }

    private static McpServerFeatures.SyncToolSpecification toSpecification(SoccerTool tool) {
        McpSchema.Tool schema = McpSchema.Tool.builder()
                .name(tool.name())
                .title(tool.title())
                .description(tool.description())
                .inputSchema(tool.inputSchema())
                .build();
        return new McpServerFeatures.SyncToolSpecification(schema, (exchange, request) -> {
            try {
                return McpSchema.CallToolResult.builder()
                        .addTextContent(tool.call(request.arguments()))
                        .isError(false)
                        .build();
            } catch (ToolException e) {
                return McpSchema.CallToolResult.builder()
                        .addTextContent(e.getMessage())
                        .isError(true)
                        .build();
            } catch (RuntimeException e) {
                System.err.println("[brazilian-soccer-mcp] tool " + tool.name() + " failed: " + e);
                return McpSchema.CallToolResult.builder()
                        .addTextContent("The tool '" + tool.name() + "' failed: " + e)
                        .isError(true)
                        .build();
            }
        });
    }

    /** Builds a synchronous MCP server on top of any transport provider. */
    public static McpSyncServer create(ToolRegistry registry, McpServerTransportProvider transport) {
        return McpServer.sync(transport)
                .serverInfo(new McpSchema.Implementation("brazilian-soccer-mcp", "Brazilian Soccer Knowledge Graph", "1.0.0"))
                .instructions(INSTRUCTIONS)
                .capabilities(McpSchema.ServerCapabilities.builder().tools(true).build())
                .requestTimeout(Duration.ofSeconds(30))
                .tools(toolSpecifications(registry))
                .build();
    }

    /** Builds the stdio server used by MCP clients such as Claude Desktop or Claude Code. */
    public static McpSyncServer createStdio(ToolRegistry registry, InputStream in, OutputStream out) {
        return create(registry, new StdioServerTransportProvider(McpJsonDefaults.getMapper(), in, out));
    }
}
