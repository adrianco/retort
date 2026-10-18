package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    @TempDir
    Path tempDir;

    private BookRepository repository;
    private BookServer server;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        repository = new BookRepository("jdbc:sqlite:" + tempDir.resolve("test.db"));
        server = new BookServer(0, repository);
        server.start();
        base = "http://localhost:" + server.port();
        client = HttpClient.newHttpClient();
    }

    @AfterEach
    void tearDown() throws Exception {
        server.stop();
        repository.close();
    }

    @Test
    void createThenGetBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}");
        assertEquals(201, created.statusCode());
        JsonNode body = JSON.readTree(created.body());
        long id = body.get("id").asLong();
        assertEquals("Dune", body.get("title").asText());

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(200, fetched.statusCode());
        assertEquals("Frank Herbert", JSON.readTree(fetched.body()).get("author").asText());
        assertEquals(1965, JSON.readTree(fetched.body()).get("year").asInt());
    }

    @Test
    void listFiltersByAuthor() throws Exception {
        send("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}");
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\"}");
        send("POST", "/books", "{\"title\":\"Children of Dune\",\"author\":\"frank herbert\"}");

        JsonNode all = JSON.readTree(send("GET", "/books", null).body());
        assertEquals(3, all.size());

        JsonNode herbert = JSON.readTree(send("GET", "/books?author=Frank%20Herbert", null).body());
        assertEquals(2, herbert.size());
        for (JsonNode book : herbert) {
            assertTrue(book.get("author").asText().equalsIgnoreCase("Frank Herbert"));
        }
    }

    @Test
    void updateAndDeleteBook() throws Exception {
        long id = JSON.readTree(send("POST", "/books",
                "{\"title\":\"Draft\",\"author\":\"Me\"}").body()).get("id").asLong();

        HttpResponse<String> updated = send("PUT", "/books/" + id,
                "{\"title\":\"Final\",\"author\":\"Me\",\"year\":2024}");
        assertEquals(200, updated.statusCode());
        assertEquals("Final", JSON.readTree(updated.body()).get("title").asText());

        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void rejectsInvalidInput() throws Exception {
        HttpResponse<String> missingAuthor = send("POST", "/books", "{\"title\":\"No Author\"}");
        assertEquals(400, missingAuthor.statusCode());
        assertTrue(missingAuthor.body().contains("author is required"));

        assertEquals(400, send("POST", "/books", "{\"title\":\"   \",\"author\":\"X\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"abc\"}").statusCode());
        assertEquals(400, send("PUT", "/books/1", "{\"author\":\"A\"}").statusCode());
    }

    @Test
    void unknownRoutesAndBadIdsReturnErrors() throws Exception {
        assertEquals(400, send("GET", "/books/abc", null).statusCode());
        assertEquals(404, send("GET", "/books/999", null).statusCode());
        assertEquals(404, send("GET", "/nope", null).statusCode());
        assertEquals(405, send("PATCH", "/books", null).statusCode());
    }

    @Test
    void healthEndpointReportsUp() throws Exception {
        HttpResponse<String> health = send("GET", "/health", null);
        assertEquals(200, health.statusCode());
        assertEquals("UP", JSON.readTree(health.body()).get("status").asText());
        assertFalse(health.body().isBlank());
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        HttpRequest request = HttpRequest.newBuilder(URI.create(base + path))
                .method(method, publisher)
                .header("Content-Type", "application/json")
                .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }
}
