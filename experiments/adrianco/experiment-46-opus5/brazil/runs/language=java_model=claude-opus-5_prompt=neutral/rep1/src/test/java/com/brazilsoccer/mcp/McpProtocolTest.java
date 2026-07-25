package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.support.TestFixtures;
import io.modelcontextprotocol.json.McpJsonDefaults;
import io.modelcontextprotocol.json.McpJsonMapper;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.spec.ProtocolVersions;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.Timeout;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PipedInputStream;
import java.io.PipedOutputStream;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * End-to-end test of the MCP layer.
 *
 * <p>The server is started on a pair of in-memory pipes and driven with hand written JSON-RPC
 * messages, exactly like an MCP client would over stdio: {@code initialize},
 * {@code notifications/initialized}, {@code tools/list} and {@code tools/call}.
 */
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@Timeout(value = 60, unit = TimeUnit.SECONDS)
class McpProtocolTest {

    private static final McpJsonMapper JSON = McpJsonDefaults.getMapper();

    private McpSyncServer server;
    private Writer toServer;
    private BufferedReader fromServer;
    private final AtomicInteger requestId = new AtomicInteger();

    @BeforeAll
    void startServer() throws Exception {
        PipedOutputStream clientOut = new PipedOutputStream();
        PipedInputStream serverIn = new PipedInputStream(clientOut, 1 << 16);
        PipedOutputStream serverOut = new PipedOutputStream();
        PipedInputStream clientIn = new PipedInputStream(serverOut, 1 << 20);

        server = McpServerFactory.createStdio(TestFixtures.registry(), serverIn, serverOut);
        toServer = new OutputStreamWriter(clientOut, StandardCharsets.UTF_8);
        fromServer = new BufferedReader(new InputStreamReader(clientIn, StandardCharsets.UTF_8));

        Map<String, Object> initialize = request("initialize", Map.of(
                "protocolVersion", ProtocolVersions.MCP_2024_11_05,
                "capabilities", Map.of(),
                "clientInfo", Map.of("name", "junit-client", "version", "1.0.0")));
        assertThat(initialize).containsKey("result");
        notification("notifications/initialized", Map.of());
    }

    @AfterAll
    void stopServer() {
        if (server != null) {
            server.closeGracefully();
        }
    }

    @Test
    @DisplayName("initialize advertises the server, its tools capability and usage instructions")
    void initializeHandshake() throws Exception {
        Map<String, Object> response = request("initialize", Map.of(
                "protocolVersion", ProtocolVersions.MCP_2024_11_05,
                "capabilities", Map.of(),
                "clientInfo", Map.of("name", "junit-client", "version", "1.0.0")));

        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) response.get("result");
        @SuppressWarnings("unchecked")
        Map<String, Object> serverInfo = (Map<String, Object>) result.get("serverInfo");
        assertThat(serverInfo.get("name")).isEqualTo("brazilian-soccer-mcp");
        assertThat(result.get("capabilities").toString()).contains("tools");
        assertThat(result.get("instructions").toString()).contains("Brasileirão");
    }

    @Test
    @DisplayName("tools/list returns every tool with a JSON schema")
    void listsTools() throws Exception {
        Map<String, Object> response = request("tools/list", Map.of());

        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) response.get("result");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> tools = (List<Map<String, Object>>) result.get("tools");

        assertThat(tools).hasSize(TestFixtures.registry().tools().size());
        assertThat(tools).extracting(tool -> tool.get("name"))
                .contains("search_matches", "head_to_head", "team_stats", "standings",
                        "search_players", "player_profile", "statistics", "dataset_info");
        assertThat(tools).allSatisfy(tool -> {
            assertThat(tool.get("description").toString()).isNotBlank();
            assertThat(tool.get("inputSchema")).isInstanceOf(Map.class);
        });
    }

    @Test
    @DisplayName("tools/call answers a real question over the protocol")
    void callsToolOverProtocol() throws Exception {
        Map<String, Object> response = request("tools/call", Map.of(
                "name", "head_to_head",
                "arguments", Map.of("team_a", "Flamengo", "team_b", "Fluminense", "limit", 3)));

        assertThat(textOf(response)).contains("Fla-Flu").contains("Head-to-head in dataset");
    }

    @Test
    @DisplayName("a bad argument comes back as an MCP error result, the session stays alive")
    void reportsToolErrors() throws Exception {
        Map<String, Object> response = request("tools/call", Map.of(
                "name", "team_stats",
                "arguments", Map.of("team", "Not A Real Club At All")));

        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) response.get("result");
        assertThat(result.get("isError")).isEqualTo(Boolean.TRUE);
        assertThat(textOf(response)).contains("No club matching");

        // The session still works afterwards.
        assertThat(textOf(request("tools/call", Map.of(
                "name", "dataset_info", "arguments", Map.of())))).contains("knowledge graph");
    }

    @Test
    @DisplayName("unicode club names survive the JSON-RPC round trip")
    void keepsUtf8OverTheWire() throws Exception {
        Map<String, Object> response = request("tools/call", Map.of(
                "name", "team_stats",
                "arguments", Map.of("team", "São Paulo", "season", 2019, "competition", "serie_a")));

        assertThat(textOf(response)).contains("São Paulo");
    }

    private String textOf(Map<String, Object> response) {
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) response.get("result");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> content = (List<Map<String, Object>>) result.get("content");
        return content.get(0).get("text").toString();
    }

    private Map<String, Object> request(String method, Map<String, Object> params) throws IOException {
        int id = requestId.incrementAndGet();
        send(Map.of("jsonrpc", "2.0", "id", id, "method", method, "params", params));
        while (true) {
            String line = fromServer.readLine();
            if (line == null) {
                throw new IOException("server closed the connection while waiting for " + method);
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> message = JSON.readValue(line, Map.class);
            if (message.containsKey("id") && ((Number) message.get("id")).intValue() == id) {
                return message;
            }
        }
    }

    private void notification(String method, Map<String, Object> params) throws IOException {
        send(Map.of("jsonrpc", "2.0", "method", method, "params", params));
    }

    private void send(Map<String, Object> message) throws IOException {
        toServer.write(JSON.writeValueAsString(message));
        toServer.write("\n");
        toServer.flush();
    }
}
