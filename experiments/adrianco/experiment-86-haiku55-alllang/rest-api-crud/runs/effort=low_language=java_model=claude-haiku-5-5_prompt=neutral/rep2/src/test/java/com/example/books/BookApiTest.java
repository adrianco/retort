package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end tests: real HTTP server on an ephemeral port, real SQLite file. */
class BookApiTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    @TempDir
    Path tempDir;

    private BookRepository repository;
    private BookServer server;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws IOException {
        repository = new BookRepository("jdbc:sqlite:" + tempDir.resolve("test.db"));
        server = new BookServer(repository);
        int port = server.start(0);
        base = "http://localhost:" + port;
        client = HttpClient.newHttpClient();
    }

    @AfterEach
    void tearDown() {
        server.stop();
        repository.close();
    }

    @Test
    void healthEndpointReportsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("ok", JSON.readTree(res.body()).get("status").asText());
    }

    @Test
    void createReturns201WithIdAndStoresBook() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"9780441172719\"}");
        assertEquals(201, res.statusCode());
        JsonNode body = JSON.readTree(res.body());
        assertTrue(body.get("id").asLong() > 0);
        assertEquals("Dune", body.get("title").asText());
        assertEquals("Frank Herbert", body.get("author").asText());
        assertEquals(1965, body.get("year").asInt());
        assertEquals("9780441172719", body.get("isbn").asText());

        HttpResponse<String> fetched = send("GET", "/books/" + body.get("id").asLong(), null);
        assertEquals(200, fetched.statusCode());
        assertEquals("Dune", JSON.readTree(fetched.body()).get("title").asText());
    }

    @Test
    void createIgnoresClientSuppliedId() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"id\":999,\"title\":\"Emma\",\"author\":\"Jane Austen\"}");
        assertEquals(201, res.statusCode());
        assertTrue(JSON.readTree(res.body()).get("id").asLong() != 999L);
    }

    @Test
    void createRejectsMissingTitleOrAuthor() throws Exception {
        HttpResponse<String> noTitle = send("POST", "/books", "{\"author\":\"X\"}");
        assertEquals(400, noTitle.statusCode());
        assertTrue(noTitle.body().contains("title is required"));

        HttpResponse<String> blankAuthor = send("POST", "/books", "{\"title\":\"T\",\"author\":\"   \"}");
        assertEquals(400, blankAuthor.statusCode());
        assertTrue(blankAuthor.body().contains("author is required"));
    }

    @Test
    void createRejectsBadYearAndIsbn() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"T\",\"author\":\"A\",\"year\":-5,\"isbn\":\"abc\"}");
        assertEquals(400, res.statusCode());
        assertTrue(res.body().contains("year must be between"));
        assertTrue(res.body().contains("isbn must be a valid ISBN"));
    }

    @Test
    void createRejectsMalformedJsonAndEmptyBody() throws Exception {
        assertEquals(400, send("POST", "/books", "{not json").statusCode());
        assertEquals(400, send("POST", "/books", null).statusCode());
        assertEquals(400, send("POST", "/books", "{\"title\":\"T\",\"author\":\"A\",\"year\":\"abc\"}").statusCode());
    }

    @Test
    void listReturnsAllAndSupportsAuthorFilter() throws Exception {
        send("POST", "/books", "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}");
        send("POST", "/books", "{\"title\":\"Emma\",\"author\":\"Jane Austen\"}");
        send("POST", "/books", "{\"title\":\"Children of Dune\",\"author\":\"frank herbert\"}");

        JsonNode all = JSON.readTree(send("GET", "/books", null).body());
        assertEquals(3, all.size());

        JsonNode filtered = JSON.readTree(send("GET", "/books?author=Frank%20Herbert", null).body());
        assertEquals(2, filtered.size());
        for (JsonNode b : filtered) {
            assertTrue(b.get("author").asText().equalsIgnoreCase("Frank Herbert"));
        }

        JsonNode none = JSON.readTree(send("GET", "/books?author=Nobody", null).body());
        assertEquals(0, none.size());
    }

    @Test
    void getUnknownIdReturns404() throws Exception {
        HttpResponse<String> res = send("GET", "/books/12345", null);
        assertEquals(404, res.statusCode());
        assertEquals("book not found", JSON.readTree(res.body()).get("error").asText());
    }

    @Test
    void getNonNumericIdReturns400() throws Exception {
        assertEquals(400, send("GET", "/books/abc", null).statusCode());
    }

    @Test
    void updateReplacesFieldsAndValidates() throws Exception {
        long id = createBook("Old Title", "Old Author");

        HttpResponse<String> res = send("PUT", "/books/" + id,
                "{\"title\":\"New Title\",\"author\":\"New Author\",\"year\":2001}");
        assertEquals(200, res.statusCode());
        JsonNode body = JSON.readTree(res.body());
        assertEquals("New Title", body.get("title").asText());
        assertEquals(2001, body.get("year").asInt());

        JsonNode stored = JSON.readTree(send("GET", "/books/" + id, null).body());
        assertEquals("New Author", stored.get("author").asText());

        assertEquals(400, send("PUT", "/books/" + id, "{\"title\":\"\",\"author\":\"A\"}").statusCode());
        assertEquals(404, send("PUT", "/books/98765", "{\"title\":\"T\",\"author\":\"A\"}").statusCode());
    }

    @Test
    void deleteRemovesBook() throws Exception {
        long id = createBook("Gone", "Soon");

        HttpResponse<String> res = send("DELETE", "/books/" + id, null);
        assertEquals(204, res.statusCode());
        assertEquals("", res.body());

        assertEquals(404, send("GET", "/books/" + id, null).statusCode());
        assertEquals(404, send("DELETE", "/books/" + id, null).statusCode());
    }

    @Test
    void unknownRoutesAndMethodsAreRejected() throws Exception {
        assertEquals(404, send("GET", "/nope", null).statusCode());
        assertEquals(404, send("GET", "/books/1/extra", null).statusCode());

        HttpResponse<String> res = send("PATCH", "/books", null);
        assertEquals(405, res.statusCode());
        assertNotNull(res.headers().firstValue("Allow").orElse(null));

        assertEquals(405, send("POST", "/health", null).statusCode());
    }

    @Test
    void dataPersistsAcrossRepositoryReopen() throws Exception {
        long id = createBook("Persistent", "Author");
        server.stop();
        repository.close();

        repository = new BookRepository("jdbc:sqlite:" + tempDir.resolve("test.db"));
        server = new BookServer(repository);
        int port = server.start(0);
        base = "http://localhost:" + port;

        HttpResponse<String> res = send("GET", "/books/" + id, null);
        assertEquals(200, res.statusCode());
        assertEquals("Persistent", JSON.readTree(res.body()).get("title").asText());
    }

    private long createBook(String title, String author) throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"" + title + "\",\"author\":\"" + author + "\"}");
        assertEquals(201, res.statusCode());
        return JSON.readTree(res.body()).get("id").asLong();
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + path))
                .method(method, publisher)
                .header("Content-Type", "application/json")
                .build();
        return client.send(req, HttpResponse.BodyHandlers.ofString());
    }
}
