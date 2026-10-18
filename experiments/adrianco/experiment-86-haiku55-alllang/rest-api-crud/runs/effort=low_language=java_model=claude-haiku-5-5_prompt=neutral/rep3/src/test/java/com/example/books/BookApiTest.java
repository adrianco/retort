package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * End-to-end tests that drive the real HTTP server against an in-memory SQLite database.
 */
class BookApiTest {

    private static final String CLEAN_BOOK = """
            {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}""";

    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpClient client = HttpClient.newHttpClient();

    private BookRepository repository;
    private BookServer server;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        repository = new BookRepository("jdbc:sqlite::memory:");
        server = new BookServer(0, repository);
        server.start();
        base = "http://localhost:" + server.port();
    }

    @AfterEach
    void tearDown() throws Exception {
        server.stop();
        repository.close();
    }

    @Test
    void healthEndpointReportsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", json(res).get("status").asText());
    }

    @Test
    void createThenGetBookById() throws Exception {
        HttpResponse<String> created = send("POST", "/books", CLEAN_BOOK);
        assertEquals(201, created.statusCode());
        JsonNode body = json(created);
        long id = body.get("id").asLong();
        assertEquals("Dune", body.get("title").asText());
        assertEquals(1965, body.get("year").asInt());
        assertEquals("/books/" + id, created.headers().firstValue("Location").orElseThrow());

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(200, fetched.statusCode());
        assertEquals("Frank Herbert", json(fetched).get("author").asText());
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"year\":2000}");
        assertEquals(400, res.statusCode());
        JsonNode details = json(res).get("details");
        assertTrue(details.toString().contains("title is required"));
        assertTrue(details.toString().contains("author is required"));
    }

    @Test
    void createRejectsBlankAndInvalidFields() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"   \",\"author\":\"A\",\"year\":0,\"isbn\":\"123\"}");
        assertEquals(400, res.statusCode());
        assertTrue(json(res).get("details").size() == 3);
    }

    @Test
    void malformedJsonIsBadRequest() throws Exception {
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "").statusCode());
    }

    @Test
    void listFiltersByAuthorCaseInsensitively() throws Exception {
        send("POST", "/books", CLEAN_BOOK);
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\"}");
        send("POST", "/books", "{\"title\":\"Children of Dune\",\"author\":\"frank herbert\"}");

        assertEquals(3, json(send("GET", "/books", null)).size());

        JsonNode herbert = json(send("GET", "/books?author=Frank%20Herbert", null));
        assertEquals(2, herbert.size());
        assertEquals("Dune", herbert.get(0).get("title").asText());
        assertEquals("Children of Dune", herbert.get(1).get("title").asText());

        assertEquals(0, json(send("GET", "/books?author=Nobody", null)).size());
    }

    @Test
    void updateReplacesBook() throws Exception {
        long id = json(send("POST", "/books", CLEAN_BOOK)).get("id").asLong();

        HttpResponse<String> res = send("PUT", "/books/" + id,
                "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\"}");
        assertEquals(200, res.statusCode());
        assertEquals("Dune Messiah", json(res).get("title").asText());
        assertTrue(json(res).get("year").isNull());

        assertEquals("Dune Messiah", json(send("GET", "/books/" + id, null)).get("title").asText());
    }

    @Test
    void updateValidatesInputAndMissingBooks() throws Exception {
        long id = json(send("POST", "/books", CLEAN_BOOK)).get("id").asLong();
        assertEquals(400, send("PUT", "/books/" + id, "{\"author\":\"X\"}").statusCode());
        assertEquals(404, send("PUT", "/books/999", "{\"title\":\"T\",\"author\":\"A\"}").statusCode());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        long id = json(send("POST", "/books", CLEAN_BOOK)).get("id").asLong();

        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownBookAndBadIdsReturnErrors() throws Exception {
        assertEquals(404, send("GET", "/books/12345", null).statusCode());
        assertEquals(400, send("GET", "/books/abc", null).statusCode());
        assertEquals(400, send("GET", "/books/0", null).statusCode());
        assertEquals(404, send("GET", "/nope", null).statusCode());
        assertEquals(405, send("PATCH", "/books", null).statusCode());
        assertEquals(405, send("POST", "/health", null).statusCode());
    }

    @Test
    void repositoryInsertAndFindById() throws Exception {
        BookRepository repo = new BookRepository("jdbc:sqlite::memory:");
        try {
            var created = repo.insert(new BookRequest("T", "A", null, null));
            assertEquals(created, repo.findById(created.id()).orElseThrow());
            assertFalse(repo.findById(created.id() + 1).isPresent());
        } finally {
            repo.close();
        }
    }

    @Test
    void validatorAcceptsValidIsbn13AndRejectsBadCheckDigit() {
        assertTrue(BookValidator.isValidIsbn("978-0-441-01359-3"));
        assertTrue(BookValidator.isValidIsbn("0-306-40615-2"));
        assertFalse(BookValidator.isValidIsbn("978-0-441-01359-4"));
    }

    private HttpResponse<String> send(String method, String path, String body) throws IOException, InterruptedException {
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        HttpRequest request = HttpRequest.newBuilder(URI.create(base + path))
                .method(method, publisher)
                .header("Content-Type", "application/json")
                .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private JsonNode json(HttpResponse<String> res) throws IOException {
        return mapper.readTree(res.body());
    }
}
