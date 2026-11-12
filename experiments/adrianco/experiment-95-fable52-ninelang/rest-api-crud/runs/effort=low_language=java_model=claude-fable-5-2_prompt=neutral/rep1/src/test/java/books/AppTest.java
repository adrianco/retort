package books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AppTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String DUNE =
            "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

    @TempDir
    Path tmp;
    private Javalin app;
    private Path dbFile;
    private final HttpClient client = HttpClient.newHttpClient();

    @BeforeEach
    void start() {
        dbFile = tmp.resolve("test.db");
        app = App.create(new BookRepository(dbFile.toString())).start(0);
    }

    @AfterEach
    void stop() {
        app.stop();
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create("http://localhost:" + app.port() + path));
        b.method(method, body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body));
        if (body != null) {
            b.header("Content-Type", "application/json");
        }
        return client.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    private static JsonNode json(HttpResponse<String> r) throws Exception {
        return MAPPER.readTree(r.body());
    }

    @Test
    void healthCheck() throws Exception {
        HttpResponse<String> r = send("GET", "/health", null);
        assertEquals(200, r.statusCode());
        assertEquals("ok", json(r).get("status").asText());
        assertTrue(r.headers().firstValue("Content-Type").orElse("").startsWith("application/json"));
    }

    @Test
    void createAndGetBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books", DUNE);
        assertEquals(201, created.statusCode());
        JsonNode book = json(created);
        long id = book.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("Dune", book.get("title").asText());

        HttpResponse<String> got = send("GET", "/books/" + id, null);
        assertEquals(200, got.statusCode());
        JsonNode g = json(got);
        assertEquals("Frank Herbert", g.get("author").asText());
        assertEquals(1965, g.get("year").asInt());
        assertEquals("9780441172719", g.get("isbn").asText());
    }

    @Test
    void createWithOnlyRequiredFields() throws Exception {
        HttpResponse<String> r = send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(201, r.statusCode());
        assertTrue(json(r).get("year").isNull());
        assertTrue(json(r).get("isbn").isNull());
    }

    @Test
    void validationRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> r = send("POST", "/books", "{\"year\":2000}");
        assertEquals(400, r.statusCode());
        String details = json(r).get("details").toString();
        assertTrue(details.contains("title is required"));
        assertTrue(details.contains("author is required"));

        assertEquals(400, send("POST", "/books", "{\"title\":\"  \",\"author\":\"A\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"x\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "[]").statusCode());
        assertEquals(0, json(send("GET", "/books", null)).size());
    }

    @Test
    void listAndFilterByAuthor() throws Exception {
        send("POST", "/books", DUNE);
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\",\"year\":1815}");
        send("POST", "/books", "{\"title\":\"Persuasion\",\"author\":\"Jane Austen\",\"year\":1817}");

        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertEquals(3, json(all).size());

        JsonNode austen = json(send("GET", "/books?author=Jane%20Austen", null));
        assertEquals(2, austen.size());
        assertEquals("Emma", austen.get(0).get("title").asText());

        assertEquals(0, json(send("GET", "/books?author=Nobody", null)).size());
    }

    @Test
    void updateBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> r = send("PUT", "/books/" + id,
                "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969}");
        assertEquals(200, r.statusCode());
        assertEquals("Dune Messiah", json(r).get("title").asText());

        JsonNode got = json(send("GET", "/books/" + id, null));
        assertEquals("Dune Messiah", got.get("title").asText());
        assertEquals(1969, got.get("year").asInt());
        assertTrue(got.get("isbn").isNull());

        assertEquals(400, send("PUT", "/books/" + id, "{\"title\":\"X\"}").statusCode());
        assertEquals(404, send("PUT", "/books/9999", DUNE).statusCode());
    }

    @Test
    void deleteBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();
        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownAndInvalidIds() throws Exception {
        HttpResponse<String> missing = send("GET", "/books/42", null);
        assertEquals(404, missing.statusCode());
        assertTrue(json(missing).has("error"));
        assertEquals(400, send("GET", "/books/abc", null).statusCode());
        HttpResponse<String> noRoute = send("GET", "/nope", null);
        assertEquals(404, noRoute.statusCode());
        assertTrue(json(noRoute).has("error"));
    }

    @Test
    void dataPersistsAcrossRestart() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();
        app.stop();
        app = App.create(new BookRepository(dbFile.toString())).start(0);
        assertEquals("Dune", json(send("GET", "/books/" + id, null)).get("title").asText());
    }
}
