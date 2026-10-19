package com.example.books;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * End-to-end tests: boots the real HTTP server on an ephemeral port with a
 * throwaway SQLite database and exercises every endpoint over the wire.
 */
class BookApiIntegrationTest {

    private BookStore store;
    private HttpServer server;
    private HttpClient client;
    private String base;

    @BeforeEach
    void setUp() throws Exception {
        String db = Files.createTempDirectory("bookapi-test").resolve("test.db").toString();
        store = new BookStore("jdbc:sqlite:" + db);
        server = HttpServer.create(new java.net.InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", new BookApiHandler(store));
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.start();
        base = "http://127.0.0.1:" + server.getAddress().getPort();
        client = HttpClient.newHttpClient();
    }

    @AfterEach
    void tearDown() throws Exception {
        server.stop(0);
        store.close();
    }

    private HttpResponse<String> send(String method, String path, String body) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(base + path)).method(method,
                body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body));
        if (body != null) {
            builder.header("Content-Type", "application/json");
        }
        return client.send(builder.build(), HttpResponse.BodyHandlers.ofString());
    }

    @Test
    void healthEndpointReturnsOk() throws Exception {
        HttpResponse<String> res = send("GET", "/health", null);
        assertEquals(200, res.statusCode());
        assertEquals("application/json", res.headers().firstValue("Content-Type").orElse(""));
        assertTrue(res.body().contains("\"status\":\"ok\""));
    }

    @Test
    void createBookReturns201WithBookAndLocation() throws Exception {
        HttpResponse<String> res = send("POST", "/books",
                "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0441172719\"}");
        assertEquals(201, res.statusCode());
        assertNotNull(res.headers().firstValue("Location"));
        assertTrue(res.body().contains("\"title\":\"Dune\""));
        assertTrue(res.body().contains("\"author\":\"Frank Herbert\""));
        assertTrue(res.body().contains("\"year\":1965"));
        assertTrue(res.body().contains("\"isbn\":\"978-0441172719\""));
        assertTrue(res.body().contains("\"id\":"));
    }

    @Test
    void createBookAcceptsOptionalFieldsOmitted() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"Moby-Dick\",\"author\":\"Melville\"}");
        assertEquals(201, res.statusCode());
        assertTrue(res.body().contains("\"year\":null"));
        assertTrue(res.body().contains("\"isbn\":null"));
    }

    @Test
    void createBookRejectsMissingTitle() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"author\":\"Someone\"}");
        assertEquals(400, res.statusCode());
        assertTrue(res.body().contains("title"));
    }

    @Test
    void createBookRejectsMissingAuthor() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"Untitled\"}");
        assertEquals(400, res.statusCode());
        assertTrue(res.body().contains("author"));
    }

    @Test
    void createBookRejectsBlankTitle() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{\"title\":\"   \",\"author\":\"Someone\"}");
        assertEquals(400, res.statusCode());
    }

    @Test
    void createBookRejectsMalformedJson() throws Exception {
        HttpResponse<String> res = send("POST", "/books", "{not json");
        assertEquals(400, res.statusCode());
        assertTrue(res.body().contains("error"));
    }

    @Test
    void listBooksReturnsAllAndFiltersByAuthor() throws Exception {
        send("POST", "/books", "{\"title\":\"A\",\"author\":\"Alpha\"}");
        send("POST", "/books", "{\"title\":\"B\",\"author\":\"Beta\"}");
        send("POST", "/books", "{\"title\":\"C\",\"author\":\"Alpha\"}");

        HttpResponse<String> all = send("GET", "/books", null);
        assertEquals(200, all.statusCode());
        assertTrue(all.body().contains("\"title\":\"A\""));
        assertTrue(all.body().contains("\"title\":\"B\""));
        assertTrue(all.body().contains("\"title\":\"C\""));

        HttpResponse<String> filtered = send("GET", "/books?author=Alpha", null);
        assertEquals(200, filtered.statusCode());
        assertTrue(filtered.body().contains("\"title\":\"A\""));
        assertTrue(filtered.body().contains("\"title\":\"C\""));
        assertTrue(!filtered.body().contains("\"title\":\"B\""));
    }

    @Test
    void getBookReturnsBookOr404() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Neuromancer\",\"author\":\"Gibson\",\"year\":1984}");
        String id = created.body().replaceAll(".*\"id\":(\\d+).*", "$1");

        HttpResponse<String> got = send("GET", "/books/" + id, null);
        assertEquals(200, got.statusCode());
        assertTrue(got.body().contains("\"title\":\"Neuromancer\""));

        HttpResponse<String> missing = send("GET", "/books/99999", null);
        assertEquals(404, missing.statusCode());
        assertTrue(missing.body().contains("error"));
    }

    @Test
    void updateBookReplacesRequiredFieldsAndKeepsOmittedOptionals() throws Exception {
        HttpResponse<String> created = send("POST", "/books",
                "{\"title\":\"Old\",\"author\":\"Writer\",\"year\":1999,\"isbn\":\"111\"}");
        String id = created.body().replaceAll(".*\"id\":(\\d+).*", "$1");

        HttpResponse<String> updated = send("PUT", "/books/" + id, "{\"title\":\"New\",\"author\":\"Editor\"}");
        assertEquals(200, updated.statusCode());
        assertTrue(updated.body().contains("\"title\":\"New\""));
        assertTrue(updated.body().contains("\"author\":\"Editor\""));
        assertTrue(updated.body().contains("\"year\":1999"));
        assertTrue(updated.body().contains("\"isbn\":\"111\""));

        // persisted
        HttpResponse<String> got = send("GET", "/books/" + id, null);
        assertTrue(got.body().contains("\"title\":\"New\""));
    }

    @Test
    void updateBookRejectsMissingAuthorAndUnknownId() throws Exception {
        HttpResponse<String> bad = send("PUT", "/books/1", "{\"title\":\"Only title\"}");
        assertEquals(400, bad.statusCode());

        HttpResponse<String> missing = send("PUT", "/books/99999", "{\"title\":\"T\",\"author\":\"A\"}");
        assertEquals(404, missing.statusCode());
    }

    @Test
    void deleteBookReturns204Then404() throws Exception {
        HttpResponse<String> created = send("POST", "/books", "{\"title\":\"Temp\",\"author\":\"Ghost\"}");
        String id = created.body().replaceAll(".*\"id\":(\\d+).*", "$1");

        HttpResponse<String> deleted = send("DELETE", "/books/" + id, null);
        assertEquals(204, deleted.statusCode());

        HttpResponse<String> gone = send("GET", "/books/" + id, null);
        assertEquals(404, gone.statusCode());

        HttpResponse<String> again = send("DELETE", "/books/" + id, null);
        assertEquals(404, again.statusCode());
    }

    @Test
    void wrongMethodReturns405WithAllowHeader() throws Exception {
        HttpResponse<String> res = send("PATCH", "/books", null);
        assertEquals(405, res.statusCode());
        assertTrue(res.headers().firstValue("Allow").orElse("").contains("GET"));
    }

    @Test
    void unknownPathReturns404() throws Exception {
        HttpResponse<String> res = send("GET", "/nope", null);
        assertEquals(404, res.statusCode());
    }
}
