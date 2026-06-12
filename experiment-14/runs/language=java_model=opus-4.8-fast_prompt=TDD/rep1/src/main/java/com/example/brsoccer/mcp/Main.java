/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    Main.java
 * Purpose: Process entry point. Loads the Kaggle datasets from a data directory
 *          (first CLI argument, or the BRSOCCER_DATA_DIR env var, or the default
 *          "data/kaggle"), constructs the MCP server and serves JSON-RPC over
 *          stdin/stdout. Diagnostic/progress output goes to stderr so it never
 *          corrupts the protocol stream on stdout.
 * Part of: mcp package (application bootstrap / stdio transport host).
 * ============================================================================
 */
package com.example.brsoccer.mcp;

import com.example.brsoccer.data.DataStore;
import com.example.brsoccer.query.SoccerDatabase;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/** Launches the Brazilian Soccer MCP server over stdio. */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws IOException {
        Path dataDir = resolveDataDir(args);
        System.err.println("[brazilian-soccer-mcp] loading data from " + dataDir.toAbsolutePath());
        SoccerDatabase db = DataStore.loadFromDirectory(dataDir);
        System.err.println("[brazilian-soccer-mcp] ready: " + db.matchCount()
                + " matches, " + db.playerCount() + " players. Serving MCP over stdio.");

        McpServer server = new McpServer(new SoccerTools(db));
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        Writer out = new OutputStreamWriter(System.out, StandardCharsets.UTF_8);
        StdioTransport.serve(server, in, out);
    }

    private static Path resolveDataDir(String[] args) {
        if (args.length > 0 && !args[0].isBlank()) {
            return Path.of(args[0]);
        }
        String env = System.getenv("BRSOCCER_DATA_DIR");
        if (env != null && !env.isBlank()) {
            return Path.of(env);
        }
        return Path.of("data", "kaggle");
    }
}
