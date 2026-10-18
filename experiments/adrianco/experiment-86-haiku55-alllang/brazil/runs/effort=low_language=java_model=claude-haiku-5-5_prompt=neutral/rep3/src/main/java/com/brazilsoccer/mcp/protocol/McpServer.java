/*
 * Context block: Minimal Model Context Protocol server speaking JSON-RPC 2.0 over
 * newline-delimited stdio. Implements initialize, ping, tools/list and tools/call.
 * Notifications (messages without an id) get no response. Tool failures come back as
 * results with isError=true, as the MCP spec requires, rather than as protocol errors.
 */
package com.brazilsoccer.mcp.protocol;

import com.brazilsoccer.mcp.tools.SoccerTools;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Optional;

public final class McpServer {

    public static final String PROTOCOL_VERSION = "2025-06-18";
    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";

    static final int PARSE_ERROR = -32700;
    static final int INVALID_REQUEST = -32600;
    static final int METHOD_NOT_FOUND = -32601;
    static final int INVALID_PARAMS = -32602;

    private final SoccerTools tools;
    private final ObjectMapper mapper;

    public McpServer(SoccerTools tools, ObjectMapper mapper) {
        this.tools = tools;
        this.mapper = mapper;
    }

    /** Reads requests line by line until the input closes, writing one response line per request. */
    public void serve(BufferedReader in, PrintStream out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            Optional<String> response = handleLine(line);
            if (response.isPresent()) {
                out.println(response.get());
                out.flush();
            }
        }
    }

    /** Handles one raw JSON-RPC message. Returns empty for notifications. */
    public Optional<String> handleLine(String line) {
        JsonNode request;
        try {
            request = mapper.readTree(line);
        } catch (JsonProcessingException e) {
            return Optional.of(write(error(null, PARSE_ERROR, "Parse error: " + e.getOriginalMessage())));
        }
        return handle(request).map(this::write);
    }

    Optional<ObjectNode> handle(JsonNode request) {
        if (request == null || !request.isObject()) {
            return Optional.of(error(null, INVALID_REQUEST, "Request must be a JSON object"));
        }
        JsonNode id = request.get("id");
        boolean isNotification = id == null;
        JsonNode methodNode = request.get("method");
        if (methodNode == null || !methodNode.isTextual()) {
            return isNotification ? Optional.empty()
                    : Optional.of(error(id, INVALID_REQUEST, "Missing method"));
        }
        String method = methodNode.asText();
        JsonNode params = request.get("params");

        if (isNotification) {
            // notifications/initialized and other notifications require no reply
            return Optional.empty();
        }
        return switch (method) {
            case "initialize" -> Optional.of(result(id, initialize(params)));
            case "ping" -> Optional.of(result(id, mapper.createObjectNode()));
            case "tools/list" -> Optional.of(result(id, toolList()));
            case "tools/call" -> Optional.of(toolCall(id, params));
            default -> Optional.of(error(id, METHOD_NOT_FOUND, "Method not found: " + method));
        };
    }

    private ObjectNode initialize(JsonNode params) {
        ObjectNode result = mapper.createObjectNode();
        String requested = params == null ? null : params.path("protocolVersion").asText(null);
        result.put("protocolVersion", requested == null ? PROTOCOL_VERSION : requested);
        result.putObject("capabilities").putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        result.put("instructions", "Answers questions about Brazilian soccer: matches and results "
                + "(Brasileirão, Copa do Brasil, Libertadores), team records and head-to-head, league "
                + "standings, aggregate statistics, and FIFA player ratings.");
        return result;
    }

    private ObjectNode toolList() {
        ObjectNode result = mapper.createObjectNode();
        result.set("tools", tools.descriptors());
        return result;
    }

    private ObjectNode toolCall(JsonNode id, JsonNode params) {
        String name = params == null ? null : params.path("name").asText(null);
        if (name == null || !tools.has(name)) {
            return error(id, INVALID_PARAMS, "Unknown tool: " + name);
        }
        JsonNode args = params.get("arguments");
        ObjectNode result = mapper.createObjectNode();
        try {
            String text = tools.call(name, args);
            result.putArray("content").addObject().put("type", "text").put("text", text);
            result.put("isError", false);
        } catch (IllegalArgumentException e) {
            result.putArray("content").addObject().put("type", "text").put("text", "Error: " + e.getMessage());
            result.put("isError", true);
        } catch (RuntimeException e) {
            result.putArray("content").addObject().put("type", "text")
                    .put("text", "Internal error while running " + name + ": " + e);
            result.put("isError", true);
        }
        return result(id, result);
    }

    private ObjectNode result(JsonNode id, ObjectNode result) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id);
        response.set("result", result);
        return response;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        if (id == null) {
            response.putNull("id");
        } else {
            response.set("id", id);
        }
        ObjectNode err = response.putObject("error");
        err.put("code", code);
        err.put("message", message);
        return response;
    }

    private String write(ObjectNode node) {
        try {
            return mapper.writeValueAsString(node);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Could not serialise response", e);
        }
    }
}
