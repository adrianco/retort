package com.example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import org.junit.jupiter.api.*;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class BookApiTest {
    static Javalin app;
    static int port;
    static String base;
    static HttpClient http;
    static ObjectMapper mapper = new ObjectMapper();
    static Path dbFile;
    static long createdId;

    @BeforeAll
    static void setup() throws Exception {
        dbFile = Files.createTempFile("books", ".db");
        Files.deleteIfExists(dbFile);
        BookDao dao = new BookDao("jdbc:sqlite:" + dbFile.toAbsolutePath());
        port = freePort();
        app = App.start(dao, port);
        base = "http://localhost:" + port;
        http = HttpClient.newHttpClient();
    }

    @AfterAll
    static void teardown() throws IOException {
        if (app != null) app.stop();
        Files.deleteIfExists(dbFile);
    }

    static int freePort() throws IOException {
        try (var s = new java.net.ServerSocket(0)) { return s.getLocalPort(); }
    }

    HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json");
        HttpRequest.BodyPublisher pub = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        b.method(method, pub);
        return http.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    @Test @Order(1)
    void health() throws Exception {
        HttpResponse<String> r = send("GET", "/health", null);
        assertEquals(200, r.statusCode());
        assertTrue(r.body().contains("ok"));
    }

    @Test @Order(2)
    void createBook() throws Exception {
        String body = "{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"123\"}";
        HttpResponse<String> r = send("POST", "/books", body);
        assertEquals(201, r.statusCode());
        JsonNode n = mapper.readTree(r.body());
        assertTrue(n.get("id").asLong() > 0);
        assertEquals("Dune", n.get("title").asText());
        createdId = n.get("id").asLong();
    }

    @Test @Order(3)
    void createValidationFails() throws Exception {
        HttpResponse<String> r = send("POST", "/books", "{\"author\":\"X\"}");
        assertEquals(400, r.statusCode());
        assertTrue(r.body().contains("title"));
    }

    @Test @Order(4)
    void getById() throws Exception {
        HttpResponse<String> r = send("GET", "/books/" + createdId, null);
        assertEquals(200, r.statusCode());
        assertTrue(r.body().contains("Dune"));
    }

    @Test @Order(5)
    void listAndFilter() throws Exception {
        send("POST", "/books", "{\"title\":\"Foundation\",\"author\":\"Asimov\"}");
        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertTrue(mapper.readTree(all.body()).size() >= 2);
        HttpResponse<String> filt = send("GET", "/books?author=Asimov", null);
        JsonNode arr = mapper.readTree(filt.body());
        assertEquals(1, arr.size());
        assertEquals("Asimov", arr.get(0).get("author").asText());
    }

    @Test @Order(6)
    void updateAndDelete() throws Exception {
        String body = "{\"title\":\"Dune (Rev)\",\"author\":\"Herbert\",\"year\":1965}";
        HttpResponse<String> u = send("PUT", "/books/" + createdId, body);
        assertEquals(200, u.statusCode());
        assertTrue(u.body().contains("Rev"));

        HttpResponse<String> d = send("DELETE", "/books/" + createdId, null);
        assertEquals(204, d.statusCode());

        HttpResponse<String> g = send("GET", "/books/" + createdId, null);
        assertEquals(404, g.statusCode());
    }
}
