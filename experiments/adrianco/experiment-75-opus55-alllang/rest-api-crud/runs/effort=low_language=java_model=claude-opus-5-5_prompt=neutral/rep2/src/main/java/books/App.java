package books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class App {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final BookRepository repo;
    private final HttpServer server;

    public App(int port, String dbUrl) throws Exception {
        repo = new BookRepository(dbUrl);
        server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", ex -> handle(ex, () -> "GET".equals(ex.getRequestMethod())
                ? new Resp(200, Map.of("status", "ok")) : new Resp(405, err("Method not allowed"))));
        server.createContext("/books", ex -> handle(ex, () -> route(ex)));
    }

    public void start() { server.start(); }
    public void stop() { server.stop(0); }
    public int port() { return server.getAddress().getPort(); }

    record Resp(int status, Object body) {}
    interface Handler { Resp run() throws Exception; }

    private Resp route(HttpExchange ex) throws Exception {
        String path = ex.getRequestURI().getPath().replaceAll("/+$", "");
        String m = ex.getRequestMethod();
        if (path.equals("/books")) {
            if (m.equals("GET")) return new Resp(200, repo.list(query(ex).get("author")));
            if (m.equals("POST")) {
                Object v = validate(ex);
                if (v instanceof Resp r) return r;
                return new Resp(201, repo.create(castMap(v)));
            }
            return new Resp(405, err("Method not allowed"));
        }
        String idStr = path.substring("/books/".length() > path.length() ? path.length() : "/books/".length());
        long id;
        try { id = Long.parseLong(idStr); } catch (NumberFormatException e) { return new Resp(404, err("Not found")); }
        switch (m) {
            case "GET": return repo.find(id).map(b -> new Resp(200, b)).orElse(notFound());
            case "PUT": {
                Object v = validate(ex);
                if (v instanceof Resp r) return r;
                return repo.update(id, castMap(v)).map(b -> new Resp(200, b)).orElse(notFound());
            }
            case "DELETE": return repo.delete(id) ? new Resp(204, null) : notFound();
            default: return new Resp(405, err("Method not allowed"));
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object o) { return (Map<String, Object>) o; }

    /** Returns either a validated body map or an error Resp. */
    private Object validate(HttpExchange ex) {
        Map<String, Object> b;
        try {
            Object parsed = JSON.readValue(ex.getRequestBody(), Object.class);
            if (!(parsed instanceof Map)) return new Resp(400, err("Body must be a JSON object"));
            b = castMap(parsed);
        } catch (IOException e) { return new Resp(400, err("Invalid JSON")); }
        List<String> errors = new ArrayList<>();
        for (String f : List.of("title", "author"))
            if (!(b.get(f) instanceof String s) || s.isBlank()) errors.add(f + " is required");
        if (b.get("year") != null && !(b.get("year") instanceof Integer)) errors.add("year must be an integer");
        if (b.get("isbn") != null && !(b.get("isbn") instanceof String)) errors.add("isbn must be a string");
        if (!errors.isEmpty()) return new Resp(400, Map.of("errors", errors));
        return b;
    }

    private static Resp notFound() { return new Resp(404, err("Book not found")); }
    private static Map<String, Object> err(String msg) { return Map.of("error", msg); }

    private static Map<String, String> query(HttpExchange ex) {
        Map<String, String> q = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw == null) return q;
        for (String kv : raw.split("&")) {
            String[] p = kv.split("=", 2);
            q.put(URLDecoder.decode(p[0], StandardCharsets.UTF_8), p.length > 1 ? URLDecoder.decode(p[1], StandardCharsets.UTF_8) : "");
        }
        return q;
    }

    private static void handle(HttpExchange ex, Handler h) throws IOException {
        Resp r;
        try { r = h.run(); } catch (Exception e) { r = new Resp(500, err("Internal server error")); }
        if (r.body() == null) { ex.sendResponseHeaders(r.status(), -1); ex.close(); return; }
        byte[] out = JSON.writeValueAsBytes(r.body());
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(r.status(), out.length);
        ex.getResponseBody().write(out);
        ex.close();
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String db = System.getenv().getOrDefault("DB_PATH", "books.db");
        App app = new App(port, "jdbc:sqlite:" + db);
        app.start();
        System.out.println("Listening on http://localhost:" + app.port());
    }
}
