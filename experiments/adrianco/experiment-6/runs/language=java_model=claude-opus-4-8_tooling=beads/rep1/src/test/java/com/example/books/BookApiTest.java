package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.testtools.JavalinTest;
import okhttp3.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Integration tests that exercise the full HTTP stack against an in-memory
 * SQLite database (fresh per test).
 */
class BookApiTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private BookDao dao;
    private Javalin app;

    @BeforeEach
    void setUp() {
        // Each test gets its own isolated in-memory database.
        dao = new BookDao("jdbc:sqlite::memory:");
        app = App.create(dao);
    }

    @AfterEach
    void tearDown() {
        dao.close();
    }

    @Test
    void healthCheckReturnsOk() {
        JavalinTest.test(app, (server, client) -> {
            try (Response res = client.get("/health")) {
                assertEquals(200, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertEquals("ok", json.get("status").asText());
            }
        });
    }

    @Test
    void createBookReturns201WithId() {
        JavalinTest.test(app, (server, client) -> {
            try (Response res = client.post("/books",
                    "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441013593\"}")) {
                assertEquals(201, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertNotNull(json.get("id"));
                assertTrue(json.get("id").asLong() > 0);
                assertEquals("Dune", json.get("title").asText());
                assertEquals("Frank Herbert", json.get("author").asText());
                assertEquals(1965, json.get("year").asInt());
            }
        });
    }

    @Test
    void createBookWithoutTitleReturns400() {
        JavalinTest.test(app, (server, client) -> {
            try (Response res = client.post("/books", "{\"author\":\"Nobody\"}")) {
                assertEquals(400, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertTrue(json.get("error").asText().contains("title"));
            }
        });
    }

    @Test
    void createBookWithoutAuthorReturns400() {
        JavalinTest.test(app, (server, client) -> {
            try (Response res = client.post("/books", "{\"title\":\"Untitled\"}")) {
                assertEquals(400, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertTrue(json.get("error").asText().contains("author"));
            }
        });
    }

    @Test
    void getMissingBookReturns404() {
        JavalinTest.test(app, (server, client) -> {
            try (Response res = client.get("/books/9999")) {
                assertEquals(404, res.code());
            }
        });
    }

    @Test
    void listFiltersByAuthor() throws IOException {
        JavalinTest.test(app, (server, client) -> {
            client.post("/books", "{\"title\":\"A\",\"author\":\"Alice\"}").close();
            client.post("/books", "{\"title\":\"B\",\"author\":\"Bob\"}").close();
            client.post("/books", "{\"title\":\"C\",\"author\":\"Alice\"}").close();

            try (Response res = client.get("/books?author=Alice")) {
                assertEquals(200, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertEquals(2, json.size());
                for (JsonNode node : json) {
                    assertEquals("Alice", node.get("author").asText());
                }
            }

            try (Response res = client.get("/books")) {
                JsonNode json = MAPPER.readTree(res.body().string());
                assertEquals(3, json.size());
            }
        });
    }

    @Test
    void updateBookChangesFields() throws IOException {
        JavalinTest.test(app, (server, client) -> {
            long id;
            try (Response res = client.post("/books", "{\"title\":\"Old\",\"author\":\"Author\"}")) {
                id = MAPPER.readTree(res.body().string()).get("id").asLong();
            }

            try (Response res = client.put("/books/" + id,
                    "{\"title\":\"New\",\"author\":\"Author\",\"year\":2020}")) {
                assertEquals(200, res.code());
                JsonNode json = MAPPER.readTree(res.body().string());
                assertEquals("New", json.get("title").asText());
                assertEquals(2020, json.get("year").asInt());
            }

            try (Response res = client.get("/books/" + id)) {
                JsonNode json = MAPPER.readTree(res.body().string());
                assertEquals("New", json.get("title").asText());
            }
        });
    }

    @Test
    void deleteBookRemovesIt() throws IOException {
        JavalinTest.test(app, (server, client) -> {
            long id;
            try (Response res = client.post("/books", "{\"title\":\"Temp\",\"author\":\"Author\"}")) {
                id = MAPPER.readTree(res.body().string()).get("id").asLong();
            }

            try (Response res = client.delete("/books/" + id)) {
                assertEquals(204, res.code());
            }

            try (Response res = client.get("/books/" + id)) {
                assertEquals(404, res.code());
            }
        });
    }
}
