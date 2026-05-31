package com.example.bookapi;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.io.IOException;
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
public class BookApiIntegrationTest {

    private Javalin app;
    private BookRepository repo;
    private Path dbFile;
    private int port;
    private HttpClient http;
    private ObjectMapper mapper;
    private String base;

    @BeforeAll
    void startServer() throws IOException {
        dbFile = Files.createTempFile("books-test-", ".db");
        Files.deleteIfExists(dbFile);
        repo = new BookRepository("jdbc:sqlite:" + dbFile.toAbsolutePath());
        app = App.createApp(repo);
        app.start(0);
        port = app.port();
        base = "http://localhost:" + port;
        http = HttpClient.newHttpClient();
        mapper = new ObjectMapper();
    }

    @AfterAll
    void stopServer() throws IOException {
        app.stop();
        Files.deleteIfExists(dbFile);
    }

    @BeforeEach
    void cleanDb() {
        repo.deleteAll();
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        HttpResponse<String> resp = http.send(
                HttpRequest.newBuilder(URI.create(base + "/health")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, resp.statusCode());
        JsonNode body = mapper.readTree(resp.body());
        assertEquals("UP", body.get("status").asText());
    }

    @Test
    void createBookAndFetchById() throws Exception {
        HttpResponse<String> create = post("/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441013593\"}");
        assertEquals(201, create.statusCode());
        JsonNode created = mapper.readTree(create.body());
        long id = created.get("id").asLong();
        assertTrue(id > 0);
        assertEquals("Dune", created.get("title").asText());

        HttpResponse<String> fetch = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, fetch.statusCode());
        JsonNode book = mapper.readTree(fetch.body());
        assertEquals("Frank Herbert", book.get("author").asText());
        assertEquals(1965, book.get("year").asInt());
    }

    @Test
    void createBookValidatesRequiredFields() throws Exception {
        HttpResponse<String> resp = post("/books", "{\"author\":\"Nobody\"}");
        assertEquals(400, resp.statusCode());
        JsonNode body = mapper.readTree(resp.body());
        assertTrue(body.get("error").asText().toLowerCase().contains("title"));
    }

    @Test
    void listAndFilterByAuthor() throws Exception {
        post("/books", "{\"title\":\"A\",\"author\":\"Asimov\"}");
        post("/books", "{\"title\":\"B\",\"author\":\"Asimov\"}");
        post("/books", "{\"title\":\"C\",\"author\":\"Tolkien\"}");

        HttpResponse<String> all = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, all.statusCode());
        JsonNode allArr = mapper.readTree(all.body());
        assertEquals(3, allArr.size());

        HttpResponse<String> filtered = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books?author=Asimov")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, filtered.statusCode());
        JsonNode arr = mapper.readTree(filtered.body());
        assertEquals(2, arr.size());
        for (JsonNode b : arr) {
            assertEquals("Asimov", b.get("author").asText());
        }
    }

    @Test
    void updateBookReplacesFields() throws Exception {
        HttpResponse<String> created = post("/books",
                "{\"title\":\"Old\",\"author\":\"Someone\",\"year\":2000}");
        long id = mapper.readTree(created.body()).get("id").asLong();

        HttpResponse<String> updated = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id))
                        .header("Content-Type", "application/json")
                        .PUT(HttpRequest.BodyPublishers.ofString(
                                "{\"title\":\"New\",\"author\":\"Someone Else\",\"year\":2020}"))
                        .build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(200, updated.statusCode());
        JsonNode body = mapper.readTree(updated.body());
        assertEquals("New", body.get("title").asText());
        assertEquals("Someone Else", body.get("author").asText());
        assertEquals(2020, body.get("year").asInt());
    }

    @Test
    void deleteBookReturns204AndThen404() throws Exception {
        HttpResponse<String> created = post("/books",
                "{\"title\":\"Bye\",\"author\":\"Author\"}");
        long id = mapper.readTree(created.body()).get("id").asLong();

        HttpResponse<String> del = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).DELETE().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(204, del.statusCode());

        HttpResponse<String> after = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books/" + id)).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(404, after.statusCode());
    }

    @Test
    void getMissingBookReturns404() throws Exception {
        HttpResponse<String> resp = http.send(
                HttpRequest.newBuilder(URI.create(base + "/books/99999")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        assertEquals(404, resp.statusCode());
        assertNotNull(mapper.readTree(resp.body()).get("error"));
    }

    private HttpResponse<String> post(String path, String json) throws Exception {
        return http.send(
                HttpRequest.newBuilder(URI.create(base + path))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(json))
                        .build(),
                HttpResponse.BodyHandlers.ofString());
    }
}
