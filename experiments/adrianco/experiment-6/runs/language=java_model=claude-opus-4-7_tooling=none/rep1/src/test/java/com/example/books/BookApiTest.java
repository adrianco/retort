package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse;
import java.net.http.HttpResponse.BodyHandlers;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class BookApiTest {

    private static App app;
    private static HttpClient client;
    private static String baseUrl;
    private static Path dbFile;
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @BeforeAll
    static void setUp() throws Exception {
        dbFile = Files.createTempFile("books-test-", ".db");
        Files.deleteIfExists(dbFile);
        app = new App("jdbc:sqlite:" + dbFile.toAbsolutePath()).start(0);
        baseUrl = "http://localhost:" + app.port();
        client = HttpClient.newHttpClient();
    }

    @AfterAll
    static void tearDown() throws Exception {
        if (app != null) app.stop();
        if (dbFile != null) Files.deleteIfExists(dbFile);
    }

    private HttpResponse<String> send(HttpRequest req) throws Exception {
        return client.send(req, BodyHandlers.ofString());
    }

    private HttpRequest.Builder req(String path) {
        return HttpRequest.newBuilder(URI.create(baseUrl + path))
                .header("Content-Type", "application/json");
    }

    @Test
    @Order(1)
    void healthEndpointReturnsOk() throws Exception {
        HttpResponse<String> resp = send(req("/health").GET().build());
        assertEquals(200, resp.statusCode());
        JsonNode body = MAPPER.readTree(resp.body());
        assertEquals("ok", body.get("status").asText());
    }

    @Test
    @Order(2)
    void createBookReturns201AndAssignsId() throws Exception {
        String payload = "{\"title\":\"The Hobbit\",\"author\":\"Tolkien\",\"year\":1937,\"isbn\":\"978-0\"}";
        HttpResponse<String> resp = send(req("/books").POST(BodyPublishers.ofString(payload)).build());
        assertEquals(201, resp.statusCode());
        JsonNode body = MAPPER.readTree(resp.body());
        assertNotNull(body.get("id"));
        assertTrue(body.get("id").asLong() > 0);
        assertEquals("The Hobbit", body.get("title").asText());
        assertEquals("Tolkien", body.get("author").asText());
        assertEquals(1937, body.get("year").asInt());
    }

    @Test
    @Order(3)
    void createBookValidatesRequiredFields() throws Exception {
        String payload = "{\"title\":\"\",\"author\":\"\"}";
        HttpResponse<String> resp = send(req("/books").POST(BodyPublishers.ofString(payload)).build());
        assertEquals(400, resp.statusCode());
        JsonNode body = MAPPER.readTree(resp.body());
        assertTrue(body.has("error"));
    }

    @Test
    @Order(4)
    void listBooksFiltersByAuthor() throws Exception {
        send(req("/books").POST(BodyPublishers.ofString(
                "{\"title\":\"A\",\"author\":\"AuthorX\"}")).build());
        send(req("/books").POST(BodyPublishers.ofString(
                "{\"title\":\"B\",\"author\":\"AuthorY\"}")).build());

        HttpResponse<String> resp = send(req("/books?author=AuthorX").GET().build());
        assertEquals(200, resp.statusCode());
        JsonNode arr = MAPPER.readTree(resp.body());
        assertTrue(arr.isArray());
        assertTrue(arr.size() >= 1);
        for (JsonNode n : arr) {
            assertEquals("AuthorX", n.get("author").asText());
        }
    }

    @Test
    @Order(5)
    void getUpdateDeleteRoundTrip() throws Exception {
        HttpResponse<String> create = send(req("/books").POST(BodyPublishers.ofString(
                "{\"title\":\"Old\",\"author\":\"Someone\",\"year\":2000}")).build());
        long id = MAPPER.readTree(create.body()).get("id").asLong();

        HttpResponse<String> get = send(req("/books/" + id).GET().build());
        assertEquals(200, get.statusCode());
        assertEquals("Old", MAPPER.readTree(get.body()).get("title").asText());

        HttpResponse<String> put = send(req("/books/" + id).PUT(BodyPublishers.ofString(
                "{\"title\":\"New\",\"author\":\"Someone\",\"year\":2024}")).build());
        assertEquals(200, put.statusCode());
        assertEquals("New", MAPPER.readTree(put.body()).get("title").asText());

        HttpResponse<String> del = send(req("/books/" + id).DELETE().build());
        assertEquals(204, del.statusCode());

        HttpResponse<String> missing = send(req("/books/" + id).GET().build());
        assertEquals(404, missing.statusCode());
    }

    @Test
    @Order(6)
    void getReturns404ForUnknownId() throws Exception {
        HttpResponse<String> resp = send(req("/books/99999999").GET().build());
        assertEquals(404, resp.statusCode());
    }
}
