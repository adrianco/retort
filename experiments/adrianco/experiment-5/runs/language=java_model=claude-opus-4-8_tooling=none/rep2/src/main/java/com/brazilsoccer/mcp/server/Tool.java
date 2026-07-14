/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    server/Tool.java
 * Purpose: Small descriptor binding an MCP tool's name, human description and
 *          JSON-Schema input contract to the handler that executes it. The
 *          handler receives the parsed "arguments" object and returns the text
 *          shown to the LLM/user.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.function.Function;

public record Tool(
        String name,
        String description,
        ObjectNode inputSchema,
        Function<JsonNode, String> handler) {
}
