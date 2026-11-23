import com.sun.net.httpserver.Headers;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.net.URI;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

class BookApiTest {
    @TempDir Path dir;
    String url;
    String original = "{\"title\":\"Dawn\",\"author\":\"O. Butler\",\"year\":1987,\"isbn\":\"0123\"}";

    @BeforeEach void start() throws Exception {
        url = BookApi.initialize(dir.resolve("books.db").toString());
    }

    record Response(int statusCode, String body, Headers headers) {}

    Response call(String method, String path, String json) throws Exception {
        Headers headers = new Headers();
        byte[] input = (json == null ? "" : json).getBytes(StandardCharsets.UTF_8);
        var reply = BookApi.handle(url, method, URI.create(path), new ByteArrayInputStream(input), headers);
        return new Response(reply.status(), BookApi.JSON.writeValueAsString(reply.body()), headers);
    }
    @Test void lifecycle() throws Exception {
        var created = call("POST", "/books", original);
        assertEquals(201, created.statusCode());
        String path = created.headers().getFirst("Location");
        start();
        var stored = BookApi.JSON.readTree(call("GET", path, null).body());
        assertEquals("0123", stored.get("isbn").asText());
        assertEquals(1987, stored.get("year").asInt());
        var updated = call("PUT", path, "{\"title\":\"Kindred\",\"author\":\"Butler\"}");
        assertEquals(200, updated.statusCode());
        assertEquals("Kindred", BookApi.JSON.readTree(call("GET", path, null).body()).get("title").asText());
        assertEquals(204, call("DELETE", path, null).statusCode());
        assertEquals(404, call("GET", path, null).statusCode());
    }
    @Test void listsAndFilters() throws Exception {
        call("POST", "/books", original);
        call("POST", "/books", original.replace("O. Butler", "Other"));
        assertEquals(2, BookApi.JSON.readTree(call("GET", "/books", null).body()).size());
        var list = BookApi.JSON.readTree(call("GET", "/books?author=O.%20Butler", null).body());
        assertEquals(1, list.size());
        assertEquals("O. Butler", list.get(0).get("author").asText());
    }
    @Test void rejectsInvalidInput() throws Exception {
        for (String invalid : new String[]{"{", "{}", original.replace("Dawn", " "), original.replace("1987", "false"), "{\"title\":\"Dawn\"}"})
            assertEquals(400, call("POST", "/books", invalid).statusCode());
        assertEquals("[]", call("GET", "/books", null).body());
    }
    @Test void healthAndMissingResources() throws Exception {
        assertEquals(200, call("GET", "/health", null).statusCode());
        assertEquals(404, call("DELETE", "/books/42", null).statusCode());
        assertEquals(404, call("PUT", "/books/42", original).statusCode());
        assertEquals(405, call("POST", "/health", original).statusCode());
    }
}
