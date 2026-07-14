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
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private App app;
    private Path dbFile;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        dbFile = Files.createTempFile("books-test-", ".db");
        Files.deleteIfExists(dbFile);
        BookRepository repo = new BookRepository("jdbc:sqlite:" + dbFile.toAbsolutePath());
        app = new App(0, repo);
        app.start();
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        base = "http://localhost:" + app.port();
    }

    @AfterEach
    void tearDown() throws Exception {
        app.stop();
        Files.deleteIfExists(dbFile);
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        HttpResponse<String> resp = get("/health");
        assertEquals(200, resp.statusCode());
        JsonNode body = MAPPER.readTree(resp.body());
        assertEquals("ok", body.get("status").asText());
    }

    @Test
    void createListGetUpdateDeleteBook() throws Exception {
        String payload = """
                {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}
                """;
        HttpResponse<String> created = post("/books", payload);
        assertEquals(201, created.statusCode());
        JsonNode createdBody = MAPPER.readTree(created.body());
        long id = createdBody.get("id").asLong();
        assertEquals("Dune", createdBody.get("title").asText());

        HttpResponse<String> list = get("/books");
        assertEquals(200, list.statusCode());
        JsonNode listBody = MAPPER.readTree(list.body());
        assertTrue(listBody.isArray());
        assertEquals(1, listBody.size());

        HttpResponse<String> single = get("/books/" + id);
        assertEquals(200, single.statusCode());
        assertEquals("Frank Herbert", MAPPER.readTree(single.body()).get("author").asText());

        String updated = """
                {"title":"Dune (Revised)","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}
                """;
        HttpResponse<String> upd = put("/books/" + id, updated);
        assertEquals(200, upd.statusCode());
        assertEquals("Dune (Revised)", MAPPER.readTree(upd.body()).get("title").asText());

        HttpResponse<String> del = delete("/books/" + id);
        assertEquals(204, del.statusCode());

        HttpResponse<String> gone = get("/books/" + id);
        assertEquals(404, gone.statusCode());
    }

    @Test
    void rejectsBookWithoutRequiredFields() throws Exception {
        HttpResponse<String> noTitle = post("/books", "{\"author\":\"Anon\"}");
        assertEquals(400, noTitle.statusCode());
        assertTrue(noTitle.body().contains("title"));

        HttpResponse<String> noAuthor = post("/books", "{\"title\":\"Untitled\"}");
        assertEquals(400, noAuthor.statusCode());
        assertTrue(noAuthor.body().contains("author"));
    }

    @Test
    void filterByAuthor() throws Exception {
        post("/books", "{\"title\":\"A\",\"author\":\"Alice\"}");
        post("/books", "{\"title\":\"B\",\"author\":\"Bob\"}");
        post("/books", "{\"title\":\"C\",\"author\":\"Alice\"}");

        HttpResponse<String> all = get("/books");
        assertEquals(3, MAPPER.readTree(all.body()).size());

        HttpResponse<String> alice = get("/books?author=Alice");
        JsonNode body = MAPPER.readTree(alice.body());
        assertEquals(2, body.size());
        for (JsonNode n : body) {
            assertEquals("Alice", n.get("author").asText());
        }
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        HttpResponse<String> resp = get("/books/9999");
        assertEquals(404, resp.statusCode());
    }

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
