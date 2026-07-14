/*
 * ============================================================================
 * ToolSchemas - JSON Schema definitions for the MCP tools
 * ============================================================================
 * Context:
 *   Builds the tool descriptors returned by `tools/list`. Each tool advertises a
 *   name, a natural-language description (so the LLM knows when to call it) and a
 *   JSON Schema for its arguments. Kept apart from McpServer to keep the protocol
 *   logic readable.
 * ============================================================================
 */
package com.brasilsoccer.mcp.mcp;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

final class ToolSchemas {

    private ToolSchemas() {
    }

    static ObjectNode searchMatches(ObjectMapper m) {
        ObjectNode tool = tool(m, "search_matches",
                "Search Brazilian soccer matches by team, opponent, competition, season or date "
                        + "range. Returns matches with date, score and competition. If both 'team' "
                        + "and 'opponent' are given, also returns a head-to-head summary.");
        ObjectNode props = props(tool);
        addString(props, "team", "Team name (matches home or away), e.g. 'Flamengo'.");
        addString(props, "opponent", "Restrict to matches against this second team.");
        addString(props, "competition",
                "Competition filter, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores'.");
        addInteger(props, "season", "Season year, e.g. 2019.");
        addString(props, "start_date", "Earliest match date, ISO format YYYY-MM-DD.");
        addString(props, "end_date", "Latest match date, ISO format YYYY-MM-DD.");
        addEnum(m, props, "venue", "Restrict a single-team search to home or away games.",
                "any", "home", "away");
        addInteger(props, "limit", "Maximum matches to return (default 50).");
        return tool;
    }

    static ObjectNode headToHead(ObjectMapper m) {
        ObjectNode tool = tool(m, "head_to_head",
                "Aggregate head-to-head record between two teams: wins, draws and goals.");
        ObjectNode props = props(tool);
        addString(props, "team1", "First team name.");
        addString(props, "team2", "Second team name.");
        require(tool, "team1", "team2");
        return tool;
    }

    static ObjectNode teamRecord(ObjectMapper m) {
        ObjectNode tool = tool(m, "team_record",
                "A team's win/loss/draw record and goals, optionally filtered by season, "
                        + "competition and venue (home/away).");
        ObjectNode props = props(tool);
        addString(props, "team", "Team name, e.g. 'Corinthians'.");
        addInteger(props, "season", "Season year filter, e.g. 2022.");
        addString(props, "competition", "Competition filter, e.g. 'Brasileirao'.");
        addEnum(m, props, "venue", "Limit to home or away matches.", "any", "home", "away");
        require(tool, "team");
        return tool;
    }

    static ObjectNode searchPlayers(ObjectMapper m) {
        ObjectNode tool = tool(m, "search_players",
                "Search FIFA players by name, nationality, club, position or minimum rating. "
                        + "Useful for 'Brazilian players', 'players at Flamengo', etc.");
        ObjectNode props = props(tool);
        addString(props, "name", "Full or partial player name.");
        addString(props, "nationality", "Nationality, e.g. 'Brazil'.");
        addString(props, "club", "Club name, e.g. 'Flamengo'.");
        addString(props, "position", "Position code, e.g. 'GK', 'ST', 'CB'.");
        addInteger(props, "min_overall", "Minimum FIFA overall rating.");
        addEnum(m, props, "sort_by", "Sort order (default overall).",
                "overall", "potential", "age", "name");
        addInteger(props, "limit", "Maximum players to return (default 20).");
        return tool;
    }

    static ObjectNode standings(ObjectMapper m) {
        ObjectNode tool = tool(m, "standings",
                "Calculate the final league table for a competition and season from match "
                        + "results (points, W/D/L, goals). Best for Brasileirao Serie A/B/C.");
        ObjectNode props = props(tool);
        addString(props, "competition", "Competition, e.g. 'Brasileirao' (default), 'Serie B'.");
        addInteger(props, "season", "Season year, e.g. 2019.");
        require(tool, "season");
        return tool;
    }

    static ObjectNode leagueStatistics(ObjectMapper m) {
        ObjectNode tool = tool(m, "league_statistics",
                "Aggregate statistics over matches: average goals per match, home/away win "
                        + "rates and draw rate. Optionally filtered by competition and season.");
        ObjectNode props = props(tool);
        addString(props, "competition", "Competition filter (optional).");
        addInteger(props, "season", "Season year filter (optional).");
        return tool;
    }

    static ObjectNode biggestWins(ObjectMapper m) {
        ObjectNode tool = tool(m, "biggest_wins",
                "List the biggest victories (largest goal margins), optionally filtered by "
                        + "competition and season.");
        ObjectNode props = props(tool);
        addString(props, "competition", "Competition filter (optional).");
        addInteger(props, "season", "Season year filter (optional).");
        addInteger(props, "limit", "How many to return (default 10).");
        return tool;
    }

    static ObjectNode dataSummary(ObjectMapper m) {
        ObjectNode tool = tool(m, "data_summary",
                "Overview of the loaded data: match and player counts, competitions and "
                        + "season range.");
        props(tool); // no arguments
        return tool;
    }

    // ----------------------------------------------------------------- builders

    private static ObjectNode tool(ObjectMapper m, String name, String description) {
        ObjectNode tool = m.createObjectNode();
        tool.put("name", name);
        tool.put("description", description);
        ObjectNode schema = tool.putObject("inputSchema");
        schema.put("type", "object");
        schema.putObject("properties");
        return tool;
    }

    private static ObjectNode props(ObjectNode tool) {
        return (ObjectNode) tool.get("inputSchema").get("properties");
    }

    private static void addString(ObjectNode props, String name, String desc) {
        ObjectNode p = props.putObject(name);
        p.put("type", "string");
        p.put("description", desc);
    }

    private static void addInteger(ObjectNode props, String name, String desc) {
        ObjectNode p = props.putObject(name);
        p.put("type", "integer");
        p.put("description", desc);
    }

    private static void addEnum(ObjectMapper m, ObjectNode props, String name, String desc,
                                String... values) {
        ObjectNode p = props.putObject(name);
        p.put("type", "string");
        p.put("description", desc);
        ArrayNode en = p.putArray("enum");
        for (String v : values) {
            en.add(v);
        }
    }

    private static void require(ObjectNode tool, String... names) {
        ObjectNode schema = (ObjectNode) tool.get("inputSchema");
        ArrayNode req = schema.putArray("required");
        for (String n : names) {
            req.add(n);
        }
    }
}
