package br.soccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).
 * stdout carries protocol messages only; diagnostics go to stderr.
 *
 * <p>Usage: {@code java -jar brazilian-soccer-mcp.jar [data-dir]} (default data dir: ./data/kaggle,
 * or the BRAZILIAN_SOCCER_DATA_DIR environment variable).
 */
public final class McpServer {
    static final String SERVER_NAME = "brazilian-soccer-mcp";
    static final String SERVER_VERSION = "1.0.0";
    private static final List<String> PROTOCOL_VERSIONS = List.of("2025-06-18", "2025-03-26", "2024-11-05");
    private static final ObjectMapper JSON = new ObjectMapper();

    private final Tools tools;

    McpServer(Tools tools) {
        this.tools = tools;
    }

    public static void main(String[] args) throws IOException {
        DataStore ds;
        try {
            long t0 = System.currentTimeMillis();
            ds = DataStore.load(DataStore.defaultDataDir(args.length > 0 ? args[0] : null));
            System.err.println("[" + SERVER_NAME + "] loaded " + ds.matches.size() + " matches and " + ds.players.size()
                    + " players in " + (System.currentTimeMillis() - t0) + " ms");
        } catch (IOException e) {
            System.err.println("[" + SERVER_NAME + "] failed to load data: " + e.getMessage());
            System.exit(1);
            return;
        }
        new McpServer(new Tools(new SoccerService(ds))).serve(System.in, System.out);
    }

    /** Reads requests line by line until end of input. */
    void serve(InputStream in, OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        PrintStream writer = new PrintStream(out, false, StandardCharsets.UTF_8);
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isBlank()) continue;
            String response = handleLine(line);
            if (response != null) {
                writer.print(response);
                writer.print('\n');
                writer.flush();
            }
        }
    }

    /** Handles one JSON-RPC message; returns the serialized response, or null for notifications. */
    String handleLine(String line) {
        JsonNode msg;
        try {
            msg = JSON.readTree(line);
        } catch (IOException e) {
            return error(null, -32700, "Parse error").toString();
        }
        if (msg == null || !msg.isObject()) return error(null, -32600, "Invalid Request").toString();
        JsonNode id = msg.get("id");
        JsonNode method = msg.get("method");
        if (method == null || !method.isTextual()) {
            // a response from the client (we never send requests) or garbage
            return id == null || msg.has("result") || msg.has("error") ? null : error(id, -32600, "Invalid Request").toString();
        }
        boolean notification = id == null;
        ObjectNode response;
        try {
            response = dispatch(method.asText(), msg.get("params"), id);
        } catch (RuntimeException e) {
            System.err.println("[" + SERVER_NAME + "] internal error: " + e);
            response = error(id, -32603, "Internal error");
        }
        return notification || response == null ? null : response.toString();
    }

    private ObjectNode dispatch(String method, JsonNode params, JsonNode id) {
        switch (method) {
            case "initialize": {
                String requested = params != null && params.hasNonNull("protocolVersion") ? params.get("protocolVersion").asText() : "";
                ObjectNode r = JSON.createObjectNode();
                r.put("protocolVersion", PROTOCOL_VERSIONS.contains(requested) ? requested : PROTOCOL_VERSIONS.get(0));
                r.putObject("capabilities").putObject("tools").put("listChanged", false);
                ObjectNode info = r.putObject("serverInfo");
                info.put("name", SERVER_NAME);
                info.put("version", SERVER_VERSION);
                r.put("instructions", "Brazilian soccer knowledge base: Brasileirão, Copa do Brasil and Copa Libertadores "
                        + "matches plus the FIFA player database. Call dataset_info to see coverage. Team names may be given "
                        + "in any common spelling. All answers are computed from the bundled CSV files.");
                return result(id, r);
            }
            case "ping":
                return result(id, JSON.createObjectNode());
            case "tools/list": {
                ObjectNode r = JSON.createObjectNode();
                r.set("tools", tools.list());
                return result(id, r);
            }
            case "tools/call": {
                if (params == null || !params.hasNonNull("name") || !params.get("name").isTextual()) {
                    return error(id, -32602, "Invalid params: tool name is required");
                }
                String name = params.get("name").asText();
                if (!tools.has(name)) return error(id, -32602, "Unknown tool: " + name);
                JsonNode args = params.get("arguments");
                if (args != null && !args.isNull() && !args.isObject()) {
                    return error(id, -32602, "Invalid params: arguments must be an object");
                }
                String text;
                boolean isError = false;
                try {
                    text = tools.call(name, args);
                } catch (IllegalArgumentException e) {
                    // tool-level failure: reported in the result so the model can read it and retry
                    text = "Error: " + e.getMessage();
                    isError = true;
                }
                ObjectNode r = JSON.createObjectNode();
                ObjectNode c = r.putArray("content").addObject();
                c.put("type", "text");
                c.put("text", text);
                r.put("isError", isError);
                return result(id, r);
            }
            default:
                if (method.startsWith("notifications/")) return null;
                return error(id, -32601, "Method not found: " + method);
        }
    }

    private static ObjectNode result(JsonNode id, ObjectNode result) {
        ObjectNode o = JSON.createObjectNode();
        o.put("jsonrpc", "2.0");
        o.set("id", id);
        o.set("result", result);
        return o;
    }

    private static ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode o = JSON.createObjectNode();
        o.put("jsonrpc", "2.0");
        o.set("id", id == null ? JSON.nullNode() : id);
        ObjectNode e = o.putObject("error");
        e.put("code", code);
        e.put("message", message);
        return o;
    }
}
