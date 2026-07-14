package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class BookApiIntegrationTest {

    private ApiServer server;
    private BookRepository repository;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        // Fresh in-memory database per test, held open by the repository's connection.
        repository = new BookRepository("jdbc:sqlite::memory:");
        BookService service = new BookService(repository);
        server = new ApiServer(0, service);
        server.start();
        client = HttpClient.newHttpClient();
        base = "http://localhost:" + server.port();
    }

    @AfterEach
    void tearDown() {
        server.stop();
        repository.close();
    }

    @Test
    void healthCheckReturnsOk() throws Exception {
        HttpResponse<String> res = get("/health");
        assertEquals(200, res.statusCode());
        assertEquals("ok", asMap(res.body()).get("status"));
    }

    @Test
    void createReturns201AndAssignsId() throws Exception {
        HttpResponse<String> res = post("/books",
            "{\"title\":\"Dune\",\"author\":\"Herbert\",\"year\":1965,\"isbn\":\"123\"}");
        assertEquals(201, res.statusCode());
        Map<String, Object> book = asMap(res.body());
        assertNotNull(book.get("id"));
        assertEquals("Dune", book.get("title"));
        assertEquals("Herbert", book.get("author"));
        assertEquals(1965.0, ((Number) book.get("year")).doubleValue());
        assertEquals("123", book.get("isbn"));
    }

    @Test
    void createWithoutTitleReturns400() throws Exception {
        HttpResponse<String> res = post("/books", "{\"author\":\"Herbert\"}");
        assertEquals(400, res.statusCode());
        assertTrue(((String) asMap(res.body()).get("error")).contains("title"));
    }

    @Test
    void createWithoutAuthorReturns400() throws Exception {
        HttpResponse<String> res = post("/books", "{\"title\":\"Dune\"}");
        assertEquals(400, res.statusCode());
        assertTrue(((String) asMap(res.body()).get("error")).contains("author"));
    }

    @Test
    void createWithMalformedJsonReturns400() throws Exception {
        HttpResponse<String> res = post("/books", "{not json");
        assertEquals(400, res.statusCode());
    }

    @Test
    void getByIdReturnsBookOr404() throws Exception {
        long id = createBook("Dune", "Herbert");
        HttpResponse<String> found = get("/books/" + id);
        assertEquals(200, found.statusCode());
        assertEquals("Dune", asMap(found.body()).get("title"));

        HttpResponse<String> missing = get("/books/99999");
        assertEquals(404, missing.statusCode());
    }

    @Test
    void listReturnsAllBooks() throws Exception {
        createBook("Dune", "Herbert");
        createBook("Hyperion", "Simmons");
        HttpResponse<String> res = get("/books");
        assertEquals(200, res.statusCode());
        // Two JSON objects in the array.
        assertEquals(2, countOccurrences(res.body(), "\"title\""));
    }

    @Test
    void listFiltersByAuthor() throws Exception {
        createBook("Dune", "Herbert");
        createBook("Dune Messiah", "Herbert");
        createBook("Hyperion", "Simmons");

        HttpResponse<String> res = get("/books?author=Herbert");
        assertEquals(200, res.statusCode());
        assertEquals(2, countOccurrences(res.body(), "\"author\":\"Herbert\""));
        assertEquals(0, countOccurrences(res.body(), "Simmons"));
    }

    @Test
    void updateModifiesBookOr404() throws Exception {
        long id = createBook("Dune", "Herbert");
        HttpResponse<String> res = put("/books/" + id,
            "{\"title\":\"Dune (Updated)\",\"author\":\"Frank Herbert\",\"year\":1965}");
        assertEquals(200, res.statusCode());
        Map<String, Object> book = asMap(res.body());
        assertEquals("Dune (Updated)", book.get("title"));
        assertEquals("Frank Herbert", book.get("author"));

        HttpResponse<String> missing = put("/books/99999", "{\"title\":\"X\",\"author\":\"Y\"}");
        assertEquals(404, missing.statusCode());
    }

    @Test
    void updateWithInvalidBodyReturns400() throws Exception {
        long id = createBook("Dune", "Herbert");
        HttpResponse<String> res = put("/books/" + id, "{\"author\":\"Herbert\"}");
        assertEquals(400, res.statusCode());
    }

    @Test
    void deleteRemovesBookOr404() throws Exception {
        long id = createBook("Dune", "Herbert");
        HttpResponse<String> deleted = delete("/books/" + id);
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> afterDelete = get("/books/" + id);
        assertEquals(404, afterDelete.statusCode());

        HttpResponse<String> missing = delete("/books/" + id);
        assertEquals(404, missing.statusCode());
    }

    @Test
    void unknownMethodOnCollectionReturns405() throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + "/books"))
            .method("PATCH", HttpRequest.BodyPublishers.noBody())
            .build();
        HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
        assertEquals(405, res.statusCode());
    }

    // ----- helpers -------------------------------------------------------

    private long createBook(String title, String author) throws Exception {
        HttpResponse<String> res = post("/books",
            "{\"title\":\"" + title + "\",\"author\":\"" + author + "\"}");
        assertEquals(201, res.statusCode());
        return ((Number) asMap(res.body()).get("id")).longValue();
    }

    private HttpResponse<String> get(String path) throws Exception {
        return client.send(
            HttpRequest.newBuilder(URI.create(base + path)).GET().build(),
            HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> post(String path, String body) throws Exception {
        return client.send(
            HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build(),
            HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> put(String path, String body) throws Exception {
        return client.send(
            HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json")
                .PUT(HttpRequest.BodyPublishers.ofString(body)).build(),
            HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> delete(String path) throws Exception {
        return client.send(
            HttpRequest.newBuilder(URI.create(base + path)).DELETE().build(),
            HttpResponse.BodyHandlers.ofString());
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(String json) {
        return (Map<String, Object>) Json.parse(json);
    }

    private static int countOccurrences(String haystack, String needle) {
        int count = 0;
        int idx = 0;
        while ((idx = haystack.indexOf(needle, idx)) != -1) {
            count++;
            idx += needle.length();
        }
        return count;
    }
}
