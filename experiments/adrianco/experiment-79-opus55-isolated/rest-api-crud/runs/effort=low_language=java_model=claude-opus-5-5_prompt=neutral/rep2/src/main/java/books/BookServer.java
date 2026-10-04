package books;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** HTTP front end: routes requests, validates input and renders JSON. */
public class BookServer {
    private static final int MAX_BODY_BYTES = 1 << 20;

    private final ObjectMapper json = new ObjectMapper();
    private final BookRepository repo;
    private final HttpServer server;
    private final ExecutorService executor = Executors.newFixedThreadPool(8);

    /** @param port port to bind, or 0 for an ephemeral port */
    public BookServer(BookRepository repo, int port) throws IOException {
        this.repo = repo;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        server.setExecutor(executor);
        server.createContext("/", this::handle);
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
    private static final class ApiException extends Exception {
        final int status;
        final Object body;

        ApiException(int status, String message) {
            super(message);
            this.status = status;
            this.body = Map.of("error", message);
        }

        ApiException(int status, String message, List<String> details) {
            super(message);
            this.status = status;
            this.body = Map.of("error", message, "details", details);
        }
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            try {
                route(ex);
            } catch (ApiException e) {
                send(ex, e.status, e.body);
            } catch (Exception e) {
                e.printStackTrace();
                send(ex, 500, Map.of("error", "Internal server error"));
            }
        }
    }

    private void route(HttpExchange ex) throws Exception {
        String method = ex.getRequestMethod();
        String path = ex.getRequestURI().getPath();
        if (path.length() > 1 && path.endsWith("/")) {
            path = path.substring(0, path.length() - 1);
        }

        if (path.equals("/health")) {
            requireMethod(ex, method, "GET");
            repo.ping();
            send(ex, 200, Map.of("status", "ok"));
        } else if (path.equals("/books")) {
            switch (method) {
                case "GET" -> send(ex, 200, repo.list(queryParam(ex, "author")));
                case "POST" -> {
                    Book created = repo.create(parseBook(ex));
                    ex.getResponseHeaders().set("Location", "/books/" + created.id());
                    send(ex, 201, created);
                }
                default -> throw methodNotAllowed(ex, "GET, POST");
            }
        } else if (path.startsWith("/books/")) {
            long id = parseId(path.substring("/books/".length()));
            switch (method) {
                case "GET" -> send(ex, 200, found(repo.find(id), id));
                case "PUT" -> send(ex, 200, found(repo.update(id, parseBook(ex)), id));
                case "DELETE" -> {
                    if (!repo.delete(id)) {
                        throw notFound(id);
                    }
                    ex.sendResponseHeaders(204, -1);
                }
                default -> throw methodNotAllowed(ex, "GET, PUT, DELETE");
            }
        } else {
            throw new ApiException(404, "Not found");
        }
    }

    private static void requireMethod(HttpExchange ex, String method, String allowed) throws ApiException {
        if (!method.equals(allowed)) {
            throw methodNotAllowed(ex, allowed);
        }
    }

    private static ApiException methodNotAllowed(HttpExchange ex, String allowed) {
        ex.getResponseHeaders().set("Allow", allowed);
        return new ApiException(405, "Method not allowed");
    }

    private static ApiException notFound(long id) {
        return new ApiException(404, "Book " + id + " not found");
    }

    private static Book found(Optional<Book> book, long id) throws ApiException {
        return book.orElseThrow(() -> notFound(id));
    }

    private static long parseId(String raw) throws ApiException {
        try {
            long id = Long.parseLong(raw);
            if (id > 0) {
                return id;
            }
        } catch (NumberFormatException ignored) {
            // fall through
        }
        throw new ApiException(400, "Book id must be a positive integer");
    }

    /** Returns the decoded value of a query parameter, or null if absent. */
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

    /** Reads and validates the request body as a book (without id). */
    private Book parseBook(HttpExchange ex) throws IOException, ApiException {
        byte[] body;
        try (InputStream in = ex.getRequestBody()) {
            body = in.readNBytes(MAX_BODY_BYTES + 1);
        }
        if (body.length > MAX_BODY_BYTES) {
            throw new ApiException(413, "Request body too large");
        }

        JsonNode node;
        try {
            node = json.readTree(body);
        } catch (JsonProcessingException e) {
            throw new ApiException(400, "Request body is not valid JSON");
        }
        if (node == null || !node.isObject()) {
            throw new ApiException(400, "Request body must be a JSON object");
        }

        List<String> errors = new ArrayList<>();
        String title = requiredText(node, "title", errors);
        String author = requiredText(node, "author", errors);

        Integer year = null;
        JsonNode yearNode = node.get("year");
        if (yearNode != null && !yearNode.isNull()) {
            if (yearNode.isIntegralNumber() && yearNode.canConvertToInt()) {
                year = yearNode.intValue();
            } else {
                errors.add("year must be an integer");
            }
        }

        String isbn = null;
        JsonNode isbnNode = node.get("isbn");
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

    private static String requiredText(JsonNode node, String field, List<String> errors) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            errors.add(field + " is required");
        } else if (!value.isTextual()) {
            errors.add(field + " must be a string");
        } else if (value.textValue().isBlank()) {
            errors.add(field + " must not be blank");
        } else {
            return value.textValue().trim();
        }
        return null;
    }

    private void send(HttpExchange ex, int status, Object body) throws IOException {
        byte[] bytes = json.writeValueAsBytes(body);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = ex.getResponseBody()) {
            out.write(bytes);
        }
    }
}
