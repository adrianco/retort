package com.example.books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
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

/**
 * HTTP layer for the book API, built on the JDK's built-in {@link HttpServer}.
 */
public class BookServer {

    private static final ObjectMapper JSON = new ObjectMapper();

    private final BookRepository repository;
    private final HttpServer server;

    /**
     * Creates the server and binds it to the given port without starting it.
     *
     * @param port       TCP port; 0 picks a free ephemeral port
     * @param repository storage backend
     */
    public BookServer(int port, BookRepository repository) throws IOException {
        this.repository = repository;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/books", this::handleBooks);
        server.createContext("/health", this::handleHealth);
        server.setExecutor(null);
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    /** @return the port the server is listening on */
    public int port() {
        return server.getAddress().getPort();
    }

    private void handleHealth(HttpExchange exchange) throws IOException {
        try (exchange) {
            if (!"GET".equals(exchange.getRequestMethod())) {
                sendError(exchange, 405, "method not allowed");
                return;
            }
            boolean up = repository.ping();
            sendJson(exchange, up ? 200 : 503,
                    Map.of("status", up ? "UP" : "DOWN"));
        }
    }

    private void handleBooks(HttpExchange exchange) throws IOException {
        try (exchange) {
            String path = exchange.getRequestURI().getPath();
            String method = exchange.getRequestMethod();
            if ("/books".equals(path) || "/books/".equals(path)) {
                switch (method) {
                    case "GET" -> listBooks(exchange);
                    case "POST" -> createBook(exchange);
                    default -> sendError(exchange, 405, "method not allowed");
                }
                return;
            }
            String idPart = path.substring("/books/".length());
            if (idPart.isEmpty() || idPart.contains("/")) {
                sendError(exchange, 404, "not found");
                return;
            }
            Long id = parseId(idPart);
            if (id == null) {
                sendError(exchange, 400, "book id must be a number");
                return;
            }
            switch (method) {
                case "GET" -> getBook(exchange, id);
                case "PUT" -> updateBook(exchange, id);
                case "DELETE" -> deleteBook(exchange, id);
                default -> sendError(exchange, 405, "method not allowed");
            }
        } catch (SQLException e) {
            sendError(exchange, 500, "database error");
        }
    }

    private void listBooks(HttpExchange exchange) throws IOException, SQLException {
        String author = queryParam(exchange.getRequestURI(), "author");
        List<Book> books = repository.findAll(author);
        sendJson(exchange, 200, books);
    }

    private void createBook(HttpExchange exchange) throws IOException, SQLException {
        Optional<BookInput> input = readBody(exchange);
        if (input.isEmpty()) {
            return;
        }
        Book created = repository.create(input.get());
        sendJson(exchange, 201, created);
    }

    private void getBook(HttpExchange exchange, long id) throws IOException, SQLException {
        Optional<Book> book = repository.findById(id);
        if (book.isEmpty()) {
            sendError(exchange, 404, "book not found");
        } else {
            sendJson(exchange, 200, book.get());
        }
    }

    private void updateBook(HttpExchange exchange, long id) throws IOException, SQLException {
        Optional<BookInput> input = readBody(exchange);
        if (input.isEmpty()) {
            return;
        }
        Optional<Book> updated = repository.update(id, input.get());
        if (updated.isEmpty()) {
            sendError(exchange, 404, "book not found");
        } else {
            sendJson(exchange, 200, updated.get());
        }
    }

    private void deleteBook(HttpExchange exchange, long id) throws IOException, SQLException {
        if (repository.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
        } else {
            sendError(exchange, 404, "book not found");
        }
    }

    /**
     * Parses and validates the JSON request body. On failure, writes a 400
     * response and returns empty.
     */
    private Optional<BookInput> readBody(HttpExchange exchange) throws IOException {
        BookInput input;
        try (InputStream in = exchange.getRequestBody()) {
            input = JSON.readValue(in, BookInput.class);
        } catch (JsonProcessingException e) {
            sendError(exchange, 400, "malformed JSON body");
            return Optional.empty();
        }
        if (input == null) {
            sendError(exchange, 400, "request body is required");
            return Optional.empty();
        }
        List<String> errors = input.validate();
        if (!errors.isEmpty()) {
            sendJson(exchange, 400, Map.of("error", "validation failed", "details", errors));
            return Optional.empty();
        }
        return Optional.of(input);
    }

    private static Long parseId(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String queryParam(URI uri, String name) {
        String query = uri.getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq < 0 ? pair : pair.substring(0, eq);
            if (key.equals(name)) {
                String value = eq < 0 ? "" : pair.substring(eq + 1);
                return java.net.URLDecoder.decode(value, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private static void sendError(HttpExchange exchange, int status, String message) throws IOException {
        sendJson(exchange, status, Map.of("error", message));
    }

    private static void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] bytes = JSON.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(bytes);
        }
    }
}
