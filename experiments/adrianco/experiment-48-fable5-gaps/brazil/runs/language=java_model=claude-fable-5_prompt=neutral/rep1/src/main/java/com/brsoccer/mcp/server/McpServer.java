package com.brsoccer.mcp.server;

import com.brsoccer.mcp.tools.McpTools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;

/**
 * Minimal MCP (Model Context Protocol) server over the stdio transport:
 * newline-delimited JSON-RPC 2.0 messages on stdin/stdout.
 *
 * Supported methods: initialize, notifications/*, ping, tools/list, tools/call,
 * resources/list, prompts/list.
 */
public class McpServer {

    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";
    public static final String PROTOCOL_VERSION = "2024-11-05";

    private final ObjectMapper om = new ObjectMapper();
    private final McpTools tools;
    private final BufferedReader in;
    private final Writer out;

    public McpServer(McpTools tools, InputStream in, OutputStream out) {
        this.tools = tools;
        this.in = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        this.out = new BufferedWriter(new OutputStreamWriter(out, StandardCharsets.UTF_8));
    }

    public void run() throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) continue;
            handleLine(line);
        }
    }

    void handleLine(String line) throws IOException {
        JsonNode msg;
        try {
            msg = om.readTree(line);
        } catch (Exception e) {
            send(error(om.nullNode(), -32700, "Parse error: " + e.getMessage()));
            return;
        }
        if (!msg.isObject()) {
            send(error(om.nullNode(), -32600, "Invalid request: expected a JSON object"));
            return;
        }
        JsonNode id = msg.get("id");
        boolean isNotification = id == null || id.isNull();
        String method = msg.path("method").asText(null);
        JsonNode params = msg.get("params");
        if (method == null) {
            if (!isNotification) send(error(id, -32600, "Invalid request: missing method"));
            return;
        }
        if (method.startsWith("notifications/")) return;

        try {
            switch (method) {
                case "initialize" -> send(result(id, initialize(params)));
                case "ping" -> send(result(id, om.createObjectNode()));
                case "tools/list" -> {
                    ObjectNode r = om.createObjectNode();
                    r.set("tools", tools.toolList());
                    send(result(id, r));
                }
                case "tools/call" -> send(toolsCall(id, params));
                case "resources/list" -> {
                    ObjectNode r = om.createObjectNode();
                    r.putArray("resources");
                    send(result(id, r));
                }
                case "prompts/list" -> {
                    ObjectNode r = om.createObjectNode();
                    r.putArray("prompts");
                    send(result(id, r));
                }
                default -> {
                    if (!isNotification) send(error(id, -32601, "Method not found: " + method));
                }
            }
        } catch (Exception e) {
            if (!isNotification) send(error(id, -32603, "Internal error: " + e.getMessage()));
        }
    }

    private ObjectNode initialize(JsonNode params) {
        ObjectNode r = om.createObjectNode();
        String requested = params == null ? null : params.path("protocolVersion").asText(null);
        r.put("protocolVersion", requested == null ? PROTOCOL_VERSION : requested);
        ObjectNode caps = r.putObject("capabilities");
        caps.putObject("tools");
        ObjectNode info = r.putObject("serverInfo");
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        return r;
    }

    private ObjectNode toolsCall(JsonNode id, JsonNode params) {
        String name = params == null ? null : params.path("name").asText(null);
        if (name == null) return error(id, -32602, "Missing tool name");
        JsonNode args = params.get("arguments");
        ObjectNode r = om.createObjectNode();
        try {
            String text = tools.call(name, args);
            r.set("content", textContent(text));
            r.put("isError", false);
        } catch (IllegalArgumentException e) {
            if (e.getMessage() != null && e.getMessage().startsWith("Unknown tool")) {
                return error(id, -32602, e.getMessage());
            }
            r.set("content", textContent("Error: " + e.getMessage()));
            r.put("isError", true);
        } catch (Exception e) {
            r.set("content", textContent("Error: " + e));
            r.put("isError", true);
        }
        return result(id, r);
    }

    private JsonNode textContent(String text) {
        ObjectNode item = om.createObjectNode();
        item.put("type", "text");
        item.put("text", text);
        return om.createArrayNode().add(item);
    }

    private ObjectNode result(JsonNode id, JsonNode result) {
        ObjectNode r = om.createObjectNode();
        r.put("jsonrpc", "2.0");
        r.set("id", id);
        r.set("result", result);
        return r;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode r = om.createObjectNode();
        r.put("jsonrpc", "2.0");
        r.set("id", id == null ? om.nullNode() : id);
        ObjectNode e = r.putObject("error");
        e.put("code", code);
        e.put("message", message);
        return r;
    }

    private void send(ObjectNode msg) throws IOException {
        out.write(om.writeValueAsString(msg));
        out.write('\n');
        out.flush();
    }
}
