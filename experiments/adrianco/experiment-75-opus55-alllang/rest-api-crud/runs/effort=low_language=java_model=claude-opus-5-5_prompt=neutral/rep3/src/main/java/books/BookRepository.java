package books;

import java.sql.*;
import java.util.*;

public class BookRepository {
    public record Book(Long id, String title, String author, Integer year, String isbn) {}

    private final String url;

    public BookRepository(String url) {
        this.url = url;
        try (Connection c = conn(); Statement s = c.createStatement()) {
            s.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    private Connection conn() throws SQLException { return DriverManager.getConnection(url); }

    public synchronized Book create(Book b) throws SQLException {
        try (Connection c = conn(); PreparedStatement ps = c.prepareStatement(
                "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, b);
            ps.executeUpdate();
            try (ResultSet rs = ps.getGeneratedKeys()) { rs.next(); return withId(b, rs.getLong(1)); }
        }
    }

    public synchronized List<Book> list(String author) throws SQLException {
        String sql = author == null ? "SELECT * FROM books ORDER BY id" : "SELECT * FROM books WHERE author = ? ORDER BY id";
        try (Connection c = conn(); PreparedStatement ps = c.prepareStatement(sql)) {
            if (author != null) ps.setString(1, author);
            List<Book> out = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) { while (rs.next()) out.add(map(rs)); }
            return out;
        }
    }

    public synchronized Optional<Book> get(long id) throws SQLException {
        try (Connection c = conn(); PreparedStatement ps = c.prepareStatement("SELECT * FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) { return rs.next() ? Optional.of(map(rs)) : Optional.empty(); }
        }
    }

    public synchronized Optional<Book> update(long id, Book b) throws SQLException {
        try (Connection c = conn(); PreparedStatement ps = c.prepareStatement(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?")) {
            bind(ps, b);
            ps.setLong(5, id);
            return ps.executeUpdate() == 0 ? Optional.empty() : Optional.of(withId(b, id));
        }
    }

    public synchronized boolean delete(long id) throws SQLException {
        try (Connection c = conn(); PreparedStatement ps = c.prepareStatement("DELETE FROM books WHERE id=?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private static void bind(PreparedStatement ps, Book b) throws SQLException {
        ps.setString(1, b.title());
        ps.setString(2, b.author());
        if (b.year() == null) ps.setNull(3, Types.INTEGER); else ps.setInt(3, b.year());
        ps.setString(4, b.isbn());
    }

    private static Book withId(Book b, long id) { return new Book(id, b.title(), b.author(), b.year(), b.isbn()); }

    private static Book map(ResultSet rs) throws SQLException {
        int y = rs.getInt("year");
        Integer year = rs.wasNull() ? null : y;
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"), year, rs.getString("isbn"));
    }
}
