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
 * SQLite-backed storage for books. All methods are synchronised because a
 * single JDBC connection is shared across request threads.
 */
public class BookRepository implements AutoCloseable {

    private final Connection connection;

    /**
     * @param jdbcUrl a SQLite JDBC URL, e.g. {@code jdbc:sqlite:books.db} or {@code jdbc:sqlite::memory:}
     */
    public BookRepository(String jdbcUrl) throws SQLException {
        this.connection = DriverManager.getConnection(jdbcUrl);
        try (Statement statement = connection.createStatement()) {
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year INTEGER,
                        isbn TEXT
                    )""");
        }
    }

    public synchronized Book insert(BookRequest request) throws SQLException {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, request);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), request.title(), request.author(), request.year(), request.isbn());
            }
        }
    }

    public synchronized Optional<Book> findById(long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        }
    }

    /**
     * Lists books ordered by id. When {@code author} is non-null, only books whose
     * author matches case-insensitively are returned.
     */
    public synchronized List<Book> findAll(String author) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books";
        if (author != null) {
            sql += " WHERE LOWER(author) = LOWER(?)";
        }
        sql += " ORDER BY id";
        List<Book> books = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            if (author != null) {
                ps.setString(1, author);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(map(rs));
                }
            }
        }
        return books;
    }

    public synchronized Optional<Book> update(long id, BookRequest request) throws SQLException {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            bind(ps, request);
            ps.setLong(5, id);
            if (ps.executeUpdate() == 0) {
                return Optional.empty();
            }
        }
        return Optional.of(new Book(id, request.title(), request.author(), request.year(), request.isbn()));
    }

    public synchronized boolean delete(long id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    @Override
    public synchronized void close() throws SQLException {
        connection.close();
    }

    private static void bind(PreparedStatement ps, BookRequest request) throws SQLException {
        ps.setString(1, request.title());
        ps.setString(2, request.author());
        if (request.year() == null) {
            ps.setNull(3, java.sql.Types.INTEGER);
        } else {
            ps.setInt(3, request.year());
        }
        ps.setString(4, request.isbn());
    }

    private static Book map(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearValue = rs.wasNull() ? null : year;
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearValue,
                rs.getString("isbn"));
    }
}
