package books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse;
import java.net.http.HttpResponse.BodyHandlers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end tests: real HTTP server on an ephemeral port, in-memory SQLite. */
class BookApiTest {
    private static final String DUNE =
            "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

    private final ObjectMapper json = new ObjectMapper();
    private final HttpClient client = HttpClient.newHttpClient();
    private BookRepository repo;
    private BookServer server;

    @BeforeEach
    void setUp() throws Exception {
        repo = new BookRepository("jdbc:sqlite::memory:");
        server = new BookServer(repo, 0);
        server.start();
    }

    @AfterEach
    void tearDown() throws Exception {
        server.stop();
        repo.close();
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder req = HttpRequest.newBuilder(URI.create("http://localhost:" + server.port() + path))
                .method(method, body == null ? BodyPublishers.noBody() : BodyPublishers.ofString(body));
        if (body != null) {
            req.header("Content-Type", "application/json");
        }
        return client.send(req.build(), BodyHandlers.ofString());
    }

    private JsonNode parse(HttpResponse<String> res) throws Exception {
        return json.readTree(res.body());
    }

    @Test
    void healthReturnsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", parse(res).get("status").asText());
        assertTrue(res.headers().firstValue("Content-Type").orElse("").startsWith("application/json"));
    }

    @Test
    void createThenGetBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books", DUNE);
        assertEquals(201, created.statusCode());
        JsonNode book = parse(created);
        long id = book.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("/books/" + id, created.headers().firstValue("Location").orElse(null));

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(200, fetched.statusCode());
        JsonNode got = parse(fetched);
        assertEquals("Dune", got.get("title").asText());
        assertEquals("Frank Herbert", got.get("author").asText());
        assertEquals(1965, got.get("year").asInt());
        assertEquals("9780441172719", got.get("isbn").asText());
    }

    @Test
    void createWithOnlyRequiredFields() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(201, res.statusCode());
        JsonNode book = parse(res);
        assertTrue(book.get("year").isNull());
        assertTrue(book.get("isbn").isNull());
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"year\":1965}");
        assertEquals(400, res.statusCode());
        JsonNode body = parse(res);
        assertEquals("Validation failed", body.get("error").asText());
        assertEquals(2, body.get("details").size());
        assertEquals(0, parse(send("GET", "/books", null)).size());
    }

    @Test
    void createRejectsBlankOrWronglyTypedFields() throws Exception {
        assertEquals(400, send("POST", "/books", "{\"title\":\"  \",\"author\":\"A\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":42}").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"x\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":1.5}").statusCode());
    }

    @Test
    void createRejectsMalformedJson() throws Exception {
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "[1,2]").statusCode());
        assertEquals(400, send("POST", "/books", "").statusCode());
    }

    @Test
    void listReturnsAllBooksAndFiltersByAuthor() throws Exception {
        send("POST", "/books", DUNE);
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\",\"year\":1815}");
        send("POST", "/books", "{\"title\":\"Persuasion\",\"author\":\"Jane Austen\",\"year\":1817}");

        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertEquals(3, parse(all).size());

        JsonNode austen = parse(send("GET", "/books?author=Jane%20Austen", null));
        assertEquals(2, austen.size());
        assertEquals("Emma", austen.get(0).get("title").asText());
        assertEquals("Persuasion", austen.get(1).get("title").asText());

        assertEquals(2, parse(send("GET", "/books?author=jane+austen", null)).size());
        assertEquals(0, parse(send("GET", "/books?author=Nobody", null)).size());
    }

    @Test
    void updateReplacesBook() throws Exception {
        long id = parse(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> res = send("PUT", "/books/" + id,
                "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969}");
        assertEquals(200, res.statusCode());
        assertEquals(id, parse(res).get("id").asLong());

        JsonNode got = parse(send("GET", "/books/" + id, null));
        assertEquals("Dune Messiah", got.get("title").asText());
        assertEquals(1969, got.get("year").asInt());
        assertTrue(got.get("isbn").isNull());
    }

    @Test
    void updateValidatesAndReports404() throws Exception {
        long id = parse(send("POST", "/books", DUNE)).get("id").asLong();
        assertEquals(400, send("PUT", "/books/" + id, "{\"title\":\"No author\"}").statusCode());
        assertEquals("Dune", parse(send("GET", "/books/" + id, null)).get("title").asText());
        assertEquals(404, send("PUT", "/books/9999", DUNE).statusCode());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        long id = parse(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> res = send("DELETE", "/books/" + id, null);
        assertEquals(204, res.statusCode());
        assertEquals("", res.body());

        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownBookAndBadIdsAndRoutes() throws Exception {
        HttpResponse<String> missing = send("GET", "/books/12345", null);
        assertEquals(404, missing.statusCode());
        assertTrue(parse(missing).has("error"));

        assertEquals(400, send("GET", "/books/abc", null).statusCode());
        assertEquals(404, send("GET", "/nope", null).statusCode());

        HttpResponse<String> notAllowed = send("DELETE", "/books", null);
        assertEquals(405, notAllowed.statusCode());
        assertEquals("GET, POST", notAllowed.headers().firstValue("Allow").orElse(null));
    }
}
