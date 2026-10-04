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

/**
 * SQLite-backed book storage. Holds a single connection; all access is
 * synchronized because the HTTP server handles requests on multiple threads.
 */
public class BookRepository implements AutoCloseable {
    private final Connection conn;

    /** @param jdbcUrl e.g. {@code jdbc:sqlite:books.db} or {@code jdbc:sqlite::memory:} */
    public BookRepository(String jdbcUrl) throws SQLException {
        conn = DriverManager.getConnection(jdbcUrl);
        try (Statement st = conn.createStatement()) {
            st.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id     INTEGER PRIMARY KEY AUTOINCREMENT,
                        title  TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year   INTEGER,
                        isbn   TEXT
                    )""");
        }
    }

    public synchronized Book create(Book book) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, book);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return book.withId(keys.getLong(1));
            }
        }
    }

    /** Lists books ordered by id; a non-null author restricts to that author (case-insensitive). */
    public synchronized List<Book> list(String author) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (author == null ? "" : " WHERE author = ? COLLATE NOCASE")
                + " ORDER BY id";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            if (author != null) {
                ps.setString(1, author);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(read(rs));
                }
                return books;
            }
        }
    }

    public synchronized Optional<Book> find(long id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(read(rs)) : Optional.empty();
            }
        }
    }

    /** @return the updated book, or empty if no book has that id */
    public synchronized Optional<Book> update(long id, Book book) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            bind(ps, book);
            ps.setLong(5, id);
            return ps.executeUpdate() == 0 ? Optional.empty() : Optional.of(book.withId(id));
        }
    }

    /** @return false if no book has that id */
    public synchronized boolean delete(long id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    @Override
    public synchronized void close() throws SQLException {
        conn.close();
    }

    private static void bind(PreparedStatement ps, Book book) throws SQLException {
        ps.setString(1, book.title());
        ps.setString(2, book.author());
        if (book.year() == null) {
            ps.setNull(3, Types.INTEGER);
        } else {
            ps.setInt(3, book.year());
        }
        ps.setString(4, book.isbn());
    }

    private static Book read(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearOrNull = rs.wasNull() ? null : year;
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"),
                yearOrNull, rs.getString("isbn"));
    }
}
