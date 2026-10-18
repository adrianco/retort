package br.soccer;

import br.soccer.data.DataLoader;
import br.soccer.data.Dataset;
import br.soccer.mcp.McpServer;
import br.soccer.mcp.SoccerTools;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/**
 * Entry point. Usage: {@code java -jar brazilian-soccer-mcp.jar [dataDir]}. The data directory defaults to
 * the SOCCER_DATA_DIR environment variable, then to {@code data/kaggle}. stdout carries only protocol messages;
 * diagnostics go to stderr.
 */
public final class Main {

    private Main() {}

    public static void main(String[] args) throws IOException {
        Path dir = Path.of(args.length > 0 ? args[0] : System.getenv().getOrDefault("SOCCER_DATA_DIR", "data/kaggle"));
        long started = System.nanoTime();
        Dataset data = DataLoader.load(dir);
        System.err.printf("Loaded %d matches and %d players from %s in %d ms%n",
                data.matches().size(), data.players().size(), dir, (System.nanoTime() - started) / 1_000_000);

        McpServer server = new McpServer(new SoccerTools(data));
        server.serve(
                new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)),
                new PrintWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), true));
    }
}
