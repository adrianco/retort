/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : McpServer.java
 *  Purpose : Minimal Model Context Protocol server speaking JSON-RPC 2.0 over
 *            stdio (newline-delimited JSON), the standard MCP stdio transport.
 *
 *  Context : Wires the LLM/MCP client to the Tools dispatcher. It implements the
 *            handshake (initialize / notifications/initialized), tools/list and
 *            tools/call, plus ping. Requests are read one JSON object per line
 *            from stdin; responses are written one per line to stdout. Diagnostic
 *            logging goes to stderr so it never corrupts the protocol stream.
 *            The transport is intentionally tiny and delegates all domain logic
 *            to Tools/QueryService; handleMessage() is exposed so the protocol
 *            can be exercised directly in tests without real pipes.
 *
 *  Used by : Main (entry point) and McpServerTest.
 * ============================================================================
 */
package com.brasileirao.mcp.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

/** JSON-RPC 2.0 over stdio implementation of the MCP server. */
public final class McpServer {

    private static final String PROTOCOL_VERSION = "2024-11-05";
    private static final ObjectMapper M = new ObjectMapper();

    private final Tools tools;
    private final String serverName;
    private final String serverVersion;

    public McpServer(Tools tools, String serverName, String serverVersion) {
        this.tools = tools;
        this.serverName = serverName;
        this.serverVersion = serverVersion;
    }

    /** Run the read/respond loop until stdin is closed. */
    public void serve(InputStream in, OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        PrintStream writer = new PrintStream(out, true, StandardCharsets.UTF_8);
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            JsonNode response;
            try {
                JsonNode request = M.readTree(line);
                response = handleMessage(request);
            } catch (Exception e) {
                response = errorResponse(null, -32700, "Parse error: " + e.getMessage());
            }
            if (response != null) {
                writer.println(M.writeValueAsString(response));
            }
        }
    }

    /**
     * Handle a single JSON-RPC message and return the response node, or
     * {@code null} for notifications (which must not be answered).
     */
    public JsonNode handleMessage(JsonNode request) {
        JsonNode idNode = request.get("id");
        boolean isNotification = idNode == null;
        String method = request.path("method").asText("");
        JsonNode params = request.get("params");

        try {
            switch (method) {
                case "initialize":
                    return result(idNode, initializeResult());
                case "notifications/initialized":
                case "notifications/cancelled":
                    return null; // notifications get no reply
                case "ping":
                    return result(idNode, M.createObjectNode());
                case "tools/list":
                    return result(idNode, toolsListResult());
                case "tools/call":
                    return result(idNode, toolsCallResult(params));
                default:
                    if (isNotification) {
                        return null;
                    }
                    return errorResponse(idNode, -32601, "Method not found: " + method);
            }
        } catch (IllegalArgumentException e) {
            return errorResponse(idNode, -32602, e.getMessage());
        } catch (Exception e) {
            return errorResponse(idNode, -32603, "Internal error: " + e.getMessage());
        }
    }

    // ------------------------------------------------------------- results

    private ObjectNode initializeResult() {
        ObjectNode r = M.createObjectNode();
        r.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = M.createObjectNode();
        ObjectNode toolsCap = M.createObjectNode();
        toolsCap.put("listChanged", false);
        caps.set("tools", toolsCap);
        r.set("capabilities", caps);
        ObjectNode info = M.createObjectNode();
        info.put("name", serverName);
        info.put("version", serverVersion);
        r.set("serverInfo", info);
        r.put("instructions", "Query Brazilian soccer match, team, player and competition data. "
                + "Start with list_competitions to see what is available.");
        return r;
    }

    private ObjectNode toolsListResult() {
        ObjectNode r = M.createObjectNode();
        r.set("tools", tools.listTools());
        return r;
    }

    private ObjectNode toolsCallResult(JsonNode params) {
        if (params == null || !params.hasNonNull("name")) {
            throw new IllegalArgumentException("tools/call requires a 'name'");
        }
        String name = params.get("name").asText();
        JsonNode args = params.get("arguments");

        ObjectNode r = M.createObjectNode();
        ArrayNode content = M.createArrayNode();
        ObjectNode textNode = M.createObjectNode();
        textNode.put("type", "text");
        try {
            textNode.put("text", tools.callTool(name, args));
            r.put("isError", false);
        } catch (IllegalArgumentException e) {
            textNode.put("text", "Error: " + e.getMessage());
            r.put("isError", true);
        }
        content.add(textNode);
        r.set("content", content);
        return r;
    }

    // ------------------------------------------------------------- envelopes

    private ObjectNode result(JsonNode id, JsonNode payload) {
        ObjectNode r = M.createObjectNode();
        r.put("jsonrpc", "2.0");
        r.set("id", id == null ? null : id);
        r.set("result", payload);
        return r;
    }

    private ObjectNode errorResponse(JsonNode id, int code, String message) {
        ObjectNode r = M.createObjectNode();
        r.put("jsonrpc", "2.0");
        r.set("id", id == null ? null : id);
        ObjectNode err = M.createObjectNode();
        err.put("code", code);
        err.put("message", message);
        r.set("error", err);
        return r;
    }
}
