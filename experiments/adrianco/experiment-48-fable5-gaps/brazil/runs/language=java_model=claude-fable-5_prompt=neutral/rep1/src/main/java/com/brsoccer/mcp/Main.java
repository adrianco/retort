package com.brsoccer.mcp;

import com.brsoccer.mcp.data.DataStore;
import com.brsoccer.mcp.query.QueryService;
import com.brsoccer.mcp.server.McpServer;
import com.brsoccer.mcp.tools.McpTools;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Entry point. Loads the CSV datasets and serves MCP over stdio.
 *
 * Data directory resolution: first CLI argument, else $BRSOCCER_DATA, else ./data/kaggle.
 */
public final class Main {

    public static void main(String[] args) throws Exception {
        Path dir = args.length > 0
            ? Path.of(args[0])
            : Path.of(System.getenv().getOrDefault("BRSOCCER_DATA", "data/kaggle"));
        if (!Files.isDirectory(dir)) {
            System.err.println("Data directory not found: " + dir.toAbsolutePath());
            System.err.println("Usage: java -jar brazilian-soccer-mcp.jar [data-dir]");
            System.exit(1);
        }
        long t0 = System.currentTimeMillis();
        DataStore store = new DataStore();
        store.loadAll(dir);
        System.err.printf("brazilian-soccer-mcp: loaded %,d matches and %,d players in %d ms%n",
            store.matches().size(), store.players().size(), System.currentTimeMillis() - t0);
        new McpServer(new McpTools(new QueryService(store)), System.in, System.out).run();
    }

    private Main() {}
}
