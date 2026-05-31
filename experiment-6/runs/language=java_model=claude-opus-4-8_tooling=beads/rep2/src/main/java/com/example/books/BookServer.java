package com.example.books;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Lightweight REST server for the book collection, built on the JDK's
 * built-in {@link HttpServer}.
 */
public class BookServer {

    private static final Pattern BOOK_ID_PATTERN = Pattern.compile("^/books/([^/]+)$");

    private final BookRepository repository;
    private final ObjectMapper mapper;
    private final HttpServer httpServer;

    public BookServer(int port, BookRepository repository) throws IOException {
        this.repository = repository;
        this.mapper = new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
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
    public int getPort() {
        return httpServer.getAddress().getPort();
    }

    // ---- Route handlers ----

    private void handleHealth(HttpExchange exchange) throws IOException {
        try {
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                methodNotAllowed(exchange);
                return;
            }
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("status", "ok");
            sendJson(exchange, 200, body);
        } catch (Exception e) {
            handleUnexpected(exchange, e);
        }
    }

    private void handleBooks(HttpExchange exchange) throws IOException {
        try {
            String path = exchange.getRequestURI().getPath();
            String method = exchange.getRequestMethod().toUpperCase();
            Matcher idMatcher = BOOK_ID_PATTERN.matcher(path);

            if (path.equals("/books")) {
                switch (method) {
                    case "GET" -> listBooks(exchange);
                    case "POST" -> createBook(exchange);
                    default -> methodNotAllowed(exchange);
                }
            } else if (idMatcher.matches()) {
                Integer id = parseId(idMatcher.group(1));
                if (id == null) {
                    sendError(exchange, 400, "Invalid book id");
                    return;
                }
                switch (method) {
                    case "GET" -> getBook(exchange, id);
                    case "PUT" -> updateBook(exchange, id);
                    case "DELETE" -> deleteBook(exchange, id);
                    default -> methodNotAllowed(exchange);
                }
            } else {
                sendError(exchange, 404, "Not found");
            }
        } catch (ValidationException e) {
            sendError(exchange, 400, e.getMessage());
        } catch (Exception e) {
            handleUnexpected(exchange, e);
        }
    }

    private void listBooks(HttpExchange exchange) throws IOException {
        String author = queryParam(exchange.getRequestURI(), "author");
        List<Book> books = repository.findAll(author);
        sendJson(exchange, 200, books);
    }

    private void createBook(HttpExchange exchange) throws IOException {
        Book book = readBook(exchange);
        validate(book);
        Book created = repository.create(book);
        sendJson(exchange, 201, created);
    }

    private void getBook(HttpExchange exchange, int id) throws IOException {
        Optional<Book> book = repository.findById(id);
        if (book.isPresent()) {
            sendJson(exchange, 200, book.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void updateBook(HttpExchange exchange, int id) throws IOException {
        Book book = readBook(exchange);
        validate(book);
        Optional<Book> updated = repository.update(id, book);
        if (updated.isPresent()) {
            sendJson(exchange, 200, updated.get());
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    private void deleteBook(HttpExchange exchange, int id) throws IOException {
        if (repository.delete(id)) {
            exchange.sendResponseHeaders(204, -1);
            exchange.close();
        } else {
            sendError(exchange, 404, "Book not found");
        }
    }

    // ---- Validation ----

    private void validate(Book book) {
        if (book == null) {
            throw new ValidationException("Request body is required");
        }
        if (isBlank(book.getTitle())) {
            throw new ValidationException("title is required");
        }
        if (isBlank(book.getAuthor())) {
            throw new ValidationException("author is required");
        }
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    // ---- Helpers ----

    private Book readBook(HttpExchange exchange) throws IOException {
        try (InputStream is = exchange.getRequestBody()) {
            byte[] bytes = is.readAllBytes();
            if (bytes.length == 0) {
                throw new ValidationException("Request body is required");
            }
            try {
                return mapper.readValue(bytes, Book.class);
            } catch (IOException e) {
                throw new ValidationException("Malformed JSON request body");
            }
        }
    }

    private Integer parseId(String raw) {
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String queryParam(URI uri, String name) {
        String query = uri.getRawQuery();
        if (query == null || query.isEmpty()) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            if (eq < 0) {
                continue;
            }
            String key = urlDecode(pair.substring(0, eq));
            if (key.equals(name)) {
                return urlDecode(pair.substring(eq + 1));
            }
        }
        return null;
    }

    private static String urlDecode(String s) {
        return java.net.URLDecoder.decode(s, StandardCharsets.UTF_8);
    }

    private void sendJson(HttpExchange exchange, int status, Object body) throws IOException {
        byte[] payload = mapper.writeValueAsBytes(body);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, payload.length);
        exchange.getResponseBody().write(payload);
        exchange.close();
    }

    private void sendError(HttpExchange exchange, int status, String message) throws IOException {
        Map<String, Object> body = new HashMap<>();
        body.put("error", message);
        sendJson(exchange, status, body);
    }

    private void methodNotAllowed(HttpExchange exchange) throws IOException {
        sendError(exchange, 405, "Method not allowed");
    }

    private void handleUnexpected(HttpExchange exchange, Exception e) throws IOException {
        e.printStackTrace();
        try {
            sendError(exchange, 500, "Internal server error");
        } catch (IOException ignored) {
            // response may already be partially written
        }
    }
}
