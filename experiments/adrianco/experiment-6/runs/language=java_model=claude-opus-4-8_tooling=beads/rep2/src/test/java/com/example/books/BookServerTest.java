package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Integration tests that exercise the full HTTP stack against an
 * in-memory SQLite database on a randomly assigned port.
 */
class BookServerTest {

    private BookServer server;
    private HttpClient client;
    private final ObjectMapper mapper = new ObjectMapper();
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        // A unique shared in-memory DB per test run keeps the connection-per-call
        // repository pointed at the same data.
        String jdbcUrl = "jdbc:sqlite:file:memdb_" + System.nanoTime()
                + "?mode=memory&cache=shared";
        // Keep one connection open for the lifetime of the test so the shared
        // in-memory database is not discarded between calls.
        keepAlive = java.sql.DriverManager.getConnection(jdbcUrl);

        BookRepository repository = new BookRepository(jdbcUrl);
        server = new BookServer(0, repository);
        server.start();
        client = HttpClient.newHttpClient();
        base = "http://localhost:" + server.getPort();
    }

    private java.sql.Connection keepAlive;

    @AfterEach
    void tearDown() throws Exception {
        server.stop();
        if (keepAlive != null) {
            keepAlive.close();
        }
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> resp = get("/health");
        assertEquals(200, resp.statusCode());
        JsonNode body = mapper.readTree(resp.body());
        assertEquals("ok", body.get("status").asText());
    }

    @Test
    void createAndFetchBook() throws Exception {
        String json = """
                {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}
                """;
        HttpResponse<String> created = post("/books", json);
        assertEquals(201, created.statusCode());

        JsonNode createdBody = mapper.readTree(created.body());
        int id = createdBody.get("id").asInt();
        assertTrue(id > 0);
        assertEquals("Dune", createdBody.get("title").asText());

        HttpResponse<String> fetched = get("/books/" + id);
        assertEquals(200, fetched.statusCode());
        JsonNode fetchedBody = mapper.readTree(fetched.body());
        assertEquals("Frank Herbert", fetchedBody.get("author").asText());
        assertEquals(1965, fetchedBody.get("year").asInt());
    }

    @Test
    void createBookWithoutTitleFailsValidation() throws Exception {
        String json = """
                {"author":"Anonymous"}
                """;
        HttpResponse<String> resp = post("/books", json);
        assertEquals(400, resp.statusCode());
        JsonNode body = mapper.readTree(resp.body());
        assertTrue(body.get("error").asText().contains("title"));
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        post("/books", "{\"title\":\"A\",\"author\":\"Alice\"}");
        post("/books", "{\"title\":\"B\",\"author\":\"Bob\"}");
        post("/books", "{\"title\":\"C\",\"author\":\"Alice\"}");

        HttpResponse<String> all = get("/books");
        assertEquals(200, all.statusCode());
        assertEquals(3, mapper.readTree(all.body()).size());

        HttpResponse<String> filtered = get("/books?author=Alice");
        assertEquals(200, filtered.statusCode());
        JsonNode arr = mapper.readTree(filtered.body());
        assertEquals(2, arr.size());
        for (JsonNode node : arr) {
            assertEquals("Alice", node.get("author").asText());
        }
    }

    @Test
    void updateBook() throws Exception {
        HttpResponse<String> created = post("/books",
                "{\"title\":\"Old\",\"author\":\"Author\"}");
        int id = mapper.readTree(created.body()).get("id").asInt();

        HttpResponse<String> updated = put("/books/" + id,
                "{\"title\":\"New Title\",\"author\":\"Author\",\"year\":2020}");
        assertEquals(200, updated.statusCode());
        JsonNode body = mapper.readTree(updated.body());
        assertEquals("New Title", body.get("title").asText());
        assertEquals(2020, body.get("year").asInt());
    }

    @Test
    void deleteBookThenNotFound() throws Exception {
        HttpResponse<String> created = post("/books",
                "{\"title\":\"Doomed\",\"author\":\"Author\"}");
        int id = mapper.readTree(created.body()).get("id").asInt();

        HttpResponse<String> deleted = delete("/books/" + id);
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> fetched = get("/books/" + id);
        assertEquals(404, fetched.statusCode());
    }

    @Test
    void unknownBookReturns404() throws Exception {
        HttpResponse<String> resp = get("/books/999999");
        assertEquals(404, resp.statusCode());
    }

    @Test
    void invalidIdReturns400() throws Exception {
        HttpResponse<String> resp = get("/books/not-a-number");
        assertEquals(400, resp.statusCode());
        assertFalse(resp.body().isEmpty());
    }

    // ---- HTTP helpers ----

    private HttpResponse<String> get(String path) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> post(String path, String body) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(body)).build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> put(String path, String body) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path))
                        .header("Content-Type", "application/json")
                        .PUT(HttpRequest.BodyPublishers.ofString(body)).build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> delete(String path) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).DELETE().build(),
                HttpResponse.BodyHandlers.ofString());
    }
}
