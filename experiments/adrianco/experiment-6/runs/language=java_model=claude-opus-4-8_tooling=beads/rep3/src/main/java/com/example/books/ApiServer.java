package com.example.books;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

/**
 * HTTP server exposing the Book collection REST API using the JDK's built-in
 * {@link HttpServer}.
 */
public final class ApiServer {

    private final HttpServer httpServer;
    private final BookService service;

    public ApiServer(int port, BookService service) throws IOException {
        this.service = service;
        this.httpServer = HttpServer.create(new InetSocketAddress(port), 0);
        this.httpServer.setExecutor(Executors.newFixedThreadPool(8));
        this.httpServer.createContext("/health", this::handleHealth);
        this.httpServer.createContext("/books", this::handleBooks);
    }

    public void start() {
        httpServer.start();
    }

    public void stop() {
        httpServer.stop(0);
    }

    /** Returns the actual bound port (useful when constructed with port 0). */
    public int port() {
        return httpServer.getAddress().getPort();
    }

    // ----- Handlers ------------------------------------------------------

    private void handleHealth(HttpExchange exchange) throws IOException {
        try {
            if (!"GET".equals(exchange.getRequestMethod())) {
                methodNotAllowed(exchange);
                return;
            }
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("status", "ok");
            sendJson(exchange, 200, body);
        } finally {
            exchange.close();
        }
    }

    private void handleBooks(HttpExchange exchange) throws IOException {
        try {
            route(exchange);
        } catch (ValidationException e) {
            sendError(exchange, 400, e.getMessage());
        } catch (Json.JsonException e) {
            sendError(exchange, 400, "invalid JSON: " + e.getMessage());
        } catch (Exception e) {
            sendError(exchange, 500, "internal error: " + e.getMessage());
        } finally {
            exchange.close();
        }
    }

    private void route(HttpExchange exchange) throws IOException {
        String method = exchange.getRequestMethod();
        URI uri = exchange.getRequestURI();
        String path = uri.getPath();

        // Strip the "/books" prefix to find the remaining path segment.
        String remainder = path.substring("/books".length());
        if (remainder.startsWith("/")) {
            remainder = remainder.substring(1);
        }

        if (remainder.isEmpty()) {
            // Collection endpoints: /books
            switch (method) {
                case "GET":
                    listBooks(exchange, uri);
                    return;
                case "POST":
                    createBook(exchange);
                    return;
                default:
                    methodNotAllowed(exchange);
                    return;
            }
        }

        // Item endpoints: /books/{id}
        if (remainder.contains("/")) {
            sendError(exchange, 404, "not found");
            return;
        }
        long id;
        try {
            id = Long.parseLong(remainder);
        } catch (NumberFormatException e) {
            sendError(exchange, 400, "invalid id: " + remainder);
            return;
        }

        switch (method) {
            case "GET":
                getBook(exchange, id);
                return;
            case "PUT":
                updateBook(exchange, id);
                return;
            case "DELETE":
                deleteBook(exchange, id);
                return;
            default:
                methodNotAllowed(exchange);
        }
    }

    private void listBooks(HttpExchange exchange, URI uri) throws IOException {
        String author = queryParam(uri.getRawQuery(), "author");
        List<Book> books = service.list(author);
        List<Object> payload = books.stream()
            .map(Book::toMap)
            .collect(Collectors.toList());
        sendJson(exchange, 200, payload);
    }

    private void createBook(HttpExchange exchange) throws IOException {
        Map<String, Object> body = readJsonObject(exchange);
        Book created = service.create(body);
        sendJson(exchange, 201, created.toMap());
    }

    private void getBook(HttpExchange exchange, long id) throws IOException {
        Optional<Book> book = service.get(id);
        if (book.isPresent()) {
            sendJson(exchange, 200, book.get().toMap());
        } else {
            sendError(exchange, 404, "book not found: " + id);
        }
    }

    private void updateBook(HttpExchange exchange, long id) throws IOException {
        Map<String, Object> body = readJsonObject(exchange);
        Optional<Book> updated = service.update(id, body);
        if (updated.isPresent()) {
            sendJson(exchange, 200, updated.get().toMap());
        } else {
            sendError(exchange, 404, "book not found: " + id);
        }
    }

    private void deleteBook(HttpExchange exchange, long id) throws IOException {
        if (service.delete(id)) {
            sendStatus(exchange, 204);
        } else {
            sendError(exchange, 404, "book not found: " + id);
        }
    }

    // ----- Helpers -------------------------------------------------------

    private Map<String, Object> readJsonObject(HttpExchange exchange) throws IOException {
        String body = readBody(exchange);
        if (body.trim().isEmpty()) {
            throw new ValidationException("request body is required");
        }
        return Json.parseObject(body);
    }

    private static String readBody(HttpExchange exchange) throws IOException {
        try (InputStream in = exchange.getRequestBody()) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    /** Extracts a single decoded query parameter value, or null if absent. */
    static String queryParam(String rawQuery, String name) {
        if (rawQuery == null || rawQuery.isEmpty()) {
            return null;
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq >= 0 ? pair.substring(0, eq) : pair;
            if (key.equals(name)) {
                String value = eq >= 0 ? pair.substring(eq + 1) : "";
                return java.net.URLDecoder.decode(value, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private void methodNotAllowed(HttpExchange exchange) throws IOException {
        sendError(exchange, 405, "method not allowed: " + exchange.getRequestMethod());
    }

    private void sendError(HttpExchange exchange, int status, String message) throws IOException {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("error", message);
        sendJson(exchange, status, body);
    }

    private void sendJson(HttpExchange exchange, int status, Object payload) throws IOException {
        byte[] bytes = Json.write(payload).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(bytes);
        }
    }

    private void sendStatus(HttpExchange exchange, int status) throws IOException {
        // 204 No Content: no response body.
        exchange.sendResponseHeaders(status, -1);
    }
}
