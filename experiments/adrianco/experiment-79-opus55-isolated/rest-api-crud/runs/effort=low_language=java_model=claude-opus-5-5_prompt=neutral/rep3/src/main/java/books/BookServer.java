package books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** HTTP front end: routes requests, validates input and renders JSON. */
public class BookServer {
    private static final int MAX_BODY_BYTES = 1 << 20;

    private final ObjectMapper mapper = new ObjectMapper();
    private final BookRepository repo;
    private final HttpServer server;
    private final ExecutorService executor = Executors.newFixedThreadPool(8);

    /** @param port port to listen on; 0 picks a free port (see {@link #port()}) */
    public BookServer(BookRepository repo, int port) throws IOException {
        this.repo = repo;
        server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", this::handle);
        server.setExecutor(executor);
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

    /** An error that maps directly to an HTTP response. */
    private static class ApiException extends Exception {
        final int status;
        final List<String> details;

        ApiException(int status, String message) {
            this(status, message, List.of());
        }

        ApiException(int status, String message, List<String> details) {
            super(message);
            this.status = status;
            this.details = details;
        }
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            try {
                route(ex);
            } catch (ApiException e) {
                Map<String, Object> body = e.details.isEmpty()
                        ? Map.of("error", e.getMessage())
                        : Map.of("error", e.getMessage(), "details", e.details);
                send(ex, e.status, body);
            } catch (SQLException | RuntimeException e) {
                e.printStackTrace();
                send(ex, 500, Map.of("error", "Internal server error"));
            }
        }
    }

    private void route(HttpExchange ex) throws IOException, ApiException, SQLException {
        String method = ex.getRequestMethod();
        String path = ex.getRequestURI().getPath();
        if (path.length() > 1 && path.endsWith("/")) {
            path = path.substring(0, path.length() - 1);
        }

        if (path.equals("/health")) {
            requireMethod(ex, method, "GET");
            send(ex, 200, Map.of("status", "ok"));
        } else if (path.equals("/books")) {
            switch (method) {
                case "GET" -> send(ex, 200, repo.list(queryParam(ex, "author")));
                case "POST" -> {
                    Book created = repo.create(parseBook(ex));
                    ex.getResponseHeaders().set("Location", "/books/" + created.id());
                    send(ex, 201, created);
                }
                default -> requireMethod(ex, method, "GET", "POST");
            }
        } else if (path.startsWith("/books/")) {
            long id = parseId(path.substring("/books/".length()));
            switch (method) {
                case "GET" -> send(ex, 200, found(repo.find(id)));
                case "PUT" -> send(ex, 200, found(repo.update(id, parseBook(ex))));
                case "DELETE" -> {
                    if (!repo.delete(id)) {
                        throw notFound();
                    }
                    ex.sendResponseHeaders(204, -1);
                }
                default -> requireMethod(ex, method, "GET", "PUT", "DELETE");
            }
        } else {
            throw new ApiException(404, "Not found");
        }
    }

    private static void requireMethod(HttpExchange ex, String method, String... allowed) throws ApiException {
        if (!List.of(allowed).contains(method)) {
            ex.getResponseHeaders().set("Allow", String.join(", ", allowed));
            throw new ApiException(405, "Method not allowed");
        }
    }

    private static ApiException notFound() {
        return new ApiException(404, "Book not found");
    }

    private static Book found(Optional<Book> book) throws ApiException {
        return book.orElseThrow(BookServer::notFound);
    }

    private static long parseId(String raw) throws ApiException {
        if (!raw.matches("\\d{1,18}")) {
            throw notFound();
        }
        return Long.parseLong(raw);
    }

    private static String queryParam(HttpExchange ex, String name) {
        String query = ex.getRequestURI().getRawQuery();
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int eq = pair.indexOf('=');
            String key = eq < 0 ? pair : pair.substring(0, eq);
            if (decode(key).equals(name)) {
                return eq < 0 ? "" : decode(pair.substring(eq + 1));
            }
        }
        return null;
    }

    private static String decode(String s) {
        try {
            return URLDecoder.decode(s, StandardCharsets.UTF_8);
        } catch (IllegalArgumentException e) {
            return s;
        }
    }

    /** Reads and validates a book from the request body; the result has no id. */
    private Book parseBook(HttpExchange ex) throws IOException, ApiException {
        byte[] raw;
        try (InputStream in = ex.getRequestBody()) {
            raw = in.readNBytes(MAX_BODY_BYTES + 1);
        }
        if (raw.length > MAX_BODY_BYTES) {
            throw new ApiException(413, "Request body too large");
        }
        JsonNode json;
        try {
            json = mapper.readTree(raw);
        } catch (JsonProcessingException e) {
            throw new ApiException(400, "Request body is not valid JSON");
        }
        if (json == null || !json.isObject()) {
            throw new ApiException(400, "Request body must be a JSON object");
        }

        List<String> errors = new ArrayList<>();
        String title = requiredText(json, "title", errors);
        String author = requiredText(json, "author", errors);

        Integer year = null;
        JsonNode yearNode = json.get("year");
        if (yearNode != null && !yearNode.isNull()) {
            if (yearNode.isIntegralNumber() && yearNode.canConvertToInt()) {
                year = yearNode.intValue();
            } else {
                errors.add("year must be an integer");
            }
        }

        String isbn = null;
        JsonNode isbnNode = json.get("isbn");
        if (isbnNode != null && !isbnNode.isNull()) {
            if (isbnNode.isTextual()) {
                isbn = isbnNode.textValue().trim();
            } else {
                errors.add("isbn must be a string");
            }
        }

        if (!errors.isEmpty()) {
            throw new ApiException(400, "Validation failed", errors);
        }
        return new Book(null, title, author, year, isbn);
    }

    private static String requiredText(JsonNode json, String field, List<String> errors) {
        JsonNode node = json.get(field);
        if (node == null || node.isNull()) {
            errors.add(field + " is required");
        } else if (!node.isTextual()) {
            errors.add(field + " must be a string");
        } else if (node.textValue().isBlank()) {
            errors.add(field + " must not be blank");
        } else {
            return node.textValue().trim();
        }
        return null;
    }

    private void send(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = mapper.writeValueAsBytes(body);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(status, bytes.length);
        ex.getResponseBody().write(bytes);
    }
}
