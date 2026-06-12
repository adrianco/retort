package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.nio.file.Path;
import java.util.Map;

/**
 * A thin client that exercises the {@link McpServer} ONLY through the public MCP
 * JSON-RPC protocol (initialize / tools/list / tools/call). It has no access to
 * the server internals or the underlying data model — exactly how a real MCP
 * client (an LLM host) would talk to the server.
 */
final class McpTestClient {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Path DATA_DIR = Path.of("data", "kaggle");

    private final McpServer server;
    private int nextId = 1;

    private McpTestClient(McpServer server) {
        this.server = server;
    }

    /** Boots a fresh, fully-loaded server and performs the MCP handshake. */
    static McpTestClient bootAndInitialize() {
        McpServer server = new McpServer(SoccerService.load(DATA_DIR));
        McpTestClient client = new McpTestClient(server);
        client.initialize();
        return client;
    }

    JsonNode initialize() {
        ObjectNode params = MAPPER.createObjectNode();
        params.put("protocolVersion", "2024-11-05");
        params.set("capabilities", MAPPER.createObjectNode());
        return request("initialize", params).get("result");
    }

    JsonNode listTools() {
        return request("tools/list", MAPPER.createObjectNode()).get("result");
    }

    /** Calls a tool and returns the parsed JSON payload the tool produced. */
    JsonNode callTool(String name, Map<String, Object> arguments) {
        JsonNode response = rawToolCall(name, arguments);
        JsonNode result = response.get("result");
        if (result == null) {
            throw new AssertionError("tool call returned an error: " + response.toPrettyString());
        }
        String text = result.get("content").get(0).get("text").asText();
        try {
            return MAPPER.readTree(text);
        } catch (Exception e) {
            throw new RuntimeException("tool text was not valid JSON: " + text, e);
        }
    }

    /** Calls a tool returning the raw JSON-RPC envelope (used to assert on errors). */
    JsonNode rawToolCall(String name, Map<String, Object> arguments) {
        ObjectNode params = MAPPER.createObjectNode();
        params.put("name", name);
        params.set("arguments", MAPPER.valueToTree(arguments));
        return request("tools/call", params);
    }

    private JsonNode request(String method, JsonNode params) {
        ObjectNode req = MAPPER.createObjectNode();
        req.put("jsonrpc", "2.0");
        req.put("id", nextId++);
        req.put("method", method);
        req.set("params", params);
        try {
            String out = server.handle(MAPPER.writeValueAsString(req));
            return MAPPER.readTree(out);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
