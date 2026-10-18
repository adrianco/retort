package br.soccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintWriter;

/** Minimal MCP server speaking newline-delimited JSON-RPC 2.0 over stdio. */
public final class McpServer {

    static final String PROTOCOL_VERSION = "2024-11-05";
    private static final String SERVER_NAME = "brazilian-soccer-mcp";
    private static final String SERVER_VERSION = "1.0.0";

    private final ObjectMapper json = new ObjectMapper();
    private final SoccerTools tools;

    public McpServer(SoccerTools tools) {
        this.tools = tools;
    }

    public void serve(BufferedReader in, PrintWriter out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            JsonNode response = handle(line);
            if (response != null) {
                out.println(json.writeValueAsString(response));
                out.flush();
            }
        }
    }

    /** Returns the reply for one message, or null when the message needs none (notifications, client responses). */
    JsonNode handle(String line) {
        JsonNode message;
        try {
            message = json.readTree(line);
        } catch (IOException e) {
            return error(null, -32700, "Parse error");
        }
        JsonNode id = message.get("id");
        String method = message.path("method").asText("");
        if (id == null || method.isEmpty()) {
            return null;
        }
        try {
            return switch (method) {
                case "initialize" -> result(id, initializeResult());
                case "ping" -> result(id, json.createObjectNode());
                case "tools/list" -> result(id, toolList());
                case "tools/call" -> callTool(id, message.path("params"));
                default -> error(id, -32601, "Method not found: " + method);
            };
        } catch (RuntimeException e) {
            return error(id, -32603, "Internal error: " + e.getMessage());
        }
    }

    private ObjectNode initializeResult() {
        ObjectNode result = json.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        result.putObject("capabilities").putObject("tools");
        result.putObject("serverInfo").put("name", SERVER_NAME).put("version", SERVER_VERSION);
        return result;
    }

    private ObjectNode toolList() {
        ObjectNode result = json.createObjectNode();
        result.set("tools", tools.definitions());
        return result;
    }

    private JsonNode callTool(JsonNode id, JsonNode params) {
        String name = params.path("name").asText("");
        if (!tools.has(name)) {
            return error(id, -32602, "Unknown tool: " + name);
        }
        try {
            return result(id, content(tools.call(name, params.path("arguments")), false));
        } catch (IllegalArgumentException e) {
            // Tool-level failures are reported inside the result so the model can read and correct them.
            return result(id, content(e.getMessage(), true));
        }
    }

    private ObjectNode content(String text, boolean isError) {
        ObjectNode result = json.createObjectNode();
        result.putArray("content").addObject().put("type", "text").put("text", text);
        result.put("isError", isError);
        return result;
    }

    private ObjectNode result(JsonNode id, JsonNode body) {
        ObjectNode response = envelope(id);
        response.set("result", body);
        return response;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode response = envelope(id);
        response.putObject("error").put("code", code).put("message", message);
        return response;
    }

    private ObjectNode envelope(JsonNode id) {
        ObjectNode response = json.createObjectNode();
        response.put("jsonrpc", "2.0");
        if (id == null) {
            response.putNull("id");
        } else {
            response.set("id", id);
        }
        return response;
    }
}
