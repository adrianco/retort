import com.fasterxml.jackson.databind.*;
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.*;

public class BookApi {
    static final ObjectMapper JSON = new ObjectMapper().enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    record Book(long id, String title, String author, Integer year, String isbn) {}
    record Reply(int status, Object body) {}
    static Reply error(int status, String message) {
        return new Reply(status, Map.of("error", message));
    }

    static String initialize(String database) throws SQLException {
        String url = "jdbc:sqlite:" + database;
        try (var db = DriverManager.getConnection(url); var sql = db.createStatement()) {
            sql.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
        }
        return url;
    }

    static HttpServer start(int port, String database) throws Exception {
        String url = initialize(database);
        var server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", exchange -> {
            try (exchange) {
                Reply reply = handle(url, exchange.getRequestMethod(), exchange.getRequestURI(),
                        exchange.getRequestBody(), exchange.getResponseHeaders());
                if (reply.body == null) {
                    exchange.sendResponseHeaders(reply.status, -1);
                } else {
                    byte[] data = JSON.writeValueAsBytes(reply.body);
                    exchange.getResponseHeaders().set("Content-Type", "application/json");
                    exchange.sendResponseHeaders(reply.status, data.length);
                    exchange.getResponseBody().write(data);
                }
            }
        });
        server.start();
        return server;
    }

    static Reply handle(String url, String method, URI uri, InputStream input, Headers headers) throws IOException {
        try (var db = DriverManager.getConnection(url)) {
            return route(method, uri, input, headers, db);
        } catch (IllegalArgumentException | com.fasterxml.jackson.core.JsonProcessingException e) {
            return error(400, "Invalid request");
        } catch (SQLException e) {
            e.printStackTrace();
            return error(500, "Database error");
        }
    }

    static Reply route(String method, URI uri, InputStream input, Headers headers, Connection db) throws IOException, SQLException {
        String path = uri.getRawPath();
        boolean collection = path.equals("/books");
        boolean health = path.equals("/health");
        boolean item = path.matches("/books/[1-9][0-9]*");
        if (!collection && !item && !health) return error(404, "Unknown path");
        String allow = health ? "GET" : collection ? "GET, POST" : "GET, PUT, DELETE";
        if (!Arrays.asList(allow.split(", ")).contains(method)) {
            headers.set("Allow", allow);
            return error(405, "Method not allowed");
        }
        if (health) return new Reply(200, Map.of("status", "ok"));
        long id = item ? Long.parseLong(path.substring(7)) : 0;
        if (collection && method.equals("GET")) {
            String author = authorFilter(uri.getRawQuery());
            String query = "SELECT * FROM books" + (author == null ? "" : " WHERE author = ?") + " ORDER BY id";
            try (var stmt = db.prepareStatement(query)) {
                if (author != null) stmt.setString(1, author);
                List<Book> books = new ArrayList<>();
                try (var rows = stmt.executeQuery()) {
                    while (rows.next()) books.add(read(rows));
                }
                return new Reply(200, books);
            }
        }
        if (method.equals("POST") || method.equals("PUT")) {
            JsonNode body = JSON.readTree(input);
            if (body == null || !body.isObject()) return error(400, "Expected a JSON object");
            var title = body.path("title");
            var author = body.path("author");
            if (!title.isTextual() || title.textValue().isBlank() || !author.isTextual() || author.textValue().isBlank())
                return error(400, "Title and author must be nonblank strings");
            var year = body.get("year");
            var isbn = body.get("isbn");
            if (body.hasNonNull("year") && !(year.isIntegralNumber() && year.canConvertToInt()))
                return error(400, "Year must be an integer");
            if (body.hasNonNull("isbn") && !isbn.isTextual()) return error(400, "ISBN must be a string");
            String query = collection ? "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)"
                    : "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?";
            try (var stmt = db.prepareStatement(query + " RETURNING *")) {
                stmt.setString(1, title.textValue());
                stmt.setString(2, author.textValue());
                stmt.setObject(3, body.hasNonNull("year") ? year.intValue() : null);
                stmt.setString(4, body.hasNonNull("isbn") ? isbn.textValue() : null);
                if (item) stmt.setLong(5, id);
                try (var rows = stmt.executeQuery()) {
                    if (!rows.next()) return error(404, "Book not found");
                    Book book = read(rows);
                    if (collection) headers.set("Location", "/books/" + book.id);
                    return new Reply(collection ? 201 : 200, book);
                }
            }
        }
        boolean delete = method.equals("DELETE");
        try (var stmt = db.prepareStatement(delete ? "DELETE FROM books WHERE id=?" : "SELECT * FROM books WHERE id=?")) {
            stmt.setLong(1, id);
            if (delete) return stmt.executeUpdate() == 1 ? new Reply(204, null) : error(404, "Book not found");
            try (var rows = stmt.executeQuery()) {
                return rows.next() ? new Reply(200, read(rows)) : error(404, "Book not found");
            }
        }
    }

    static String authorFilter(String query) {
        if (query != null) {
            for (String parameter : query.split("&")) {
                String[] pair = parameter.split("=", 2);
                if (URLDecoder.decode(pair[0], StandardCharsets.UTF_8).equals("author"))
                    return pair.length == 1 ? "" : URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    static Book read(ResultSet row) throws SQLException {
        return new Book(row.getLong("id"), row.getString("title"), row.getString("author"),
                (Integer) row.getObject("year"), row.getString("isbn"));
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        start(port, System.getenv().getOrDefault("BOOK_DB", "books.db"));
        System.out.println("Book API listening on port " + port);
    }
}
