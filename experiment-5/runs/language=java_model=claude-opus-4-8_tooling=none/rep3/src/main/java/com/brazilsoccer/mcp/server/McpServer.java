/*
 * ============================================================================
 * McpServer.java
 * ============================================================================
 * Context:
 *   Minimal Model Context Protocol server speaking JSON-RPC 2.0 over the stdio
 *   transport: each request is one line of JSON on stdin, each response one
 *   line of JSON on stdout. Diagnostic logging goes to stderr so it never
 *   corrupts the protocol stream.
 *
 *   Implemented methods:
 *     - initialize                -> protocol/version + capabilities handshake
 *     - notifications/initialized -> (notification, no response)
 *     - tools/list                -> the SoccerTools tool catalogue
 *     - tools/call                -> dispatch to SoccerTools, return text content
 *     - ping                      -> {}
 *
 *   Tool execution is delegated to SoccerTools; this class is purely the
 *   transport/dispatch loop.
 * ============================================================================
 */
package com.brazilsoccer.mcp.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;

/** JSON-RPC 2.0 / stdio MCP server. */
public final class McpServer {

    /** MCP protocol revision this server implements. */
    public static final String PROTOCOL_VERSION = "2024-11-05";
    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";

    private final ObjectMapper json = new ObjectMapper();
    private final SoccerTools tools;

    public McpServer(SoccerTools tools) {
        this.tools = tools;
    }

    /** Run the stdio read/dispatch/write loop until end of input. */
    public void serve(InputStream in, OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;
            ObjectNode response;
            try {
                JsonNode request = json.readTree(line);
                response = handle(request);
            } catch (Exception e) {
                response = errorResponse(null, -32700, "Parse error: " + e.getMessage());
            }
            if (response != null) { // notifications produce no response
                writer.write(json.writeValueAsString(response));
                writer.write("\n");
                writer.flush();
            }
        }
    }

    /** Handle a single parsed JSON-RPC request, returning the response (or null for notifications). */
    public ObjectNode handle(JsonNode request) {
        JsonNode idNode = request.get("id");
        String method = request.path("method").asText("");
        JsonNode params = request.get("params");

        try {
            switch (method) {
                case "initialize":
                    return result(idNode, initializeResult());
                case "notifications/initialized":
                case "notifications/cancelled":
                    return null; // notifications: no response
                case "ping":
                    return result(idNode, json.createObjectNode());
                case "tools/list":
                    return result(idNode, toolsListResult());
                case "tools/call":
                    return result(idNode, toolsCallResult(params));
                default:
                    return errorResponse(idNode, -32601, "Method not found: " + method);
            }
        } catch (IllegalArgumentException e) {
            return errorResponse(idNode, -32602, e.getMessage());
        } catch (Exception e) {
            return errorResponse(idNode, -32603, "Internal error: " + e.getMessage());
        }
    }

    private ObjectNode initializeResult() {
        ObjectNode r = json.createObjectNode();
        r.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = json.createObjectNode();
        caps.set("tools", json.createObjectNode());
        r.set("capabilities", caps);
        ObjectNode info = json.createObjectNode();
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        r.set("serverInfo", info);
        r.put("instructions",
                "Query Brazilian soccer data: matches, team records, head-to-head, FIFA players, "
                        + "league standings and aggregate statistics.");
        return r;
    }

    private ObjectNode toolsListResult() {
        ObjectNode r = json.createObjectNode();
        r.set("tools", tools.toolDefinitions());
        return r;
    }

    private ObjectNode toolsCallResult(JsonNode params) {
        if (params == null || !params.hasNonNull("name")) {
            throw new IllegalArgumentException("tools/call requires a 'name'");
        }
        String name = params.get("name").asText();
        JsonNode arguments = params.get("arguments");

        ObjectNode r = json.createObjectNode();
        ArrayNode content = json.createArrayNode();
        try {
            String text = tools.call(name, arguments);
            ObjectNode block = json.createObjectNode();
            block.put("type", "text");
            block.put("text", text);
            content.add(block);
            r.set("content", content);
            r.put("isError", false);
        } catch (IllegalArgumentException e) {
            // Report tool-level errors as content with isError=true per MCP convention.
            ObjectNode block = json.createObjectNode();
            block.put("type", "text");
            block.put("text", "Error: " + e.getMessage());
            content.add(block);
            r.set("content", content);
            r.put("isError", true);
        }
        return r;
    }

    // ------------------------------------------------------------------
    // JSON-RPC envelope helpers
    // ------------------------------------------------------------------

    private ObjectNode result(JsonNode id, JsonNode result) {
        ObjectNode r = json.createObjectNode();
        r.put("jsonrpc", "2.0");
        setId(r, id);
        r.set("result", result);
        return r;
    }

    private ObjectNode errorResponse(JsonNode id, int code, String message) {
        ObjectNode r = json.createObjectNode();
        r.put("jsonrpc", "2.0");
        setId(r, id);
        ObjectNode err = json.createObjectNode();
        err.put("code", code);
        err.put("message", message);
        r.set("error", err);
        return r;
    }

    private void setId(ObjectNode r, JsonNode id) {
        if (id == null || id.isNull()) {
            r.putNull("id");
        } else {
            r.set("id", id);
        }
    }
}
