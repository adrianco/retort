package books;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import org.junit.jupiter.api.*;

class AppTest {
    static final ObjectMapper M = new ObjectMapper();
    App app;
    HttpClient client = HttpClient.newHttpClient();
    Path db;

    @BeforeEach void up() throws Exception {
        db = Files.createTempFile("books", ".db");
        app = new App(0, "jdbc:sqlite:" + db);
        app.start();
    }

    @AfterEach void down() throws Exception { app.stop(); Files.deleteIfExists(db); }

    HttpResponse<String> send(String method, String path, String body) throws Exception {
        var b = HttpRequest.newBuilder(URI.create("http://localhost:" + app.port() + path))
                .header("Content-Type", "application/json")
                .method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body));
        return client.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    @Test void health() throws Exception {
        var r = send("GET", "/health", null);
        assertEquals(200, r.statusCode());
        assertEquals("ok", M.readTree(r.body()).get("status").asText());
    }

    @Test void crudLifecycle() throws Exception {
        var r = send("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"123\"}");
        assertEquals(201, r.statusCode());
        long id = M.readTree(r.body()).get("id").asLong();

        r = send("GET", "/books/" + id, null);
        assertEquals(200, r.statusCode());
        assertEquals("Dune", M.readTree(r.body()).get("title").asText());
        assertEquals(1965, M.readTree(r.body()).get("year").asInt());

        r = send("PUT", "/books/" + id, "{\"title\":\"Dune Messiah\",\"author\":\"Herbert\",\"year\":1969}");
        assertEquals(200, r.statusCode());
        assertEquals("Dune Messiah", M.readTree(send("GET", "/books/" + id, null).body()).get("title").asText());

        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("PUT", "/books/" + id, "{\"title\":\"x\",\"author\":\"y\"}").statusCode());
    }

    @Test void validation() throws Exception {
        var r = send("POST", "/books", "{\"author\":\"Someone\"}");
        assertEquals(400, r.statusCode());
        assertTrue(r.body().contains("title is required"));
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"  \"}").statusCode());
        assertEquals(400, send("POST", "/books", "not json").statusCode());
    }

    @Test void listWithAuthorFilter() throws Exception {
        send("POST", "/books", "{\"title\":\"A\",\"author\":\"Le Guin\"}");
        send("POST", "/books", "{\"title\":\"B\",\"author\":\"Asimov\"}");
        send("POST", "/books", "{\"title\":\"C\",\"author\":\"Le Guin\"}");
        JsonNode all = M.readTree(send("GET", "/books", null).body());
        assertEquals(3, all.size());
        JsonNode filtered = M.readTree(send("GET", "/books?author=Le%20Guin", null).body());
        assertEquals(2, filtered.size());
        filtered.forEach(b -> assertEquals("Le Guin", b.get("author").asText()));
    }
}
