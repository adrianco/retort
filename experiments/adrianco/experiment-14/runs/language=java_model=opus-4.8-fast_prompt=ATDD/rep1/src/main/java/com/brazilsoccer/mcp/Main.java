package com.brazilsoccer.mcp;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/**
 * Entry point: runs the Brazilian Soccer MCP server over stdio using
 * newline-delimited JSON-RPC messages, the standard MCP stdio transport.
 *
 * <p>The data directory defaults to {@code data/kaggle} and may be overridden with
 * the first command-line argument.
 */
public final class Main {

    public static void main(String[] args) throws Exception {
        Path dataDir = Path.of(args.length > 0 ? args[0] : "data/kaggle");
        System.err.println("[brazilian-soccer-mcp] loading datasets from " + dataDir.toAbsolutePath());
        McpServer server = new McpServer(SoccerService.load(dataDir));
        System.err.println("[brazilian-soccer-mcp] ready");

        try (BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
             BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8))) {
            String line;
            while ((line = in.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String response = server.handle(line);
                if (response != null) {
                    out.write(response);
                    out.write('\n');
                    out.flush();
                }
            }
        }
    }

    private Main() {
    }
}
