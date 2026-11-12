package books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/** SQLite-backed storage for books. Opens a short-lived connection per operation. */
public class BookRepository {
    private final String url;

    public BookRepository(String dbPath) {
        this.url = "jdbc:sqlite:" + dbPath;
        try (Connection c = connect(); Statement s = c.createStatement()) {
            s.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year INTEGER,
                        isbn TEXT
                    )""");
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to initialise database", e);
        }
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(url);
    }

    public Book create(Book b) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, b);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), b.title(), b.author(), b.year(), b.isbn());
            }
        }
    }

    /** Lists books ordered by id; if {@code author} is non-null, only exact (case-insensitive) matches. */
    public List<Book> list(String author) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (author != null ? " WHERE author = ? COLLATE NOCASE" : "") + " ORDER BY id";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            if (author != null) {
                ps.setString(1, author);
            }
            List<Book> out = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(map(rs));
                }
            }
            return out;
        }
    }

    public Optional<Book> find(long id) throws SQLException {
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement(
                     "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        }
    }

    /** Replaces the book with the given id. Returns empty if it does not exist. */
    public Optional<Book> update(long id, Book b) throws SQLException {
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement(
                     "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            bind(ps, b);
            ps.setLong(5, id);
            if (ps.executeUpdate() == 0) {
                return Optional.empty();
            }
            return Optional.of(new Book(id, b.title(), b.author(), b.year(), b.isbn()));
        }
    }

    public boolean delete(long id) throws SQLException {
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private static void bind(PreparedStatement ps, Book b) throws SQLException {
        ps.setString(1, b.title());
        ps.setString(2, b.author());
        if (b.year() == null) {
            ps.setNull(3, Types.INTEGER);
        } else {
            ps.setInt(3, b.year());
        }
        ps.setString(4, b.isbn());
    }

    private static Book map(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer y = rs.wasNull() ? null : year;
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"), y, rs.getString("isbn"));
    }
}
