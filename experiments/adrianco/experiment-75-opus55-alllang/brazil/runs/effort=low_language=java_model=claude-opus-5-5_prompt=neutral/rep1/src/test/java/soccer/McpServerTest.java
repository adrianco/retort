package soccer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class McpServerTest {
    McpServer server;
    final ObjectMapper json = new ObjectMapper();

    @BeforeAll void setup() throws Exception {
        server = new McpServer(new SoccerService(DataStore.load(Path.of("data/kaggle"))));
    }

    @Test void initializeAndListTools() {
        JsonNode init = server.handle("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\"}}");
        assertEquals("brazilian-soccer", init.path("result").path("serverInfo").path("name").asText());
        assertNull(server.handle("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
        JsonNode list = server.handle("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        assertTrue(list.path("result").path("tools").size() >= 15);
    }

    @Test void callToolReturnsText() {
        JsonNode r = server.handle("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"head_to_head\",\"arguments\":{\"team_a\":\"Grêmio\",\"team_b\":\"Internacional\"}}}");
        String text = r.path("result").path("content").get(0).path("text").asText();
        assertTrue(text.contains("Grenal"), text);
        assertFalse(r.path("result").path("isError").asBoolean());
    }

    @Test void errorsAreReported() {
        JsonNode r = server.handle("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"team_stats\",\"arguments\":{}}}");
        assertTrue(r.path("result").path("isError").asBoolean());
        assertEquals(-32601, server.handle("{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"bogus\"}").path("error").path("code").asInt());
        assertEquals(-32700, server.handle("not json").path("error").path("code").asInt());
    }

    @Test void stdioLoopEmitsOneResponsePerRequest() throws Exception {
        String in = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"champion\",\"arguments\":{\"season\":2019}}}\n";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        server.run(new ByteArrayInputStream(in.getBytes(StandardCharsets.UTF_8)), out);
        String[] lines = out.toString(StandardCharsets.UTF_8).trim().split("\n");
        assertEquals(2, lines.length);
        assertTrue(json.readTree(lines[1]).path("result").path("content").get(0).path("text").asText().contains("Flamengo"));
    }
}
