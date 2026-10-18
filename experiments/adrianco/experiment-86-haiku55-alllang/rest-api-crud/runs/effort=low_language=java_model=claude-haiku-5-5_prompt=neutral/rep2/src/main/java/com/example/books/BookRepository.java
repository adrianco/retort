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
 * JDBC-backed storage for books using SQLite. Holds a single connection; access is
 * serialized through synchronized methods, which is sufficient for this service.
 */
public class BookRepository implements AutoCloseable {

    private final Connection connection;

    /**
     * @param jdbcUrl e.g. {@code jdbc:sqlite:books.db} or {@code jdbc:sqlite::memory:}
     */
    public BookRepository(String jdbcUrl) {
        try {
            this.connection = DriverManager.getConnection(jdbcUrl);
            try (Statement st = connection.createStatement()) {
                st.executeUpdate("""
                        CREATE TABLE IF NOT EXISTS books (
                            id     INTEGER PRIMARY KEY AUTOINCREMENT,
                            title  TEXT NOT NULL,
                            author TEXT NOT NULL,
                            year   INTEGER,
                            isbn   TEXT
                        )""");
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to open database: " + jdbcUrl, e);
        }
    }

    public synchronized Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bind(ps, book);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                return book.withId(keys.getLong(1));
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to create book", e);
        }
    }

    public synchronized Optional<Book> findById(long id) {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to load book " + id, e);
        }
    }

    /**
     * Lists books ordered by id. If {@code author} is non-null, only books whose author
     * matches case-insensitively are returned.
     */
    public synchronized List<Book> findAll(String author) {
        String sql = "SELECT id, title, author, year, isbn FROM books";
        if (author != null) {
            sql += " WHERE author = ? COLLATE NOCASE";
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
            return books;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to list books", e);
        }
    }

    /** Replaces the stored fields of the book with the given id. Returns false if not found. */
    public synchronized boolean update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            bind(ps, book);
            ps.setLong(5, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to update book " + id, e);
        }
    }

    /** Deletes the book with the given id. Returns false if not found. */
    public synchronized boolean delete(long id) {
        try (PreparedStatement ps = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to delete book " + id, e);
        }
    }

    /** Cheap liveness probe used by the health endpoint. */
    public synchronized boolean ping() {
        try (Statement st = connection.createStatement();
             ResultSet rs = st.executeQuery("SELECT 1")) {
            return rs.next();
        } catch (SQLException e) {
            return false;
        }
    }

    @Override
    public synchronized void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            throw new IllegalStateException("Failed to close database", e);
        }
    }

    private static void bind(PreparedStatement ps, Book book) throws SQLException {
        ps.setString(1, book.title());
        ps.setString(2, book.author());
        if (book.year() == null) {
            ps.setNull(3, java.sql.Types.INTEGER);
        } else {
            ps.setInt(3, book.year());
        }
        if (book.isbn() == null) {
            ps.setNull(4, java.sql.Types.VARCHAR);
        } else {
            ps.setString(4, book.isbn());
        }
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
