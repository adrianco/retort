package books;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;

import java.net.URI;
import java.net.http.*;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class BookServerTest {
    static final ObjectMapper JSON = new ObjectMapper();
    final HttpClient client = HttpClient.newHttpClient();
    BookServer server;

    @BeforeEach void start() throws Exception {
        server = new BookServer(0, "jdbc:sqlite::memory:");
        server.start();
    }
    @AfterEach void stop() throws Exception { server.stop(); }

    HttpResponse<String> req(String method, String path, String body) throws Exception {
        var b = HttpRequest.newBuilder(URI.create("http://localhost:" + server.port() + path))
                .header("Content-Type", "application/json")
                .method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body));
        return client.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    @SuppressWarnings("unchecked")
    Map<String, Object> map(HttpResponse<String> r) throws Exception { return JSON.readValue(r.body(), Map.class); }

    @Test void health() throws Exception {
        var r = req("GET", "/health", null);
        assertEquals(200, r.statusCode());
        assertEquals("ok", map(r).get("status"));
    }

    @Test void crudLifecycle() throws Exception {
        var c = req("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441013593\"}");
        assertEquals(201, c.statusCode());
        int id = ((Number) map(c).get("id")).intValue();

        var g = req("GET", "/books/" + id, null);
        assertEquals(200, g.statusCode());
        assertEquals("Dune", map(g).get("title"));
        assertEquals(1965, map(g).get("year"));

        var u = req("PUT", "/books/" + id, "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969}");
        assertEquals(200, u.statusCode());
        assertEquals("Dune Messiah", map(u).get("title"));

        assertEquals(204, req("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, req("GET", "/books/" + id, null).statusCode());
        assertEquals(404, req("DELETE", "/books/" + id, null).statusCode());
    }

    @Test void validation() throws Exception {
        assertEquals(400, req("POST", "/books", "{\"author\":\"X\"}").statusCode());
        assertEquals(400, req("POST", "/books", "{\"title\":\"  \",\"author\":\"X\"}").statusCode());
        assertEquals(400, req("POST", "/books", "{\"title\":\"T\"}").statusCode());
        assertEquals(400, req("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"abc\"}").statusCode());
        assertEquals(400, req("POST", "/books", "not json").statusCode());
        var c = req("POST", "/books", "{\"title\":\"T\",\"author\":\"A\"}");
        int id = ((Number) map(c).get("id")).intValue();
        assertEquals(400, req("PUT", "/books/" + id, "{\"title\":\"T\"}").statusCode());
        assertEquals(404, req("PUT", "/books/999", "{\"title\":\"T\",\"author\":\"A\"}").statusCode());
    }

    @Test void listWithAuthorFilter() throws Exception {
        req("POST", "/books", "{\"title\":\"A1\",\"author\":\"Ursula K. Le Guin\"}");
        req("POST", "/books", "{\"title\":\"A2\",\"author\":\"Ursula K. Le Guin\"}");
        req("POST", "/books", "{\"title\":\"B1\",\"author\":\"Iain Banks\"}");
        List<?> all = JSON.readValue(req("GET", "/books", null).body(), List.class);
        assertEquals(3, all.size());
        var f = req("GET", "/books?author=Ursula%20K.%20Le%20Guin", null);
        assertEquals(200, f.statusCode());
        assertEquals(2, JSON.readValue(f.body(), List.class).size());
    }
}
