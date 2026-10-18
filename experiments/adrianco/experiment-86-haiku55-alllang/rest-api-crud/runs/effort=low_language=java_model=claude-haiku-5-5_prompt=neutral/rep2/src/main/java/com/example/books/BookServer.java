package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * HTTP front end for the book collection. Uses the JDK's built-in {@link HttpServer}
 * and returns JSON for every response.
 *
 * <pre>
 * GET    /health            liveness + database check
 * POST   /books             create (title, author required)
 * GET    /books             list, optional ?author= filter (case-insensitive)
 * GET    /books/{id}        fetch one
 * PUT    /books/{id}        full replacement (title, author required)
 * DELETE /books/{id}        delete
 * </pre>
 */
public class BookServer {

    private static final String JSON = "application/json; charset=utf-8";
    private static final String BOOKS_PREFIX = "/books";

    private final BookRepository repository;
    private final ObjectMapper mapper = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    private HttpServer server;

    public BookServer(BookRepository repository) {
        this.repository = repository;
    }

    /**
     * Starts listening on the given port (0 picks a free port).
     *
     * @return the port actually bound
     */
    public synchronized int start(int port) throws IOException {
        server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", this::dispatch);
        server.start();
        return server.getAddress().getPort();
    }

    public synchronized void stop() {
        if (server != null) {
            server.stop(0);
            server = null;
        }
    }

    private void dispatch(HttpExchange ex) throws IOException {
        try {
            route(ex);
        } catch (RuntimeException e) {
            sendError(ex, 500, "internal error");
        } finally {
            ex.close();
        }
    }

    private void route(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        String method = ex.getRequestMethod();

        if (path.equals("/health")) {
            if (!method.equals("GET")) {
                methodNotAllowed(ex, "GET");
                return;
            }
            handleHealth(ex);
            return;
        }

        if (path.equals(BOOKS_PREFIX)) {
            switch (method) {
                case "GET" -> handleList(ex);
                case "POST" -> handleCreate(ex);
                default -> methodNotAllowed(ex, "GET, POST");
            }
            return;
        }

        if (path.startsWith(BOOKS_PREFIX + "/")) {
            String idPart = path.substring(BOOKS_PREFIX.length() + 1);
            if (idPart.isEmpty() || idPart.contains("/")) {
                sendError(ex, 404, "not found");
                return;
            }
            long id;
            try {
                id = Long.parseLong(idPart);
            } catch (NumberFormatException e) {
                sendError(ex, 400, "id must be a number");
                return;
            }
            switch (method) {
                case "GET" -> handleGet(ex, id);
                case "PUT" -> handleUpdate(ex, id);
                case "DELETE" -> handleDelete(ex, id);
                default -> methodNotAllowed(ex, "GET, PUT, DELETE");
            }
            return;
        }

        sendError(ex, 404, "not found");
    }

    private void handleHealth(HttpExchange ex) throws IOException {
        if (repository.ping()) {
            sendJson(ex, 200, Map.of("status", "ok"));
        } else {
            sendJson(ex, 503, Map.of("status", "unavailable"));
        }
    }

    private void handleList(HttpExchange ex) throws IOException {
        String author = queryParam(ex, "author");
        sendJson(ex, 200, repository.findAll(author));
    }

    private void handleGet(HttpExchange ex, long id) throws IOException {
        Optional<Book> book = repository.findById(id);
        if (book.isEmpty()) {
            sendError(ex, 404, "book not found");
        } else {
            sendJson(ex, 200, book.get());
        }
    }

    private void handleCreate(HttpExchange ex) throws IOException {
        Optional<Book> input = readBook(ex);
        if (input.isEmpty()) {
            return;
        }
        Book book = input.get();
        List<String> errors = BookValidator.validate(book);
        if (!errors.isEmpty()) {
            sendValidationError(ex, errors);
            return;
        }
        // Any id supplied by the client is ignored; the database assigns it.
        Book created = repository.create(new Book(null, book.title(), book.author(), book.year(), book.isbn()));
        sendJson(ex, 201, created);
    }

    private void handleUpdate(HttpExchange ex, long id) throws IOException {
        Optional<Book> input = readBook(ex);
        if (input.isEmpty()) {
            return;
        }
        Book book = input.get();
        List<String> errors = BookValidator.validate(book);
        if (!errors.isEmpty()) {
            sendValidationError(ex, errors);
            return;
        }
        Book replacement = new Book(id, book.title(), book.author(), book.year(), book.isbn());
        if (!repository.update(id, replacement)) {
            sendError(ex, 404, "book not found");
        } else {
            sendJson(ex, 200, replacement);
        }
    }

    private void handleDelete(HttpExchange ex, long id) throws IOException {
        if (!repository.delete(id)) {
            sendError(ex, 404, "book not found");
        } else {
            ex.sendResponseHeaders(204, -1);
        }
    }

    /**
     * Parses the request body as a Book. Sends a 400 and returns empty if the body is
     * missing or is not valid JSON for a book.
     */
    private Optional<Book> readBook(HttpExchange ex) throws IOException {
        byte[] bytes;
        try (InputStream in = ex.getRequestBody()) {
            bytes = in.readAllBytes();
        }
        if (bytes.length == 0) {
            sendValidationError(ex, List.of("request body is required"));
            return Optional.empty();
        }
        try {
            return Optional.of(mapper.readValue(bytes, Book.class));
        } catch (JsonProcessingException e) {
            sendError(ex, 400, "malformed JSON body");
            return Optional.empty();
        }
    }

    private static String queryParam(HttpExchange ex, String name) {
        String query = ex.getRequestURI().getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq < 0 ? pair : pair.substring(0, eq);
            if (URLDecoder.decode(key, StandardCharsets.UTF_8).equals(name)) {
                String value = eq < 0 ? "" : pair.substring(eq + 1);
                return URLDecoder.decode(value, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private void methodNotAllowed(HttpExchange ex, String allow) throws IOException {
        ex.getResponseHeaders().set("Allow", allow);
        sendError(ex, 405, "method not allowed");
    }

    private void sendValidationError(HttpExchange ex, List<String> details) throws IOException {
        sendJson(ex, 400, Map.of("error", "validation failed", "details", details));
    }

    private void sendError(HttpExchange ex, int status, String message) throws IOException {
        sendJson(ex, status, Map.of("error", message));
    }

    private void sendJson(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = serialize(body);
        ex.getResponseHeaders().set("Content-Type", JSON);
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }

    private byte[] serialize(Object body) throws IOException {
        try {
            return mapper.writeValueAsBytes(body);
        } catch (JsonProcessingException e) {
            throw new IOException("failed to serialize response", e);
        }
    }
}
