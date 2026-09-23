package books;

import books.BookRepository.Book;
import com.fasterxml.jackson.databind.*;
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class App {
    private static final ObjectMapper JSON = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    private final BookRepository repo;
    private final HttpServer server;

    public App(int port, String dbUrl) throws IOException {
        repo = new BookRepository(dbUrl);
        server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", ex -> handle(ex, () -> ex.getRequestMethod().equals("GET")
                ? new Resp(200, Map.of("status", "ok")) : new Resp(405, err("method not allowed"))));
        server.createContext("/books", ex -> handle(ex, () -> route(ex)));
    }

    public void start() { server.start(); }
    public void stop() { server.stop(0); }
    public int port() { return server.getAddress().getPort(); }

    record Resp(int status, Object body) {}
    interface Handler { Resp run() throws Exception; }

    private static Map<String, String> err(String m) { return Map.of("error", m); }

    private Resp route(HttpExchange ex) throws Exception {
        String path = ex.getRequestURI().getPath().replaceAll("/+$", "");
        String method = ex.getRequestMethod();
        if (path.equals("/books")) {
            return switch (method) {
                case "GET" -> new Resp(200, repo.list(query(ex.getRequestURI()).get("author")));
                case "POST" -> {
                    Object v = parse(ex);
                    yield v instanceof Resp r ? r : new Resp(201, repo.create((Book) v));
                }
                default -> new Resp(405, err("method not allowed"));
            };
        }
        long id;
        try { id = Long.parseLong(path.substring("/books/".length())); }
        catch (Exception e) { return new Resp(404, err("not found")); }
        Resp notFound = new Resp(404, err("book not found"));
        return switch (method) {
            case "GET" -> repo.get(id).<Resp>map(b -> new Resp(200, b)).orElse(notFound);
            case "PUT" -> {
                Object v = parse(ex);
                yield v instanceof Resp r ? r : repo.update(id, (Book) v).<Resp>map(b -> new Resp(200, b)).orElse(notFound);
            }
            case "DELETE" -> repo.delete(id) ? new Resp(204, null) : notFound;
            default -> new Resp(405, err("method not allowed"));
        };
    }

    /** Returns a validated Book, or a 400 Resp. */
    private Object parse(HttpExchange ex) {
        Book b;
        try { b = JSON.readValue(ex.getRequestBody(), Book.class); }
        catch (Exception e) { return new Resp(400, err("invalid JSON body")); }
        if (b == null) return new Resp(400, err("invalid JSON body"));
        List<String> errors = new ArrayList<>();
        if (b.title() == null || b.title().isBlank()) errors.add("title is required");
        if (b.author() == null || b.author().isBlank()) errors.add("author is required");
        if (!errors.isEmpty()) return new Resp(400, Map.of("errors", errors));
        return new Book(null, b.title().trim(), b.author().trim(), b.year(), b.isbn());
    }

    private static Map<String, String> query(URI uri) {
        Map<String, String> m = new HashMap<>();
        String q = uri.getRawQuery();
        if (q == null) return m;
        for (String p : q.split("&")) {
            int i = p.indexOf('=');
            if (i > 0) m.put(URLDecoder.decode(p.substring(0, i), StandardCharsets.UTF_8),
                    URLDecoder.decode(p.substring(i + 1), StandardCharsets.UTF_8));
        }
        return m;
    }

    private static void handle(HttpExchange ex, Handler h) throws IOException {
        Resp r;
        try { r = h.run(); } catch (Exception e) { r = new Resp(500, err("internal error")); }
        try (ex) {
            if (r.body() == null) { ex.sendResponseHeaders(r.status(), -1); return; }
            byte[] out = JSON.writeValueAsBytes(r.body());
            ex.getResponseHeaders().set("Content-Type", "application/json");
            ex.sendResponseHeaders(r.status(), out.length);
            ex.getResponseBody().write(out);
        }
    }

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String db = System.getenv().getOrDefault("DB_PATH", "books.db");
        App app = new App(port, "jdbc:sqlite:" + db);
        app.start();
        System.out.println("Listening on http://localhost:" + app.port());
    }
}
