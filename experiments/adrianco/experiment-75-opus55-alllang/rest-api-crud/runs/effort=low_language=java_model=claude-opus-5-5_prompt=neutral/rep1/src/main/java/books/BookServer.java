package books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.*;

/** Minimal REST API for books using the JDK HttpServer and SQLite. */
public class BookServer {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final HttpServer server;
    private final Connection db;

    public BookServer(int port, String dbUrl) throws Exception {
        db = DriverManager.getConnection(dbUrl);
        try (Statement s = db.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
        }
        server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", ex -> handle(ex, () -> ex.getRequestMethod().equals("GET")
                ? new Resp(200, Map.of("status", "ok")) : new Resp(405, err("method not allowed"))));
        server.createContext("/books", ex -> handle(ex, () -> route(ex)));
    }

    public void start() { server.start(); }
    public void stop() throws SQLException { server.stop(0); db.close(); }
    public int port() { return server.getAddress().getPort(); }

    record Resp(int status, Object body) {}
    interface Handler { Resp run() throws Exception; }

    private static Map<String, String> err(String msg) { return Map.of("error", msg); }

    private void handle(HttpExchange ex, Handler h) throws IOException {
        Resp r;
        try { r = h.run(); }
        catch (com.fasterxml.jackson.core.JsonProcessingException e) { r = new Resp(400, err("invalid JSON")); }
        catch (Exception e) { r = new Resp(500, err(e.getMessage())); }
        byte[] out = r.body() == null ? new byte[0] : JSON.writeValueAsBytes(r.body());
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(r.status(), out.length == 0 ? -1 : out.length);
        if (out.length > 0) ex.getResponseBody().write(out);
        ex.close();
    }

    private synchronized Resp route(HttpExchange ex) throws Exception {
        String path = ex.getRequestURI().getPath().replaceAll("/+$", "");
        String method = ex.getRequestMethod();
        if (path.equals("/books")) {
            return switch (method) {
                case "GET" -> new Resp(200, list(query(ex).get("author")));
                case "POST" -> create(ex);
                default -> new Resp(405, err("method not allowed"));
            };
        }
        String idStr = path.substring("/books/".length() < path.length() ? "/books/".length() : path.length());
        if (!path.startsWith("/books/") || !idStr.matches("\\d+")) return new Resp(404, err("not found"));
        long id = Long.parseLong(idStr);
        return switch (method) {
            case "GET" -> { Map<String, Object> b = find(id); yield b == null ? new Resp(404, err("book not found")) : new Resp(200, b); }
            case "PUT" -> update(ex, id);
            case "DELETE" -> {
                try (PreparedStatement ps = db.prepareStatement("DELETE FROM books WHERE id=?")) {
                    ps.setLong(1, id);
                    yield ps.executeUpdate() == 0 ? new Resp(404, err("book not found")) : new Resp(204, null);
                }
            }
            default -> new Resp(405, err("method not allowed"));
        };
    }

    private static Map<String, String> query(HttpExchange ex) {
        Map<String, String> q = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw == null) return q;
        for (String p : raw.split("&")) {
            String[] kv = p.split("=", 2);
            q.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                    kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
        }
        return q;
    }

    /** Parses and validates a book payload; returns an error message or null. */
    static String validate(Map<String, Object> b) {
        for (String f : List.of("title", "author")) {
            Object v = b.get(f);
            if (!(v instanceof String s) || s.isBlank()) return f + " is required";
        }
        Object y = b.get("year");
        if (y != null && !(y instanceof Integer)) return "year must be an integer";
        Object i = b.get("isbn");
        if (i != null && !(i instanceof String)) return "isbn must be a string";
        return null;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> body(HttpExchange ex) throws IOException {
        Object o = JSON.readValue(ex.getRequestBody(), Object.class);
        return o instanceof Map ? (Map<String, Object>) o : null;
    }

    private Resp create(HttpExchange ex) throws Exception {
        Map<String, Object> b = body(ex);
        if (b == null) return new Resp(400, err("body must be a JSON object"));
        String e = validate(b);
        if (e != null) return new Resp(400, err(e));
        try (PreparedStatement ps = db.prepareStatement(
                "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, b);
            ps.executeUpdate();
            ResultSet rs = ps.getGeneratedKeys();
            rs.next();
            return new Resp(201, find(rs.getLong(1)));
        }
    }

    private Resp update(HttpExchange ex, long id) throws Exception {
        if (find(id) == null) return new Resp(404, err("book not found"));
        Map<String, Object> b = body(ex);
        if (b == null) return new Resp(400, err("body must be a JSON object"));
        String e = validate(b);
        if (e != null) return new Resp(400, err(e));
        try (PreparedStatement ps = db.prepareStatement("UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?")) {
            bind(ps, b);
            ps.setLong(5, id);
            ps.executeUpdate();
        }
        return new Resp(200, find(id));
    }

    private static void bind(PreparedStatement ps, Map<String, Object> b) throws SQLException {
        ps.setString(1, ((String) b.get("title")).trim());
        ps.setString(2, ((String) b.get("author")).trim());
        ps.setObject(3, b.get("year"));
        ps.setObject(4, b.get("isbn"));
    }

    private List<Map<String, Object>> list(String author) throws SQLException {
        String sql = "SELECT * FROM books" + (author != null ? " WHERE author = ? COLLATE NOCASE" : "") + " ORDER BY id";
        try (PreparedStatement ps = db.prepareStatement(sql)) {
            if (author != null) ps.setString(1, author);
            ResultSet rs = ps.executeQuery();
            List<Map<String, Object>> out = new ArrayList<>();
            while (rs.next()) out.add(row(rs));
            return out;
        }
    }

    private Map<String, Object> find(long id) throws SQLException {
        try (PreparedStatement ps = db.prepareStatement("SELECT * FROM books WHERE id=?")) {
            ps.setLong(1, id);
            ResultSet rs = ps.executeQuery();
            return rs.next() ? row(rs) : null;
        }
    }

    private static Map<String, Object> row(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("author", rs.getString("author"));
        int y = rs.getInt("year");
        m.put("year", rs.wasNull() ? null : y);
        m.put("isbn", rs.getString("isbn"));
        return m;
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        String db = System.getenv().getOrDefault("DB_PATH", "books.db");
        BookServer s = new BookServer(port, "jdbc:sqlite:" + db);
        s.start();
        System.out.println("Listening on http://localhost:" + s.port());
    }
}
