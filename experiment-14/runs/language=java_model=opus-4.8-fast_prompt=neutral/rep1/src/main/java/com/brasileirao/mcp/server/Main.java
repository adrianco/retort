/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : Main.java
 *  Purpose : Process entry point. Loads the knowledge graph and starts the MCP
 *            stdio server.
 *
 *  Context : Resolves the data directory (CLI arg, BRAZIL_SOCCER_DATA env var,
 *            or the default data/kaggle/ next to the working directory), loads
 *            every CSV once at startup, then serves MCP requests on stdin/stdout.
 *            All human-readable startup logging is sent to stderr so stdout
 *            carries only protocol traffic. A '--selftest' flag runs a few
 *            representative queries and prints them, which is handy for a quick
 *            manual smoke check without an MCP client.
 *
 *  Used by : launched via `java -jar brazilian-soccer-mcp.jar` (see README).
 * ============================================================================
 */
package com.brasileirao.mcp.server;

import com.brasileirao.mcp.data.KnowledgeGraph;
import com.brasileirao.mcp.query.QueryService;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Entry point wiring the knowledge graph to the MCP stdio transport. */
public final class Main {

    public static void main(String[] args) throws Exception {
        boolean selfTest = false;
        String dataArg = null;
        for (String a : args) {
            if (a.equals("--selftest")) {
                selfTest = true;
            } else if (!a.startsWith("--")) {
                dataArg = a;
            }
        }

        Path dataDir = resolveDataDir(dataArg);
        System.err.println("[brazilian-soccer-mcp] Loading datasets from " + dataDir.toAbsolutePath());
        long t0 = System.currentTimeMillis();
        KnowledgeGraph graph = KnowledgeGraph.load(dataDir);
        QueryService query = new QueryService(graph);
        System.err.printf("[brazilian-soccer-mcp] Loaded %,d matches and %,d players in %d ms.%n",
                graph.matchCount(), graph.playerCount(), System.currentTimeMillis() - t0);

        Tools tools = new Tools(query);

        if (selfTest) {
            runSelfTest(tools);
            return;
        }

        McpServer server = new McpServer(tools, "brazilian-soccer-mcp", "1.0.0");
        server.serve(System.in, System.out);
    }

    /** Locate the data directory from arg, env var, or sensible defaults. */
    static Path resolveDataDir(String dataArg) {
        if (dataArg != null) {
            return Paths.get(dataArg);
        }
        String env = System.getenv("BRAZIL_SOCCER_DATA");
        if (env != null && !env.isBlank()) {
            return Paths.get(env);
        }
        Path[] candidates = {
                Paths.get("data", "kaggle"),
                Paths.get("..", "data", "kaggle"),
        };
        for (Path c : candidates) {
            if (Files.isDirectory(c)) {
                return c;
            }
        }
        return candidates[0];
    }

    private static void runSelfTest(Tools tools) throws Exception {
        ObjectMapper m = new ObjectMapper();
        System.out.println("=== list_competitions ===");
        System.out.println(tools.callTool("list_competitions", null));

        System.out.println("\n=== head_to_head Flamengo vs Fluminense ===");
        ObjectNode h2h = m.createObjectNode();
        h2h.put("team_a", "Flamengo");
        h2h.put("team_b", "Fluminense");
        System.out.println(tools.callTool("head_to_head", h2h));

        System.out.println("\n=== standings Brasileirão 2019 ===");
        ObjectNode st = m.createObjectNode();
        st.put("competition", "Brasileirão Série A");
        st.put("season", 2019);
        System.out.println(tools.callTool("standings", st));

        System.out.println("\n=== top Brazilian players ===");
        ObjectNode pl = m.createObjectNode();
        pl.put("nationality", "Brazil");
        pl.put("limit", 5);
        System.out.println(tools.callTool("search_players", pl));
    }

    private Main() {
    }
}
