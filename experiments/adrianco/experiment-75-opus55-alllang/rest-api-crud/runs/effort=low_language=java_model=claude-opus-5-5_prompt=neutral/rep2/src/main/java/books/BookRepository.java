package books;

import java.sql.*;
import java.util.*;

public class BookRepository {
    private final String url;

    public BookRepository(String url) throws SQLException {
        this.url = url;
        try (Connection c = conn(); Statement s = c.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
        }
    }

    private Connection conn() throws SQLException { return DriverManager.getConnection(url); }

    public synchronized Map<String, Object> create(Map<String, Object> b) throws SQLException {
        try (Connection c = conn(); PreparedStatement p = c.prepareStatement(
                "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", Statement.RETURN_GENERATED_KEYS)) {
            bind(p, b);
            p.executeUpdate();
            try (ResultSet k = p.getGeneratedKeys()) { k.next(); return find(k.getLong(1)).orElseThrow(); }
        }
    }

    public synchronized List<Map<String, Object>> list(String author) throws SQLException {
        String sql = author == null ? "SELECT * FROM books ORDER BY id" : "SELECT * FROM books WHERE author = ? ORDER BY id";
        try (Connection c = conn(); PreparedStatement p = c.prepareStatement(sql)) {
            if (author != null) p.setString(1, author);
            List<Map<String, Object>> out = new ArrayList<>();
            try (ResultSet r = p.executeQuery()) { while (r.next()) out.add(row(r)); }
            return out;
        }
    }

    public synchronized Optional<Map<String, Object>> find(long id) throws SQLException {
        try (Connection c = conn(); PreparedStatement p = c.prepareStatement("SELECT * FROM books WHERE id = ?")) {
            p.setLong(1, id);
            try (ResultSet r = p.executeQuery()) { return r.next() ? Optional.of(row(r)) : Optional.empty(); }
        }
    }

    public synchronized Optional<Map<String, Object>> update(long id, Map<String, Object> b) throws SQLException {
        try (Connection c = conn(); PreparedStatement p = c.prepareStatement(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?")) {
            bind(p, b);
            p.setLong(5, id);
            return p.executeUpdate() == 0 ? Optional.empty() : find(id);
        }
    }

    public synchronized boolean delete(long id) throws SQLException {
        try (Connection c = conn(); PreparedStatement p = c.prepareStatement("DELETE FROM books WHERE id=?")) {
            p.setLong(1, id);
            return p.executeUpdate() > 0;
        }
    }

    private static void bind(PreparedStatement p, Map<String, Object> b) throws SQLException {
        p.setString(1, (String) b.get("title"));
        p.setString(2, (String) b.get("author"));
        if (b.get("year") == null) p.setNull(3, Types.INTEGER); else p.setInt(3, ((Number) b.get("year")).intValue());
        p.setString(4, (String) b.get("isbn"));
    }

    private static Map<String, Object> row(ResultSet r) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", r.getLong("id"));
        m.put("title", r.getString("title"));
        m.put("author", r.getString("author"));
        int y = r.getInt("year");
        m.put("year", r.wasNull() ? null : y);
        m.put("isbn", r.getString("isbn"));
        return m;
    }
}
