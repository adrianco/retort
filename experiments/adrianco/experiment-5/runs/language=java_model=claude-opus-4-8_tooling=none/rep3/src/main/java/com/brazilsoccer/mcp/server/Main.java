/*
 * ============================================================================
 * Main.java
 * ============================================================================
 * Context:
 *   Entry point for the Brazilian Soccer MCP server. Loads all datasets into a
 *   DataStore, wires up the SoccerTools and starts the stdio JSON-RPC loop.
 *
 *   Startup diagnostics are written to stderr so the stdout channel stays a
 *   clean JSON-RPC stream for the MCP client.
 *
 *   The data directory is auto-detected (./data/kaggle) but can be overridden
 *   with -Dsoccer.data.dir=... or the SOCCER_DATA_DIR environment variable.
 * ============================================================================
 */
package com.brazilsoccer.mcp.server;

import com.brazilsoccer.mcp.data.DataStore;

public final class Main {

    public static void main(String[] args) throws Exception {
        long start = System.currentTimeMillis();
        DataStore store = DataStore.load();
        long ms = System.currentTimeMillis() - start;
        System.err.printf("[%s] Loaded %d matches and %d players from %s in %d ms%n",
                McpServer.SERVER_NAME, store.matches().size(), store.players().size(),
                store.dataDir(), ms);

        SoccerTools tools = new SoccerTools(store);
        McpServer server = new McpServer(tools);
        System.err.printf("[%s] MCP server ready (protocol %s). Listening on stdio.%n",
                McpServer.SERVER_NAME, McpServer.PROTOCOL_VERSION);
        server.serve(System.in, System.out);
    }
}
