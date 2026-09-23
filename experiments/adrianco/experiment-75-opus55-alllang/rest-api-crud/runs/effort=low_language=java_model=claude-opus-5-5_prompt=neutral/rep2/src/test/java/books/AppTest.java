package books;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;

import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class AppTest {
    static final ObjectMapper JSON = new ObjectMapper();
    static final HttpClient http = HttpClient.newHttpClient();
    App app;
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
        return http.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }
    Map<?, ?> map(String s) throws Exception { return JSON.readValue(s, Map.class); }

    @Test void health() throws Exception {
        var r = send("GET", "/health", null);
        assertEquals(200, r.statusCode());
        assertEquals("ok", map(r.body()).get("status"));
    }

    @Test void fullCrudLifecycle() throws Exception {
        var c = send("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"123\"}");
        assertEquals(201, c.statusCode());
        Object id = map(c.body()).get("id");
        assertEquals(200, send("GET", "/books/" + id, null).statusCode());
        var u = send("PUT", "/books/" + id, "{\"title\":\"Dune Messiah\",\"author\":\"Herbert\",\"year\":1969}");
        assertEquals(200, u.statusCode());
        assertEquals("Dune Messiah", map(u.body()).get("title"));
        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test void validationRequiresTitleAndAuthor() throws Exception {
        var r = send("POST", "/books", "{\"year\":2000}");
        assertEquals(400, r.statusCode());
        assertTrue(r.body().contains("title is required"));
        assertTrue(r.body().contains("author is required"));
        assertEquals(400, send("POST", "/books", "not json").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"x\",\"author\":\"y\",\"year\":\"abc\"}").statusCode());
    }

    @Test void listFiltersByAuthor() throws Exception {
        send("POST", "/books", "{\"title\":\"A\",\"author\":\"Le Guin\"}");
        send("POST", "/books", "{\"title\":\"B\",\"author\":\"Asimov\"}");
        assertEquals(2, JSON.readValue(send("GET", "/books", null).body(), List.class).size());
        List<?> f = JSON.readValue(send("GET", "/books?author=Le%20Guin", null).body(), List.class);
        assertEquals(1, f.size());
        assertEquals("A", ((Map<?, ?>) f.get(0)).get("title"));
    }

    @Test void unknownIdReturns404() throws Exception {
        assertEquals(404, send("GET", "/books/999", null).statusCode());
        assertEquals(404, send("PUT", "/books/999", "{\"title\":\"x\",\"author\":\"y\"}").statusCode());
    }
}
