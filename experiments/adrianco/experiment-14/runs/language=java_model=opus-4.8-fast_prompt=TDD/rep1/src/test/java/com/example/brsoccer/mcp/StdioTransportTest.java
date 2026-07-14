package com.example.brsoccer.mcp;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.query.SoccerDatabase;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.io.BufferedReader;
import java.io.StringReader;
import java.io.StringWriter;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class StdioTransportTest {

    private final ObjectMapper json = new ObjectMapper();

    private McpServer server() {
        List<Match> matches = List.of(new Match("Brasileirão", 2023,
                LocalDate.parse("2023-09-03"), "22", "Flamengo", "Fluminense", 2, 1));
        return new McpServer(new SoccerTools(new SoccerDatabase(matches, List.of())));
    }

    @Test
    void respondsToEachRequestLineAndSkipsNotifications() throws Exception {
        String input = String.join("\n",
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}",
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}",
                "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"find_matches\",\"arguments\":{\"team\":\"Flamengo\"}}}") + "\n";
        StringWriter out = new StringWriter();

        StdioTransport.serve(server(), new BufferedReader(new StringReader(input)), out);

        String[] lines = out.toString().strip().split("\\R");
        assertEquals(2, lines.length, "expected one response per request, notifications skipped");

        JsonNode first = json.readTree(lines[0]);
        assertEquals(1, first.get("id").asInt());
        assertTrue(first.get("result").has("serverInfo"));

        JsonNode second = json.readTree(lines[1]);
        assertEquals(2, second.get("id").asInt());
        assertTrue(second.get("result").get("content").get(0).get("text").asText()
                .contains("Flamengo 2-1 Fluminense"));
    }

    @Test
    void ignoresBlankLinesAndMalformedJson() throws Exception {
        String input = "\n   \nnot json\n{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"ping\"}\n";
        StringWriter out = new StringWriter();

        StdioTransport.serve(server(), new BufferedReader(new StringReader(input)), out);

        String[] lines = out.toString().strip().split("\\R");
        // one valid request -> one response; the parse-error line yields an error response
        assertTrue(lines.length >= 1);
        JsonNode last = json.readTree(lines[lines.length - 1]);
        assertEquals(5, last.get("id").asInt());
    }
}
