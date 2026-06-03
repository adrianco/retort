/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    server/McpServer.java
 * Purpose: Implements the Model Context Protocol over a JSON-RPC 2.0 / stdio
 *          transport (newline-delimited JSON messages, as used by MCP stdio
 *          clients). Handles the protocol handshake (initialize / initialized),
 *          tool discovery (tools/list) and tool invocation (tools/call),
 *          delegating tool execution to SoccerTools. Kept transport-focused so
 *          it can be unit tested by feeding request strings through
 *          {@link #handle(String)}.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.server;

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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class McpServer {

    public static final String PROTOCOL_VERSION = "2024-11-05";
    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";

    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, Tool> tools = new LinkedHashMap<>();

    public McpServer(List<Tool> toolList) {
        for (Tool t : toolList) {
            tools.put(t.name(), t);
        }
    }

    /** Run the stdio read/respond loop until end-of-input. */
    public void serve(InputStream in, OutputStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        PrintStream writer = new PrintStream(out, true, StandardCharsets.UTF_8);
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            String response = handle(line);
            if (response != null) {
                writer.println(response);
            }
        }
    }

    /**
     * Process one JSON-RPC request line and return the serialized response, or
     * null when the message is a notification that requires no reply.
     */
    public String handle(String requestLine) {
        JsonNode req;
        try {
            req = mapper.readTree(requestLine);
        } catch (IOException e) {
            return error(null, -32700, "Parse error: " + e.getMessage());
        }

        JsonNode idNode = req.get("id");
        String method = req.path("method").asText("");
        JsonNode params = req.get("params");

        try {
            switch (method) {
                case "initialize":
                    return result(idNode, initializeResult());
                case "notifications/initialized":
                case "initialized":
                    return null; // notification, no response
                case "ping":
                    return result(idNode, mapper.createObjectNode());
                case "tools/list":
                    return result(idNode, toolsListResult());
                case "tools/call":
                    return result(idNode, callTool(params));
                default:
                    if (idNode == null) {
                        return null; // unknown notification
                    }
                    return error(idNode, -32601, "Method not found: " + method);
            }
        } catch (ToolException te) {
            return result(idNode, errorContent(te.getMessage()));
        } catch (Exception e) {
            return error(idNode, -32603, "Internal error: " + e.getMessage());
        }
    }

    private ObjectNode initializeResult() {
        ObjectNode r = mapper.createObjectNode();
        r.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = mapper.createObjectNode();
        caps.set("tools", mapper.createObjectNode());
        r.set("capabilities", caps);
        ObjectNode info = mapper.createObjectNode();
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        r.set("serverInfo", info);
        r.put("instructions",
                "Tools for querying Brazilian soccer match and player datasets. "
                        + "Use search_matches, matches_between, head_to_head, team_stats, "
                        + "standings, search_players, find_players, average_goals, "
                        + "biggest_wins and list_competitions.");
        return r;
    }

    private ObjectNode toolsListResult() {
        ObjectNode r = mapper.createObjectNode();
        ArrayNode arr = mapper.createArrayNode();
        for (Tool t : tools.values()) {
            ObjectNode tn = mapper.createObjectNode();
            tn.put("name", t.name());
            tn.put("description", t.description());
            tn.set("inputSchema", t.inputSchema());
            arr.add(tn);
        }
        r.set("tools", arr);
        return r;
    }

    private ObjectNode callTool(JsonNode params) {
        if (params == null || !params.hasNonNull("name")) {
            throw new ToolException("Missing tool name");
        }
        String name = params.get("name").asText();
        Tool tool = tools.get(name);
        if (tool == null) {
            throw new ToolException("Unknown tool: " + name);
        }
        JsonNode arguments = params.get("arguments");
        if (arguments == null || arguments.isNull()) {
            arguments = mapper.createObjectNode();
        }
        String text;
        try {
            text = tool.handler().apply(arguments);
        } catch (Exception e) {
            throw new ToolException("Tool '" + name + "' failed: " + e.getMessage());
        }
        return textContent(text, false);
    }

    // ---- response envelope helpers ----------------------------------------

    private ObjectNode textContent(String text, boolean isError) {
        ObjectNode r = mapper.createObjectNode();
        ArrayNode content = mapper.createArrayNode();
        ObjectNode item = mapper.createObjectNode();
        item.put("type", "text");
        item.put("text", text);
        content.add(item);
        r.set("content", content);
        r.put("isError", isError);
        return r;
    }

    private ObjectNode errorContent(String message) {
        return textContent(message, true);
    }

    private String result(JsonNode id, ObjectNode resultNode) {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        resp.set("id", id == null ? null : id);
        resp.set("result", resultNode);
        return write(resp);
    }

    private String error(JsonNode id, int code, String message) {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        resp.set("id", id == null ? null : id);
        ObjectNode err = mapper.createObjectNode();
        err.put("code", code);
        err.put("message", message);
        resp.set("error", err);
        return write(resp);
    }

    private String write(ObjectNode node) {
        try {
            return mapper.writeValueAsString(node);
        } catch (Exception e) {
            return "{\"jsonrpc\":\"2.0\",\"id\":null,"
                    + "\"error\":{\"code\":-32603,\"message\":\"serialization failure\"}}";
        }
    }

    /** Signals a tool-level failure that should be reported as tool result text. */
    private static final class ToolException extends RuntimeException {
        ToolException(String message) {
            super(message);
        }
    }
}
