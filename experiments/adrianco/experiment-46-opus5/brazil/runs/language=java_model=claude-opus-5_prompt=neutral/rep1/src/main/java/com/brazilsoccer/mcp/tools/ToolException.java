package com.brazilsoccer.mcp.tools;

/**
 * Signals a problem the caller (an LLM) can fix: an unknown club, a malformed argument, a season
 * that is not in the dataset. The message is returned as an MCP tool error result rather than
 * crashing the server.
 */
public class ToolException extends RuntimeException {

    public ToolException(String message) {
        super(message);
    }
}
