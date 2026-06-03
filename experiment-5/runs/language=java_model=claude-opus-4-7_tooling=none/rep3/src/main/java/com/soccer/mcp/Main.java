package com.soccer.mcp;

import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.mcp.McpServer;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;

public final class Main {

    public static void main(String[] args) throws Exception {
        Path dataDir = resolveDataDir(args);
        long start = System.currentTimeMillis();
        DataStore store = DataStore.load(dataDir);
        long elapsed = System.currentTimeMillis() - start;
        System.err.println("Loaded " + store.matches().size() + " matches and "
                + store.players().size() + " players in " + elapsed + " ms from " + dataDir);

        McpServer server = new McpServer(store);
        try (PrintWriter out = new PrintWriter(System.out, true, StandardCharsets.UTF_8)) {
            server.run(System.in, out);
        }
    }

    private static Path resolveDataDir(String[] args) {
        if (args.length > 0) return Paths.get(args[0]);
        String env = System.getenv("SOCCER_DATA_DIR");
        if (env != null && !env.isEmpty()) return Paths.get(env);
        return Paths.get("data", "kaggle");
    }
}
