/*
 * Context block: Entry point. Loads the Kaggle datasets once at startup, then serves MCP
 * requests over stdin/stdout. Dataset directory: first argument, else the
 * BRAZIL_SOCCER_DATA environment variable, else data/kaggle relative to the working directory.
 * Logs go to stderr so they never corrupt the stdout protocol stream.
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.SoccerDatabase;
import com.brazilsoccer.mcp.protocol.McpServer;
import com.brazilsoccer.mcp.tools.SoccerTools;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

public final class Main {

    static final String DATA_DIR_ENV = "BRAZIL_SOCCER_DATA";
    static final String DEFAULT_DATA_DIR = "data/kaggle";

    private Main() {
    }

    public static void main(String[] args) throws Exception {
        Path dataDir = resolveDataDir(args);
        long started = System.nanoTime();
        SoccerDatabase db = SoccerDatabase.fromDirectory(dataDir);
        System.err.printf("Loaded %d matches and %d players from %s in %d ms%n",
                db.matchCount(), db.playerCount(), dataDir.toAbsolutePath(),
                (System.nanoTime() - started) / 1_000_000);

        ObjectMapper mapper = new ObjectMapper();
        McpServer server = new McpServer(new SoccerTools(db, mapper), mapper);
        PrintStream stdout = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        try (BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            server.serve(in, stdout);
        }
    }

    static Path resolveDataDir(String[] args) {
        if (args.length > 0) {
            return Path.of(args[0]);
        }
        String env = System.getenv(DATA_DIR_ENV);
        return Path.of(env != null && !env.isBlank() ? env : DEFAULT_DATA_DIR);
    }
}
