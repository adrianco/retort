package com.brsoccer.mcp.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Map;

/**
 * Minimal MCP (Model Context Protocol) server.
 *
 * Implements JSON-RPC 2.0 over stdio with:
 *   - initialize
 *   - notifications/initialized
 *   - tools/list
 *   - tools/call
 *   - ping
 *
 * Run with:  java -jar brazilian-soccer-mcp.jar [data-dir]
 */
public class McpServer {

    private static final String PROTOCOL_VERSION = "2024-11-05";
    private static final String SERVER_NAME = "brazilian-soccer-mcp";
    private static final String SERVER_VERSION = "1.0.0";

    private final ObjectMapper mapper = new ObjectMapper();
    private final ToolHandlers handlers;

    public McpServer(SoccerKnowledgeBase kb) {
        this.handlers = new ToolHandlers(kb);
    }

    public static void main(String[] args) throws Exception {
        Path dataDir = Path.of(args.length > 0 ? args[0] : "data/kaggle");
        SoccerKnowledgeBase kb = new SoccerKnowledgeBase(dataDir);
        McpServer server = new McpServer(kb);
        server.serve(System.in, System.out);
    }

    public void serve(java.io.InputStream in, java.io.OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        PrintWriter writer = new PrintWriter(new java.io.OutputStreamWriter(out, StandardCharsets.UTF_8), true);
        String line;
        while ((line = reader.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;
            String response = handle(line);
            if (response != null) {
                writer.println(response);
                writer.flush();
            }
        }
    }

    /** Public for testing. */
    public String handle(String requestLine) {
        JsonNode req;
        try {
            req = mapper.readTree(requestLine);
        } catch (Exception e) {
            return error(null, -32700, "Parse error: " + e.getMessage());
        }
        if (!req.path("jsonrpc").asText("").equals("2.0")) {
            return error(req.get("id"), -32600, "Invalid Request");
        }
        String method = req.path("method").asText("");
        JsonNode id = req.get("id");
        JsonNode params = req.path("params");

        if (id == null || id.isNull()) {
            // notification - no response
            return null;
        }

        try {
            switch (method) {
                case "initialize": return initializeResult(id);
                case "ping":       return resultOk(id);
                case "tools/list": return toolsList(id);
                case "tools/call": return toolsCall(id, params);
                case "resources/list":
                case "prompts/list":
                    return emptyList(id, method.startsWith("resources") ? "resources" : "prompts");
                default:
                    return error(id, -32601, "Method not found: " + method);
            }
        } catch (IllegalArgumentException e) {
            return error(id, -32602, e.getMessage());
        } catch (Exception e) {
            return error(id, -32603, "Internal error: " + e.getMessage());
        }
    }

    private String initializeResult(JsonNode id) {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = result.putObject("capabilities");
        caps.putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        return wrap(id, result);
    }

    private String toolsList(JsonNode id) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode arr = result.putArray("tools");
        for (Map.Entry<String, Map<String, Object>> e : ToolHandlers.toolDefinitions().entrySet()) {
            ObjectNode t = arr.addObject();
            t.put("name", e.getKey());
            t.put("description", (String) e.getValue().get("description"));
            t.set("inputSchema", mapper.valueToTree(e.getValue().get("inputSchema")));
        }
        return wrap(id, result);
    }

    private String toolsCall(JsonNode id, JsonNode params) {
        String name = params.path("name").asText("");
        JsonNode args = params.path("arguments");
        if (name.isEmpty()) return error(id, -32602, "missing tool name");
        String text;
        boolean isError = false;
        try {
            text = handlers.dispatch(name, args);
        } catch (IllegalArgumentException e) {
            text = e.getMessage();
            isError = true;
        }
        ObjectNode result = mapper.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", text);
        result.put("isError", isError);
        return wrap(id, result);
    }

    private String emptyList(JsonNode id, String key) {
        ObjectNode result = mapper.createObjectNode();
        result.putArray(key);
        return wrap(id, result);
    }

    private String resultOk(JsonNode id) {
        ObjectNode result = mapper.createObjectNode();
        return wrap(id, result);
    }

    private String wrap(JsonNode id, JsonNode result) {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        if (id != null) resp.set("id", id);
        resp.set("result", result);
        return resp.toString();
    }

    private String error(JsonNode id, int code, String message) {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        if (id != null) resp.set("id", id); else resp.putNull("id");
        ObjectNode err = resp.putObject("error");
        err.put("code", code);
        err.put("message", message);
        return resp.toString();
    }
}
