/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    McpServer.java
 * Purpose: A minimal Model Context Protocol server speaking JSON-RPC 2.0. It
 *          implements the handshake (initialize), tool discovery (tools/list)
 *          and tool invocation (tools/call) by delegating to SoccerTools, and
 *          returns null for notifications (requests without an id). The stdio
 *          transport loop lives in Main; this class is pure request->response
 *          so it can be unit tested.
 * Part of: mcp package (protocol layer).
 * ============================================================================
 */
package com.example.brsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/** JSON-RPC 2.0 dispatcher implementing the subset of MCP we need. */
public final class McpServer {

    public static final String PROTOCOL_VERSION = "2024-11-05";
    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";

    private static final int METHOD_NOT_FOUND = -32601;
    private static final int INVALID_PARAMS = -32602;

    private final ObjectMapper mapper = new ObjectMapper();
    private final SoccerTools tools;

    public McpServer(SoccerTools tools) {
        this.tools = tools;
    }

    /**
     * Handle one parsed JSON-RPC request. Returns the response object, or null
     * for notifications (no {@code id}), which must not be answered.
     */
    public JsonNode handle(JsonNode request) {
        boolean isNotification = !request.hasNonNull("id");
        String method = request.path("method").asText("");

        if (isNotification) {
            return null; // notifications (e.g. notifications/initialized) get no reply
        }

        JsonNode id = request.get("id");
        return switch (method) {
            case "initialize" -> success(id, initializeResult());
            case "tools/list" -> success(id, toolsListResult());
            case "tools/call" -> handleToolCall(id, request.path("params"));
            case "ping" -> success(id, mapper.createObjectNode());
            default -> error(id, METHOD_NOT_FOUND, "Method not found: " + method);
        };
    }

    private ObjectNode initializeResult() {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode capabilities = mapper.createObjectNode();
        capabilities.set("tools", mapper.createObjectNode());
        result.set("capabilities", capabilities);
        ObjectNode serverInfo = mapper.createObjectNode();
        serverInfo.put("name", SERVER_NAME);
        serverInfo.put("version", SERVER_VERSION);
        result.set("serverInfo", serverInfo);
        result.put("instructions",
                "Query Brazilian soccer matches, teams, players and competitions using the provided tools.");
        return result;
    }

    private ObjectNode toolsListResult() {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode arr = result.putArray("tools");
        for (ToolDefinition def : tools.definitions()) {
            ObjectNode t = mapper.createObjectNode();
            t.put("name", def.name());
            t.put("description", def.description());
            t.set("inputSchema", def.inputSchema());
            arr.add(t);
        }
        return result;
    }

    private JsonNode handleToolCall(JsonNode id, JsonNode params) {
        String name = params.path("name").asText("");
        if (name.isEmpty()) {
            return error(id, INVALID_PARAMS, "Missing tool name");
        }
        JsonNode arguments = params.has("arguments") ? params.get("arguments")
                : mapper.createObjectNode();
        String text = tools.call(name, arguments);
        boolean isError = text.startsWith("Unknown tool:") || text.startsWith("Error handling tool");

        ObjectNode result = mapper.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode textNode = mapper.createObjectNode();
        textNode.put("type", "text");
        textNode.put("text", text);
        content.add(textNode);
        result.put("isError", isError);
        return success(id, result);
    }

    private ObjectNode success(JsonNode id, JsonNode result) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id);
        response.set("result", result);
        return response;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id);
        ObjectNode err = mapper.createObjectNode();
        err.put("code", code);
        err.put("message", message);
        response.set("error", err);
        return response;
    }
}
