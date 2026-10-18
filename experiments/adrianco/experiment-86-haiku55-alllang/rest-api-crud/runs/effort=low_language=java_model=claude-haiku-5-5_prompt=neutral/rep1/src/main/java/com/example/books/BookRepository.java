package com.example.books;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * SQLite-backed storage for books. All methods are synchronized because a
 * single JDBC connection is shared across HTTP handler threads.
 */
public class BookRepository implements AutoCloseable {

    private final Connection connection;

    /**
     * Opens (and creates if needed) the database at the given JDBC URL.
     *
     * @param jdbcUrl e.g. {@code jdbc:sqlite:books.db} or {@code jdbc:sqlite::memory:}
     */
    public BookRepository(String jdbcUrl) throws SQLException {
        this.connection = DriverManager.getConnection(jdbcUrl);
        try (Statement stmt = connection.createStatement()) {
            stmt.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS books (
                        id     INTEGER PRIMARY KEY AUTOINCREMENT,
                        title  TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year   INTEGER,
                        isbn   TEXT
                    )""");
        }
    }

    public synchronized Book create(BookInput input) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, input);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), input.title(), input.author(), input.year(), input.isbn());
            }
        }
    }

    public synchronized Optional<Book> findById(long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("SELECT * FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        }
    }

    /**
     * Lists books, optionally restricted to one author (case-insensitive exact match).
     *
     * @param author author filter, or {@code null} for all books
     */
    public synchronized List<Book> findAll(String author) throws SQLException {
        String sql = "SELECT * FROM books";
        if (author != null) {
            sql += " WHERE author = ? COLLATE NOCASE";
        }
        sql += " ORDER BY id";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            if (author != null) {
                ps.setString(1, author);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(map(rs));
                }
                return books;
            }
        }
    }

    /** @return the updated book, or empty if no book has that id */
    public synchronized Optional<Book> update(long id, BookInput input) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            bind(ps, input);
            ps.setLong(5, id);
            if (ps.executeUpdate() == 0) {
                return Optional.empty();
            }
        }
        return Optional.of(new Book(id, input.title(), input.author(), input.year(), input.isbn()));
    }

    /** @return true if a book was deleted */
    public synchronized boolean delete(long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    /** @return true if the database responds to a trivial query */
    public synchronized boolean ping() {
        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT 1")) {
            return rs.next();
        } catch (SQLException e) {
            return false;
        }
    }

    @Override
    public synchronized void close() throws SQLException {
        connection.close();
    }

    private static void bind(PreparedStatement ps, BookInput input) throws SQLException {
        ps.setString(1, input.title());
        ps.setString(2, input.author());
        if (input.year() == null) {
            ps.setNull(3, java.sql.Types.INTEGER);
        } else {
            ps.setInt(3, input.year());
        }
        ps.setString(4, input.isbn());
    }

    private static Book map(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearValue = rs.wasNull() ? null : year;
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"),
                yearValue, rs.getString("isbn"));
    }
}
