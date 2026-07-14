package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class App {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Pattern BOOK_ID_PATH = Pattern.compile("^/books/(\\d+)$");

    private final HttpServer server;
    private final BookRepository repository;

    public App(int port, BookRepository repository) throws IOException {
        this.repository = repository;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        this.server.setExecutor(Executors.newFixedThreadPool(4));
        this.server.createContext("/health", this::handleHealth);
        this.server.createContext("/books", this::handleBooks);
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
    }

    public int port() {
        return server.getAddress().getPort();
    }

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getProperty("port", "8080"));
        String db = System.getProperty("db", "books.db");
        BookRepository repo = new BookRepository("jdbc:sqlite:" + db);
        App app = new App(port, repo);
        app.start();
        System.out.println("Book API listening on http://localhost:" + port);
    }

    private void handleHealth(HttpExchange ex) throws IOException {
        if (!"GET".equals(ex.getRequestMethod())) {
            sendError(ex, 405, "Method not allowed");
            return;
        }
        sendJson(ex, 200, Map.of("status", "ok"));
    }

    private void handleBooks(HttpExchange ex) throws IOException {
        try {
            String path = ex.getRequestURI().getPath();
            String method = ex.getRequestMethod();
            Matcher m = BOOK_ID_PATH.matcher(path);

            if (path.equals("/books") || path.equals("/books/")) {
                switch (method) {
                    case "GET"  -> listBooks(ex);
                    case "POST" -> createBook(ex);
                    default     -> sendError(ex, 405, "Method not allowed");
                }
            } else if (m.matches()) {
                long id = Long.parseLong(m.group(1));
                switch (method) {
                    case "GET"    -> getBook(ex, id);
                    case "PUT"    -> updateBook(ex, id);
                    case "DELETE" -> deleteBook(ex, id);
                    default       -> sendError(ex, 405, "Method not allowed");
                }
            } else {
                sendError(ex, 404, "Not found");
            }
        } catch (Exception e) {
            sendError(ex, 500, "Internal server error: " + e.getMessage());
        }
    }

    private void listBooks(HttpExchange ex) throws IOException {
        String author = queryParam(ex.getRequestURI(), "author");
        List<Book> books = repository.findAll(author);
        sendJson(ex, 200, books);
    }

    private void createBook(HttpExchange ex) throws IOException {
        Book body = readBody(ex);
        if (body == null) {
            sendError(ex, 400, "Invalid JSON body");
            return;
        }
        String err = validate(body);
        if (err != null) {
            sendError(ex, 400, err);
            return;
        }
        Book created = repository.create(body);
        sendJson(ex, 201, created);
    }

    private void getBook(HttpExchange ex, long id) throws IOException {
        Optional<Book> book = repository.findById(id);
        if (book.isEmpty()) {
            sendError(ex, 404, "Book not found");
            return;
        }
        sendJson(ex, 200, book.get());
    }

    private void updateBook(HttpExchange ex, long id) throws IOException {
        Book body = readBody(ex);
        if (body == null) {
            sendError(ex, 400, "Invalid JSON body");
            return;
        }
        String err = validate(body);
        if (err != null) {
            sendError(ex, 400, err);
            return;
        }
        Optional<Book> updated = repository.update(id, body);
        if (updated.isEmpty()) {
            sendError(ex, 404, "Book not found");
            return;
        }
        sendJson(ex, 200, updated.get());
    }

    private void deleteBook(HttpExchange ex, long id) throws IOException {
        boolean removed = repository.delete(id);
        if (!removed) {
            sendError(ex, 404, "Book not found");
            return;
        }
        ex.sendResponseHeaders(204, -1);
        ex.close();
    }

    private static String validate(Book b) {
        if (b.getTitle() == null || b.getTitle().isBlank()) return "title is required";
        if (b.getAuthor() == null || b.getAuthor().isBlank()) return "author is required";
        return null;
    }

    private static Book readBody(HttpExchange ex) throws IOException {
        try (InputStream in = ex.getRequestBody()) {
            byte[] raw = in.readAllBytes();
            if (raw.length == 0) return null;
            return MAPPER.readValue(raw, Book.class);
        } catch (IOException e) {
            return null;
        }
    }

    private static String queryParam(URI uri, String key) {
        String q = uri.getRawQuery();
        if (q == null || q.isEmpty()) return null;
        for (String pair : q.split("&")) {
            int eq = pair.indexOf('=');
            String k = eq < 0 ? pair : pair.substring(0, eq);
            String v = eq < 0 ? "" : pair.substring(eq + 1);
            if (k.equals(key)) {
                return java.net.URLDecoder.decode(v, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private static void sendJson(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = MAPPER.writeValueAsBytes(body);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static void sendError(HttpExchange ex, int status, String message) throws IOException {
        Map<String, Object> body = new HashMap<>();
        body.put("error", message);
        sendJson(ex, status, body);
    }
}
