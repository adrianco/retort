package com.example.bookapi;

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
import java.nio.charset.StandardCharsets;
import java.net.URLEncoder;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * End-to-end tests that exercise the running HTTP server against an in-memory
 * SQLite database.
 */
class BookApiIntegrationTest {

    private App app;
    private HttpClient client;
    private String base;
    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeEach
    void setUp() throws IOException {
        // Shared in-memory DB that persists for the life of the connection.
        app = new App(0, "jdbc:sqlite:file:test_" + System.nanoTime()
                + "?mode=memory&cache=shared");
        app.start();
        client = HttpClient.newHttpClient();
        base = "http://localhost:" + app.port();
    }

    @AfterEach
    void tearDown() {
        app.stop();
    }

    private HttpResponse<String> send(HttpRequest request) throws IOException, InterruptedException {
        return client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private HttpResponse<String> post(String path, String body) throws IOException, InterruptedException {
        return send(HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build());
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> resp = send(HttpRequest.newBuilder(URI.create(base + "/health")).GET().build());
        assertEquals(200, resp.statusCode());
        assertEquals("ok", mapper.readTree(resp.body()).get("status").asText());
    }

    @Test
    void createThenGetById() throws Exception {
        HttpResponse<String> created = post("/books",
                "{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"123\"}");
        assertEquals(201, created.statusCode());
        JsonNode createdBook = mapper.readTree(created.body());
        long id = createdBook.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("Dune", createdBook.get("title").asText());

        HttpResponse<String> fetched = send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build());
        assertEquals(200, fetched.statusCode());
        JsonNode book = mapper.readTree(fetched.body());
        assertEquals("Herbert", book.get("author").asText());
        assertEquals(1965, book.get("year").asInt());
    }

    @Test
    void createWithoutTitleReturns400() throws Exception {
        HttpResponse<String> resp = post("/books", "{\"author\":\"Nobody\"}");
        assertEquals(400, resp.statusCode());
        assertTrue(mapper.readTree(resp.body()).get("error").asText().toLowerCase().contains("title"));
    }

    @Test
    void listFiltersByAuthor() throws Exception {
        post("/books", "{\"title\":\"A\",\"author\":\"Alice\"}");
        post("/books", "{\"title\":\"B\",\"author\":\"Bob\"}");
        post("/books", "{\"title\":\"C\",\"author\":\"Alice\"}");

        String q = URLEncoder.encode("Alice", StandardCharsets.UTF_8);
        HttpResponse<String> resp = send(
                HttpRequest.newBuilder(URI.create(base + "/books?author=" + q)).GET().build());
        assertEquals(200, resp.statusCode());
        JsonNode arr = mapper.readTree(resp.body());
        assertEquals(2, arr.size());
        for (JsonNode b : arr) {
            assertEquals("Alice", b.get("author").asText());
        }
    }

    @Test
    void updateChangesFields() throws Exception {
        long id = mapper.readTree(post("/books",
                "{\"title\":\"Old\",\"author\":\"Author\"}").body()).get("id").asLong();

        HttpResponse<String> resp = send(HttpRequest.newBuilder(URI.create(base + "/books/" + id))
                .header("Content-Type", "application/json")
                .PUT(HttpRequest.BodyPublishers.ofString(
                        "{\"title\":\"New\",\"author\":\"Author\",\"year\":2000}"))
                .build());
        assertEquals(200, resp.statusCode());
        assertEquals("New", mapper.readTree(resp.body()).get("title").asText());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        long id = mapper.readTree(post("/books",
                "{\"title\":\"Temp\",\"author\":\"Author\"}").body()).get("id").asLong();

        HttpResponse<String> del = send(HttpRequest.newBuilder(URI.create(base + "/books/" + id))
                .DELETE().build());
        assertEquals(204, del.statusCode());

        HttpResponse<String> fetched = send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build());
        assertEquals(404, fetched.statusCode());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        HttpResponse<String> resp = send(
                HttpRequest.newBuilder(URI.create(base + "/books/999999")).GET().build());
        assertEquals(404, resp.statusCode());
        assertFalse(resp.body().isBlank());
    }
}
