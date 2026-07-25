package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BookApiTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static Connection conn;
    private static Javalin app;
    private static HttpClient client;
    private static String base;

    @BeforeAll
    static void startServer() throws Exception {
        conn = DriverManager.getConnection("jdbc:sqlite::memory:");
        app = App.create(new BookDao(conn)).start(0);
        client = HttpClient.newHttpClient();
        base = "http://localhost:" + app.port();
    }

    @AfterAll
    static void stopServer() throws Exception {
        app.stop();
        conn.close();
    }

    @BeforeEach
    void clearBooks() throws Exception {
        try (Statement st = conn.createStatement()) {
            st.execute("DELETE FROM books");
        }
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(base + path));
        if (body != null) {
            builder.method(method, HttpRequest.BodyPublishers.ofString(body))
                    .header("Content-Type", "application/json");
        } else {
            builder.method(method, HttpRequest.BodyPublishers.noBody());
        }
        return client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", MAPPER.readTree(res.body()).get("status").asText());
    }

    @Test
    void createAndFetchBook() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                """
                {"title":"Release It!","author":"Michael Nygard","year":2018,"isbn":"978-1680502398"}""");
        assertEquals(201, created.statusCode());
        JsonNode createdBook = MAPPER.readTree(created.body());
        int id = createdBook.get("id").asInt();
        assertEquals("Release It!", createdBook.get("title").asText());

        HttpResponse<String> fetched = send("GET", "/books/" + id, null);
        assertEquals(200, fetched.statusCode());
        JsonNode book = MAPPER.readTree(fetched.body());
        assertEquals("Michael Nygard", book.get("author").asText());
        assertEquals(2018, book.get("year").asInt());
        assertEquals("978-1680502398", book.get("isbn").asText());
    }

    @Test
    void createRejectsMissingTitleAndAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"year\":2020}");
        assertEquals(400, res.statusCode());
        String details = MAPPER.readTree(res.body()).get("details").toString();
        assertTrue(details.contains("title is required"));
        assertTrue(details.contains("author is required"));
    }

    @Test
    void createRejectsMalformedJson() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "not json");
        assertEquals(400, res.statusCode());
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        send("POST", "/books", "{\"title\":\"A\",\"author\":\"Alice\"}");
        send("POST", "/books", "{\"title\":\"B\",\"author\":\"Bob\"}");
        send("POST", "/books", "{\"title\":\"C\",\"author\":\"Alice\"}");

        JsonNode all = MAPPER.readTree(send("GET", "/books", null).body());
        assertEquals(3, all.size());

        JsonNode filtered = MAPPER.readTree(send("GET", "/books?author=Alice", null).body());
        assertEquals(2, filtered.size());
        for (JsonNode book : filtered) {
            assertEquals("Alice", book.get("author").asText());
        }
    }

    @Test
    void updateModifiesBookAndValidates() throws Exception {
        JsonNode created = MAPPER.readTree(send("POST", "/books",
                "{\"title\":\"Old\",\"author\":\"Someone\"}").body());
        int id = created.get("id").asInt();

        HttpResponse<String> updated = send("PUT", "/books/" + id,
                "{\"title\":\"New\",\"author\":\"Someone Else\",\"year\":1999}");
        assertEquals(200, updated.statusCode());

        JsonNode book = MAPPER.readTree(send("GET", "/books/" + id, null).body());
        assertEquals("New", book.get("title").asText());
        assertEquals("Someone Else", book.get("author").asText());
        assertEquals(1999, book.get("year").asInt());

        HttpResponse<String> invalid = send("PUT", "/books/" + id, "{\"title\":\"\"}");
        assertEquals(400, invalid.statusCode());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        JsonNode created = MAPPER.readTree(send("POST", "/books",
                "{\"title\":\"Doomed\",\"author\":\"Nobody\"}").body());
        int id = created.get("id").asInt();

        assertEquals(204, send("DELETE", "/books/" + id, null).statusCode());
        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void missingAndBadIdsReturnErrors() throws Exception {
        assertEquals(404, send("GET", "/books/99999", null).statusCode());
        assertEquals(404, send("PUT", "/books/99999",
                "{\"title\":\"X\",\"author\":\"Y\"}").statusCode());
        assertEquals(400, send("GET", "/books/abc", null).statusCode());
    }
}
