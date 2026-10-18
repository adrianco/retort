package com.brazilsoccer;

import com.brazilsoccer.data.DataRepository;
import com.brazilsoccer.mcp.McpServer;
import com.brazilsoccer.mcp.SoccerTools;
import com.brazilsoccer.query.SoccerQueries;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/**
 * Starts the MCP server on stdio. The dataset directory is taken from the first argument, then the
 * {@code SOCCER_DATA_DIR} environment variable, then defaults to {@code data/kaggle}. Progress is
 * logged to stderr so stdout carries only protocol messages.
 */
public final class Main {

    private static final String DEFAULT_DATA_DIR = "data/kaggle";

    private Main() {
    }

    public static void main(String[] args) throws IOException {
        String configured = args.length > 0 ? args[0] : System.getenv("SOCCER_DATA_DIR");
        Path dataDir = Path.of(configured == null ? DEFAULT_DATA_DIR : configured);

        long started = System.nanoTime();
        DataRepository repo = DataRepository.load(dataDir);
        System.err.printf("Loaded %d matches and %d players from %s in %d ms%n",
                repo.matches().size(), repo.players().size(), dataDir.toAbsolutePath(),
                (System.nanoTime() - started) / 1_000_000);

        ObjectMapper mapper = new ObjectMapper();
        McpServer server = new McpServer(new SoccerTools(new SoccerQueries(repo), mapper), mapper);
        server.serve(new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)),
                new PrintStream(System.out, true, StandardCharsets.UTF_8));
    }
}
