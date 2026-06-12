/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    ToolDefinition.java
 * Purpose: Describes one MCP tool: its name, human description and JSON-Schema
 *          for its input arguments. Used to answer the MCP "tools/list" request.
 * Part of: mcp package.
 * ============================================================================
 */
package com.example.brsoccer.mcp;

import com.fasterxml.jackson.databind.node.ObjectNode;

/** Metadata for a single callable MCP tool. */
public record ToolDefinition(String name, String description, ObjectNode inputSchema) {
}
