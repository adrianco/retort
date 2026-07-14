package com.example.bookapi;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class BookApiTest {

    private Javalin app;
    private Path dbFile;
    private HttpClient http;
    private ObjectMapper mapper;
    private String baseUrl;

    @BeforeAll
    void setUp() throws Exception {
        dbFile = Files.createTempFile("books-test-", ".db");
        Files.deleteIfExists(dbFile);
        BookRepository repo = new BookRepository("jdbc:sqlite:" + dbFile.toAbsolutePath());
        app = App.create(repo);
        app.start(0);
        baseUrl = "http://localhost:" + app.port();
        http = HttpClient.newHttpClient();
        mapper = new ObjectMapper();
    }

    @AfterAll
    void tearDown() throws Exception {
        if (app != null) app.stop();
        if (dbFile != null) Files.deleteIfExists(dbFile);
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        HttpResponse<String> resp = get("/health");
        assertEquals(200, resp.statusCode());
        JsonNode body = mapper.readTree(resp.body());
        assertEquals("ok", body.get("status").asText());
    }

    @Test
    void createGetUpdateDeleteFlow() throws Exception {
        String payload = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441013593\"}";
        HttpResponse<String> created = post("/books", payload);
        assertEquals(201, created.statusCode());
        JsonNode createdBody = mapper.readTree(created.body());
        long id = createdBody.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("Dune", createdBody.get("title").asText());

        HttpResponse<String> fetched = get("/books/" + id);
        assertEquals(200, fetched.statusCode());
        assertEquals("Frank Herbert", mapper.readTree(fetched.body()).get("author").asText());

        String updatePayload = "{\"title\":\"Dune (Revised)\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441013593\"}";
        HttpResponse<String> updated = put("/books/" + id, updatePayload);
        assertEquals(200, updated.statusCode());
        assertEquals("Dune (Revised)", mapper.readTree(updated.body()).get("title").asText());

        HttpResponse<String> deleted = delete("/books/" + id);
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> missing = get("/books/" + id);
        assertEquals(404, missing.statusCode());
    }

    @Test
    void listWithAuthorFilter() throws Exception {
        post("/books", "{\"title\":\"Foundation\",\"author\":\"Isaac Asimov\",\"year\":1951}");
        post("/books", "{\"title\":\"I, Robot\",\"author\":\"Isaac Asimov\",\"year\":1950}");
        post("/books", "{\"title\":\"Neuromancer\",\"author\":\"William Gibson\",\"year\":1984}");

        HttpResponse<String> all = get("/books");
        JsonNode allBody = mapper.readTree(all.body());
        assertTrue(allBody.isArray());
        assertTrue(allBody.size() >= 3);

        HttpResponse<String> filtered = get("/books?author=Isaac%20Asimov");
        JsonNode filteredBody = mapper.readTree(filtered.body());
        assertEquals(2, filteredBody.size());
        for (JsonNode node : filteredBody) {
            assertEquals("Isaac Asimov", node.get("author").asText());
        }
    }

    @Test
    void createMissingTitleReturns400() throws Exception {
        HttpResponse<String> resp = post("/books", "{\"author\":\"Anonymous\"}");
        assertEquals(400, resp.statusCode());
        assertNotNull(mapper.readTree(resp.body()).get("error"));
    }

    @Test
    void getUnknownIdReturns404() throws Exception {
        HttpResponse<String> resp = get("/books/9999999");
        assertEquals(404, resp.statusCode());
    }

    private HttpResponse<String> get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path)).GET().build();
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> post(String path, String body) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> put(String path, String body) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .header("Content-Type", "application/json")
                .PUT(HttpRequest.BodyPublishers.ofString(body))
                .build();
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> delete(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + path)).DELETE().build();
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }
}
