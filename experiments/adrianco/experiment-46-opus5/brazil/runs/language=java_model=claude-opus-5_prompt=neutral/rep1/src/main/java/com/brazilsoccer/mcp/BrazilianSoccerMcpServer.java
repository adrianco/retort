package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.DataLoader;
import com.brazilsoccer.mcp.graph.KnowledgeGraph;
import com.brazilsoccer.mcp.tools.SoccerTool;
import com.brazilsoccer.mcp.tools.ToolRegistry;
import io.modelcontextprotocol.server.McpSyncServer;

import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.CountDownLatch;

/**
 * Entry point of the Brazilian Soccer MCP server.
 *
 * <p>Usage:
 * <pre>
 *   java -jar target/brazilian-soccer-mcp.jar                # MCP server on stdio
 *   java -jar target/brazilian-soccer-mcp.jar --data DIR     # explicit dataset directory
 *   java -jar target/brazilian-soccer-mcp.jar --call TOOL k=v # run one tool and print the answer
 *   java -jar target/brazilian-soccer-mcp.jar --list-tools
 * </pre>
 *
 * <p>On stdio, {@code stdout} carries the JSON-RPC stream only: every log line goes to
 * {@code stderr}.
 */
public final class BrazilianSoccerMcpServer {

    /** Time granted to in-flight requests after the client closed stdin. */
    private static final long EOF_GRACE_MILLIS = 3000;

    private BrazilianSoccerMcpServer() {
    }

    public static void main(String[] args) throws Exception {
        Path dataDir = DataLoader.resolveDefaultDirectory();
        String callTool = null;
        boolean listTools = false;
        java.util.Map<String, Object> callArguments = new java.util.LinkedHashMap<>();

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--data", "-d" -> dataDir = Path.of(args[++i]);
                case "--list-tools" -> listTools = true;
                case "--call", "-c" -> callTool = args[++i];
                case "--help", "-h" -> {
                    printUsage();
                    return;
                }
                default -> {
                    int separator = args[i].indexOf('=');
                    if (separator > 0) {
                        callArguments.put(args[i].substring(0, separator), args[i].substring(separator + 1));
                    } else {
                        System.err.println("Unknown argument: " + args[i]);
                        printUsage();
                        return;
                    }
                }
            }
        }

        KnowledgeGraph graph = DataLoader.load(dataDir);
        ToolRegistry registry = new ToolRegistry(graph);

        if (listTools) {
            for (SoccerTool tool : registry.tools()) {
                System.out.println(tool.name() + " - " + tool.title());
                System.out.println("    " + tool.description());
            }
            return;
        }
        if (callTool != null) {
            System.out.println(registry.call(callTool, Map.copyOf(callArguments)));
            return;
        }

        // The client closing stdin is its way of asking the server to stop, so the input stream is
        // wrapped to release the main thread on end of stream.
        CountDownLatch shutdown = new CountDownLatch(1);
        InputStream input = new FilterInputStream(System.in) {
            @Override
            public int read() throws IOException {
                return signalOnEof(super.read());
            }

            @Override
            public int read(byte[] buffer, int offset, int length) throws IOException {
                return signalOnEof(super.read(buffer, offset, length));
            }

            private int signalOnEof(int result) {
                if (result == -1) {
                    shutdown.countDown();
                }
                return result;
            }
        };

        McpSyncServer server = McpServerFactory.createStdio(registry, input, System.out);
        System.err.println("[brazilian-soccer-mcp] MCP server ready on stdio with "
                + registry.tools().size() + " tools");

        Runtime.getRuntime().addShutdownHook(new Thread(shutdown::countDown));
        shutdown.await();
        // Requests are handled asynchronously, so give the ones that were already on the wire a
        // moment to finish before the transport is torn down.
        Thread.sleep(EOF_GRACE_MILLIS);
        server.closeGracefully();
        System.err.println("[brazilian-soccer-mcp] shutting down");
        System.exit(0);
    }

    private static void printUsage() {
        System.err.println("""
                Brazilian Soccer MCP server

                  --data, -d DIR      directory holding the Kaggle CSV files (default ./data/kaggle
                                      or $BRAZIL_SOCCER_DATA_DIR)
                  --list-tools        print the tool catalogue and exit
                  --call, -c NAME     run one tool from the command line, e.g.
                                      --call head_to_head team_a=Flamengo team_b=Fluminense
                  key=value           argument for --call
                  --help, -h          this message

                Without arguments the process speaks MCP over stdio.""");
    }
}
