/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    Main.java
 * Purpose: Executable entry point. Loads the Kaggle datasets, wires the query
 *          engine and tool catalogue into the MCP server, and serves the MCP
 *          protocol over stdio. The data directory defaults to ./data but can
 *          be overridden with the first CLI argument or the BRAZIL_SOCCER_DATA
 *          environment variable, so the server runs from any working directory.
 *
 *          Run:  java -jar target/brazilian-soccer-mcp.jar [dataDir]
 *          MCP client config example (Claude Desktop / mcp clients):
 *            command: "java"
 *            args: ["-jar", "/abs/path/brazilian-soccer-mcp.jar", "/abs/path/data"]
 * ===========================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.SoccerData;
import com.brazilsoccer.mcp.query.SoccerQueries;
import com.brazilsoccer.mcp.server.McpServer;
import com.brazilsoccer.mcp.server.SoccerTools;

import java.nio.file.Path;

public final class Main {

    public static void main(String[] args) throws Exception {
        Path dataDir = resolveDataDir(args);
        // Logs go to stderr so they never corrupt the JSON-RPC stream on stdout.
        System.err.println("[brazilian-soccer-mcp] loading data from " + dataDir.toAbsolutePath());

        SoccerData data = SoccerData.load(dataDir);
        System.err.printf("[brazilian-soccer-mcp] loaded %d matches and %d players%n",
                data.matches().size(), data.players().size());

        SoccerQueries queries = new SoccerQueries(data);
        SoccerTools tools = new SoccerTools(queries);
        McpServer server = new McpServer(tools.tools());

        System.err.println("[brazilian-soccer-mcp] ready - serving MCP over stdio");
        server.serve(System.in, System.out);
    }

    private static Path resolveDataDir(String[] args) {
        if (args.length > 0 && !args[0].isBlank()) {
            return Path.of(args[0]);
        }
        String env = System.getenv("BRAZIL_SOCCER_DATA");
        if (env != null && !env.isBlank()) {
            return Path.of(env);
        }
        return Path.of("data");
    }
}
