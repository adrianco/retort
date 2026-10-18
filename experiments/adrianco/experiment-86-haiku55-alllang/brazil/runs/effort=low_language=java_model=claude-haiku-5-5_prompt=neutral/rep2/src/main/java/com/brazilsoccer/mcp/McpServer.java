package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintStream;

/**
 * Minimal MCP server over newline-delimited JSON-RPC 2.0 on stdio. Implements the lifecycle
 * ({@code initialize}, {@code notifications/initialized}), {@code ping}, {@code tools/list} and
 * {@code tools/call}.
 */
public final class McpServer {

    static final String PROTOCOL_VERSION = "2024-11-05";
    static final String SERVER_NAME = "brazilian-soccer-mcp";
    static final String SERVER_VERSION = "1.0.0";

    static final int METHOD_NOT_FOUND = -32601;
    static final int INVALID_PARAMS = -32602;

    private final SoccerTools tools;
    private final ObjectMapper mapper;

    public McpServer(SoccerTools tools, ObjectMapper mapper) {
        this.tools = tools;
        this.mapper = mapper;
    }

    /** Reads requests line by line until input ends, writing one response line per request. */
    public void serve(BufferedReader in, PrintStream out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            JsonNode response = handleLine(line);
            if (response != null) {
                out.println(mapper.writeValueAsString(response));
                out.flush();
            }
        }
    }

    /** Handles one raw JSON-RPC message. Returns null for notifications, which get no reply. */
    public JsonNode handleLine(String line) {
        JsonNode request;
        try {
            request = mapper.readTree(line);
        } catch (IOException e) {
            return error(null, -32700, "Parse error: " + e.getMessage());
        }
        return handle(request);
    }

    /** Handles a parsed JSON-RPC request or notification. */
    public JsonNode handle(JsonNode request) {
        JsonNode id = request.get("id");
        if (id == null) {
            return null;
        }
        String method = request.path("method").asText("");
        JsonNode params = request.path("params");
        try {
            return switch (method) {
                case "initialize" -> result(id, initializeResult());
                case "ping" -> result(id, mapper.createObjectNode());
                case "tools/list" -> {
                    ObjectNode body = mapper.createObjectNode();
                    body.set("tools", tools.definitions());
                    yield result(id, body);
                }
                case "tools/call" -> result(id, callTool(params));
                default -> error(id, METHOD_NOT_FOUND, "Method not found: " + method);
            };
        } catch (IllegalArgumentException e) {
            return error(id, INVALID_PARAMS, e.getMessage());
        }
    }

    private ObjectNode initializeResult() {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        result.putObject("capabilities").putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        return result;
    }

    private ObjectNode callTool(JsonNode params) {
        String name = params.path("name").asText("");
        JsonNode args = params.path("arguments");
        if (args.isMissingNode() || args.isNull()) {
            args = mapper.createObjectNode();
        }
        ObjectNode result = mapper.createObjectNode();
        try {
            String text = tools.call(name, args);
            result.putArray("content").addObject().put("type", "text").put("text", text);
        } catch (RuntimeException e) {
            String message = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
            result.putArray("content").addObject().put("type", "text").put("text", "Error: " + message);
            result.put("isError", true);
        }
        return result;
    }

    private ObjectNode result(JsonNode id, JsonNode result) {
        ObjectNode response = envelope(id);
        response.set("result", result);
        return response;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode response = envelope(id);
        ObjectNode err = response.putObject("error");
        err.put("code", code);
        err.put("message", message);
        return response;
    }

    private ObjectNode envelope(JsonNode id) {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        if (id == null) {
            response.putNull("id");
        } else {
            response.set("id", id);
        }
        return response;
    }
}
