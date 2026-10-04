package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Integration tests: real HTTP server on a random port with an in-memory SQLite database. */
class AppTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String DUNE =
            "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}";

    private final HttpClient client = HttpClient.newHttpClient();
    private BookRepository repo;
    private Javalin app;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        repo = new BookRepository("jdbc:sqlite::memory:");
        app = App.create(repo).start(0);
        base = "http://localhost:" + app.port();
    }

    @AfterEach
    void tearDown() throws Exception {
        app.stop();
        repo.close();
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        HttpRequest request = HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json")
                .method(method, publisher)
                .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private static JsonNode json(HttpResponse<String> response) throws Exception {
        return MAPPER.readTree(response.body());
    }

    @Test
    void healthCheck() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", json(res).get("status").asText());
        assertTrue(res.headers().firstValue("Content-Type").orElse("").startsWith("application/json"));
    }

    @Test
    void createAndGetBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books", DUNE);
        assertEquals(201, created.statusCode());
        JsonNode book = json(created);
        assertTrue(book.get("id").asLong() > 0);
        assertEquals("Dune", book.get("title").asText());
        assertEquals("Frank Herbert", book.get("author").asText());
        assertEquals(1965, book.get("year").asInt());
        assertEquals("9780441172719", book.get("isbn").asText());

        HttpResponse<String> fetched = send("GET", "/books/" + book.get("id").asLong(), null);
        assertEquals(200, fetched.statusCode());
        assertEquals(book, json(fetched));
    }

    @Test
    void createWithOnlyRequiredFields() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(201, res.statusCode());
        assertTrue(json(res).get("year").isNull());
        assertTrue(json(res).get("isbn").isNull());
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"year\":2000}");
        assertEquals(400, res.statusCode());
        String details = json(res).get("details").toString();
        assertTrue(details.contains("title is required"));
        assertTrue(details.contains("author is required"));
        assertEquals(0, json(send("GET", "/books", null)).size());
    }

    @Test
    void createRejectsBlankTitleBadYearAndMalformedJson() throws Exception {
        assertEquals(400, send("POST", "/books", "{\"title\":\"  \",\"author\":\"A\"}").statusCode());
        assertEquals(400,
                send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"x\"}").statusCode());
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", "[]").statusCode());
        assertEquals(400, send("POST", "/books", "").statusCode());
    }

    @Test
    void listAndFilterByAuthor() throws Exception {
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
    void updateBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();

        HttpResponse<String> updated = send("PUT", "/books/" + id,
                "{\"title\":\"Dune Messiah\",\"author\":\"Frank Herbert\",\"year\":1969}");
        assertEquals(200, updated.statusCode());
        assertEquals("Dune Messiah", json(updated).get("title").asText());

        JsonNode fetched = json(send("GET", "/books/" + id, null));
        assertEquals("Dune Messiah", fetched.get("title").asText());
        assertEquals(1969, fetched.get("year").asInt());
        assertTrue(fetched.get("isbn").isNull());
    }

    @Test
    void updateValidatesAndReturns404ForUnknownId() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();
        assertEquals(400, send("PUT", "/books/" + id, "{\"title\":\"No author\"}").statusCode());
        assertEquals("Dune", json(send("GET", "/books/" + id, null)).get("title").asText());
        assertEquals(404, send("PUT", "/books/9999", DUNE).statusCode());
    }

    @Test
    void deleteBook() throws Exception {
        long id = json(send("POST", "/books", DUNE)).get("id").asLong();
        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownAndInvalidIds() throws Exception {
        HttpResponse<String> missing = send("GET", "/books/12345", null);
        assertEquals(404, missing.statusCode());
        assertTrue(json(missing).has("error"));
        assertEquals("Book 12345 not found", json(missing).get("error").asText());
        assertEquals(400, send("GET", "/books/abc", null).statusCode());

        HttpResponse<String> noRoute = send("GET", "/nope", null);
        assertEquals(404, noRoute.statusCode());
        assertEquals("Not found", json(noRoute).get("error").asText());
    }
}
