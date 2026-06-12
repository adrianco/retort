/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    StdioTransport.java
 * Purpose: Newline-delimited JSON-RPC transport for the MCP server. Reads one
 *          JSON message per input line, dispatches it through McpServer and
 *          writes each response as a single JSON line. Blank lines are ignored,
 *          unparseable lines yield a JSON-RPC parse error, and notifications
 *          (no id) produce no output. Separated from Main so it is testable
 *          with in-memory readers/writers.
 * Part of: mcp package (transport layer).
 * ============================================================================
 */
package com.example.brsoccer.mcp;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Writer;

/** Drives an {@link McpServer} over a line-delimited JSON-RPC stream. */
public final class StdioTransport {

    private static final int PARSE_ERROR = -32700;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private StdioTransport() {
    }

    /** Read and answer requests until the input is exhausted. */
    public static void serve(McpServer server, BufferedReader in, Writer out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) {
                continue;
            }
            JsonNode request;
            try {
                request = MAPPER.readTree(trimmed);
            } catch (JsonProcessingException e) {
                writeLine(out, parseError(e.getOriginalMessage()));
                continue;
            }
            JsonNode response = server.handle(request);
            if (response != null) {
                writeLine(out, response);
            }
        }
    }

    private static void writeLine(Writer out, JsonNode node) throws IOException {
        out.write(MAPPER.writeValueAsString(node));
        out.write('\n');
        out.flush();
    }

    private static ObjectNode parseError(String detail) {
        ObjectNode response = MAPPER.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.putNull("id");
        ObjectNode err = MAPPER.createObjectNode();
        err.put("code", PARSE_ERROR);
        err.put("message", "Parse error: " + detail);
        response.set("error", err);
        return response;
    }
}
