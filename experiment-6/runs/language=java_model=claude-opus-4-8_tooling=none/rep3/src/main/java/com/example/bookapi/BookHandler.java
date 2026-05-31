package com.example.bookapi;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Routes book-related HTTP requests to the {@link BookRepository} and renders
 * JSON responses. Handles both the collection ("/books") and item
 * ("/books/{id}") resources.
 */
public class BookHandler implements HttpHandler {

    private static final Pattern ITEM_PATH = Pattern.compile("^/books/([^/]+)/?$");

    private final BookRepository repository;
    private final ObjectMapper mapper = new ObjectMapper();

    public BookHandler(BookRepository repository) {
        this.repository = repository;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        try {
            route(exchange);
        } catch (ValidationException e) {
            sendError(exchange, 400, e.getMessage());
        } catch (Exception e) {
            sendError(exchange, 500, "Internal server error: " + e.getMessage());
        } finally {
            exchange.close();
        }
    }

    private void route(HttpExchange exchange) throws IOException {
        String method = exchange.getRequestMethod();
        URI uri = exchange.getRequestURI();
        String path = uri.getPath();

        Matcher itemMatcher = ITEM_PATH.matcher(path);

        if (path.equals("/books") || path.equals("/books/")) {
            switch (method) {
                case "POST" -> createBook(exchange);
                case "GET" -> listBooks(exchange, uri);
                default -> sendError(exchange, 405, "Method not allowed");
            }
        } else if (itemMatcher.matches()) {
            long id = parseId(itemMatcher.group(1));
            switch (method) {
                case "GET" -> getBook(exchange, id);
                case "PUT" -> updateBook(exchange, id);
                case "DELETE" -> deleteBook(exchange, id);
                default -> sendError(exchange, 405, "Method not allowed");
            }
        } else {
            sendError(exchange, 404, "Not found");
        }
    }

    private void createBook(HttpExchange exchange) throws IOException {
        Book book = parseBody(exchange);
        validate(book);
        Book created = repository.create(book);
        sendJson(exchange, 201, created);
    }

    private void listBooks(HttpExchange exchange, URI uri) throws IOException {
        String author = queryParam(uri.getRawQuery(), "author");
        List<Book> books = repository.findAll(author);
        sendJson(exchange, 200, books);
    }

    private void getBook(HttpExchange exchange, long id) throws IOException {
        Optional<Book> book = repository.findById(id);
        if (book.isPresent()) {
            sendJson(exchange, 200, book.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void updateBook(HttpExchange exchange, long id) throws IOException {
        Book book = parseBody(exchange);
        validate(book);
        Optional<Book> updated = repository.update(id, book);
        if (updated.isPresent()) {
            sendJson(exchange, 200, updated.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void deleteBook(HttpExchange exchange, long id) throws IOException {
        if (repository.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    // --- helpers ---

    private long parseId(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (NumberFormatException e) {
            throw new ValidationException("Invalid book id: " + raw);
        }
    }

    private Book parseBody(HttpExchange exchange) throws IOException {
        try (InputStream in = exchange.getRequestBody()) {
            byte[] bytes = in.readAllBytes();
            if (bytes.length == 0) {
                throw new ValidationException("Request body is required");
            }
            try {
                Book book = mapper.readValue(bytes, Book.class);
                if (book == null) {
                    throw new ValidationException("Request body is required");
                }
                return book;
            } catch (ValidationException e) {
                throw e;
            } catch (Exception e) {
                throw new ValidationException("Malformed JSON body");
            }
        }
    }

    private void validate(Book book) {
        if (isBlank(book.getTitle())) {
            throw new ValidationException("Field 'title' is required");
        }
        if (isBlank(book.getAuthor())) {
            throw new ValidationException("Field 'author' is required");
        }
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    /** Extracts a single decoded query parameter value, or null if absent. */
    static String queryParam(String rawQuery, String key) {
        if (rawQuery == null || rawQuery.isEmpty()) {
            return null;
        }
        for (String pair : rawQuery.split("&")) {
            int eq = pair.indexOf('=');
            String k = eq >= 0 ? pair.substring(0, eq) : pair;
            String v = eq >= 0 ? pair.substring(eq + 1) : "";
            if (decode(k).equals(key)) {
                return decode(v);
            }
        }
        return null;
    }

    private static String decode(String s) {
        return java.net.URLDecoder.decode(s, StandardCharsets.UTF_8);
    }

    private void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] payload = mapper.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, payload.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(payload);
        }
    }

    private void sendError(HttpExchange exchange, int status, String message) throws IOException {
        ObjectNode node = mapper.createObjectNode();
        node.put("error", message);
        sendJson(exchange, status, node);
    }
}
