package com.example.books;

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
 * SQLite-backed book storage. A single connection is shared and access is
 * synchronized, which also keeps in-memory databases alive for the lifetime
 * of the repository.
 */
public class BookRepository implements AutoCloseable {
    private final Connection conn;

    public BookRepository(String jdbcUrl) throws SQLException {
        this.conn = DriverManager.getConnection(jdbcUrl);
        try (Statement st = conn.createStatement()) {
            st.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year INTEGER,
                        isbn TEXT
                    )""");
        }
    }

    public synchronized Book create(Book book) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, book);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), book.title(), book.author(), book.year(), book.isbn());
            }
        }
    }

    /** Lists all books, optionally restricted to an exact (case-insensitive) author match. */
    public synchronized List<Book> list(String author) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books"
                + (author != null ? " WHERE author = ? COLLATE NOCASE" : "")
                + " ORDER BY id";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
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

    public synchronized Optional<Book> find(long id) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        }
    }

    public synchronized Optional<Book> update(long id, Book book) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            bind(ps, book);
            ps.setLong(5, id);
            if (ps.executeUpdate() == 0) {
                return Optional.empty();
            }
            return Optional.of(new Book(id, book.title(), book.author(), book.year(), book.isbn()));
        }
    }

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

    private static Book map(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearOrNull = rs.wasNull() ? null : year;
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"),
                yearOrNull, rs.getString("isbn"));
    }
}
