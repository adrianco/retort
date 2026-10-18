package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * HTTP front end for {@link BookRepository} using the JDK's built-in HTTP server.
 */
public class BookServer {

    private static final String JSON = "application/json; charset=utf-8";

    private final ObjectMapper mapper = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    private final BookRepository repository;
    private final HttpServer server;
    private final ExecutorService executor;

    /**
     * @param port       TCP port to bind; use 0 for an ephemeral port
     * @param repository storage backend, which the caller owns and closes
     */
    public BookServer(int port, BookRepository repository) throws IOException {
        this.repository = repository;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        this.executor = Executors.newFixedThreadPool(4);
        this.server.createContext("/", this::handle);
        this.server.setExecutor(executor);
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
        executor.shutdownNow();
    }

    public int port() {
        return server.getAddress().getPort();
    }

    private void handle(HttpExchange exchange) throws IOException {
        try {
            route(exchange);
        } catch (ValidationFailure e) {
            sendJson(exchange, 400, Map.of("error", "Validation failed", "details", e.details()));
        } catch (BadRequest e) {
            sendJson(exchange, 400, Map.of("error", e.getMessage()));
        } catch (MethodNotAllowed e) {
            sendJson(exchange, 405, Map.of("error", e.getMessage()));
        } catch (SQLException e) {
            sendJson(exchange, 500, Map.of("error", "Database error"));
        } catch (RuntimeException e) {
            sendJson(exchange, 500, Map.of("error", "Internal server error"));
        } finally {
            exchange.close();
        }
    }

    private void route(HttpExchange exchange) throws IOException, SQLException {
        URI uri = exchange.getRequestURI();
        String path = uri.getPath();
        String method = exchange.getRequestMethod();
        if (path.length() > 1 && path.endsWith("/")) {
            path = path.substring(0, path.length() - 1);
        }

        if (path.equals("/health")) {
            requireMethod(method, "GET");
            sendJson(exchange, 200, Map.of("status", "ok"));
            return;
        }

        if (path.equals("/books")) {
            switch (method) {
                case "GET" -> listBooks(exchange);
                case "POST" -> createBook(exchange);
                default -> throw new MethodNotAllowed();
            }
            return;
        }

        if (path.startsWith("/books/")) {
            long id = parseId(path.substring("/books/".length()));
            switch (method) {
                case "GET" -> getBook(exchange, id);
                case "PUT" -> updateBook(exchange, id);
                case "DELETE" -> deleteBook(exchange, id);
                default -> throw new MethodNotAllowed();
            }
            return;
        }

        sendJson(exchange, 404, Map.of("error", "Not found"));
    }

    private void listBooks(HttpExchange exchange) throws IOException, SQLException {
        String author = queryParam(exchange.getRequestURI().getRawQuery(), "author");
        sendJson(exchange, 200, repository.findAll(author));
    }

    private void createBook(HttpExchange exchange) throws IOException, SQLException {
        BookRequest request = validatedBody(exchange);
        Book created = repository.insert(request);
        exchange.getResponseHeaders().set("Location", "/books/" + created.id());
        sendJson(exchange, 201, created);
    }

    private void getBook(HttpExchange exchange, long id) throws IOException, SQLException {
        Optional<Book> book = repository.findById(id);
        if (book.isEmpty()) {
            sendNotFound(exchange, id);
        } else {
            sendJson(exchange, 200, book.get());
        }
    }

    private void updateBook(HttpExchange exchange, long id) throws IOException, SQLException {
        BookRequest request = validatedBody(exchange);
        Optional<Book> updated = repository.update(id, request);
        if (updated.isEmpty()) {
            sendNotFound(exchange, id);
        } else {
            sendJson(exchange, 200, updated.get());
        }
    }

    private void deleteBook(HttpExchange exchange, long id) throws IOException, SQLException {
        if (repository.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
        } else {
            sendNotFound(exchange, id);
        }
    }

    private BookRequest validatedBody(HttpExchange exchange) throws IOException {
        byte[] bytes;
        try (InputStream in = exchange.getRequestBody()) {
            bytes = in.readAllBytes();
        }
        if (bytes.length == 0) {
            throw new BadRequest("Request body is required");
        }
        BookRequest request;
        try {
            request = mapper.readValue(bytes, BookRequest.class);
        } catch (JsonProcessingException e) {
            throw new BadRequest("Malformed JSON body: " + e.getOriginalMessage());
        }
        try {
            return BookValidator.validate(request);
        } catch (BookValidator.ValidationException e) {
            throw new ValidationFailure(e.errors());
        }
    }

    private static long parseId(String raw) {
        try {
            long id = Long.parseLong(raw);
            if (id > 0) {
                return id;
            }
        } catch (NumberFormatException ignored) {
            // fall through to the error below
        }
        throw new BadRequest("Book id must be a positive integer");
    }

    private static void requireMethod(String actual, String expected) {
        if (!expected.equals(actual)) {
            throw new MethodNotAllowed();
        }
    }

    static String queryParam(String rawQuery, String name) {
        if (rawQuery == null) {
            return null;
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq < 0 ? pair : pair.substring(0, eq);
            if (key.equals(name)) {
                String value = eq < 0 ? "" : pair.substring(eq + 1);
                return java.net.URLDecoder.decode(value, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private void sendNotFound(HttpExchange exchange, long id) throws IOException {
        sendJson(exchange, 404, Map.of("error", "Book " + id + " not found"));
    }

    private void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] bytes = mapper.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", JSON);
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(bytes);
        }
    }

    private static final class BadRequest extends RuntimeException {
        BadRequest(String message) {
            super(message);
        }
    }

    private static final class MethodNotAllowed extends RuntimeException {
        MethodNotAllowed() {
            super("Method not allowed");
        }
    }

    private static final class ValidationFailure extends RuntimeException {
        private final List<String> details;

        ValidationFailure(List<String> details) {
            super(String.join("; ", details));
            this.details = details;
        }

        List<String> details() {
            return details;
        }
    }
}
