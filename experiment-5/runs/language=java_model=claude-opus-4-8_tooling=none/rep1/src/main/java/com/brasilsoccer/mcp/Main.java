/*
 * ============================================================================
 * Main - entry point for the Brazilian Soccer MCP server
 * ============================================================================
 * Context:
 *   Boots the server: locates the data directory, loads all CSV datasets into
 *   the in-memory KnowledgeBase, then serves the MCP protocol over stdin/stdout.
 *
 *   Data directory resolution order:
 *     1. First CLI argument
 *     2. SOCCER_DATA_DIR environment variable
 *     3. Default "data/kaggle" (relative to the working directory)
 *
 *   All diagnostics go to stderr; stdout carries only JSON-RPC frames so the
 *   server can be wired directly into an MCP client.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.mcp.McpServer;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

public final class Main {

    public static void main(String[] args) throws Exception {
        Path dataDir = resolveDataDir(args);
        System.err.println("[brazilian-soccer-mcp] Loading data from: " + dataDir.toAbsolutePath());

        long t0 = System.currentTimeMillis();
        KnowledgeBase kb = KnowledgeBase.load(dataDir);
        long ms = System.currentTimeMillis() - t0;
        System.err.printf("[brazilian-soccer-mcp] Loaded %d matches and %d players in %d ms%n",
                kb.allMatches().size(), kb.allPlayers().size(), ms);

        McpServer server = new McpServer(kb);
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        Writer out = new OutputStreamWriter(System.out, StandardCharsets.UTF_8);
        System.err.println("[brazilian-soccer-mcp] Ready. Listening on stdio.");
        server.serve(in, out);
    }

    private static Path resolveDataDir(String[] args) {
        if (args.length > 0 && !args[0].isBlank()) {
            return Path.of(args[0]);
        }
        String env = System.getenv("SOCCER_DATA_DIR");
        if (env != null && !env.isBlank()) {
            return Path.of(env);
        }
        return Path.of("data", "kaggle");
    }
}
