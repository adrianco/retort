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

/** End-to-end tests: real HTTP server on a free port, in-memory SQLite. */
class BookApiTest {
    private static final String DUNE =
            "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

    private final ObjectMapper mapper = new ObjectMapper();
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
        return client.send(req.build(), BodyHandlers.ofString());
    }

    private JsonNode json(HttpResponse<String> res) throws Exception {
        return mapper.readTree(res.body());
    }

    @Test
    void healthCheck() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", json(res).get("status").asText());
        assertTrue(res.headers().firstValue("Content-Type").orElse("").startsWith("application/json"));
    }

    @Test
    void createThenGet() throws Exception {
        HttpResponse<String> created = send("POST", "/books", DUNE);
        assertEquals(201, created.statusCode());
        long id = json(created).get("id").asLong();
        assertEquals("/books/" + id, created.headers().firstValue("Location").orElse(null));

        HttpResponse<String> got = send("GET", "/books/" + id, null);
        assertEquals(200, got.statusCode());
        JsonNode book = json(got);
        assertEquals("Dune", book.get("title").asText());
        assertEquals("Frank Herbert", book.get("author").asText());
        assertEquals(1965, book.get("year").asInt());
        assertEquals("9780441172719", book.get("isbn").asText());
    }

    @Test
    void yearAndIsbnAreOptional() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(201, res.statusCode());
        assertTrue(json(res).get("year").isNull());
        assertTrue(json(res).get("isbn").isNull());
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"year\":1999}");
        assertEquals(400, res.statusCode());
        String details = json(res).get("details").toString();
        assertTrue(details.contains("title is required"), details);
        assertTrue(details.contains("author is required"), details);
        assertEquals(0, json(send("GET", "/books", null)).size());
    }

    @Test
    void createRejectsBlankTitleBadYearAndMalformedJson() throws Exception {
        assertEquals(400, send("POST", "/books", "{\"title\":\"  \",\"author\":\"A\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"x\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "").statusCode());
        assertEquals(400, send("POST", "/books", "[]").statusCode());
    }

    @Test
    void listAllAndFilterByAuthor() throws Exception {
        send("POST", "/books", DUNE);
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\",\"year\":1815}");
        send("POST", "/books", "{\"title\":\"Persuasion\",\"author\":\"Jane Austen\",\"year\":1817}");

        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertEquals(3, json(all).size());

        JsonNode austen = json(send("GET", "/books?author=Jane%20Austen", null));
        assertEquals(2, austen.size());
        assertEquals("Emma", austen.get(0).get("title").asText());
        assertEquals("Persuasion", austen.get(1).get("title").asText());

        assertEquals(0, json(send("GET", "/books?author=Nobody", null)).size());
    }

    @Test
    void updateReplacesBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> res = send("PUT", "/books/" + id,
                "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969}");
        assertEquals(200, res.statusCode());
        assertEquals(id, json(res).get("id").asLong());

        JsonNode book = json(send("GET", "/books/" + id, null));
        assertEquals("Dune Messiah", book.get("title").asText());
        assertEquals(1969, book.get("year").asInt());
        assertTrue(book.get("isbn").isNull());
    }

    @Test
    void updateValidatesAndReports404() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();
        assertEquals(400, send("PUT", "/books/" + id, "{\"title\":\"Only title\"}").statusCode());
        assertEquals("Dune", json(send("GET", "/books/" + id, null)).get("title").asText());
        assertEquals(404, send("PUT", "/books/9999", DUNE).statusCode());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> res = send("DELETE", "/books/" + id, null);
        assertEquals(204, res.statusCode());
        assertEquals("", res.body());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownIdsPathsAndMethods() throws Exception {
        assertEquals(404, send("GET", "/books/9999", null).statusCode());
        assertEquals(404, send("GET", "/books/abc", null).statusCode());
        assertEquals(404, send("GET", "/nope", null).statusCode());

        HttpResponse<String> res = send("DELETE", "/books", null);
        assertEquals(405, res.statusCode());
        assertEquals("GET, POST", res.headers().firstValue("Allow").orElse(null));
        assertEquals("Method not allowed", json(res).get("error").asText());
    }
}
