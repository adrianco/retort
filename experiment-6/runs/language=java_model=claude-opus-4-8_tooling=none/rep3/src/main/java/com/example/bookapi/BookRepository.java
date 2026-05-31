package com.example.bookapi;

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
 * SQLite-backed storage for {@link Book} records.
 */
public class BookRepository implements AutoCloseable {

    private final Connection connection;

    /**
     * @param jdbcUrl e.g. "jdbc:sqlite:books.db" for a file, or
     *                "jdbc:sqlite::memory:" for an in-memory database.
     */
    public BookRepository(String jdbcUrl) {
        try {
            this.connection = DriverManager.getConnection(jdbcUrl);
            initSchema();
        } catch (SQLException e) {
            throw new RuntimeException("Failed to open database: " + jdbcUrl, e);
        }
    }

    private void initSchema() throws SQLException {
        try (Statement st = connection.createStatement()) {
            st.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """);
        }
    }

    public synchronized Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getLong(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to create book", e);
        }
    }

    public synchronized List<Book> findAll(String authorFilter) {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        boolean filtering = authorFilter != null && !authorFilter.isBlank();
        if (filtering) {
            sql.append(" WHERE author = ?");
        }
        sql.append(" ORDER BY id");
        try (PreparedStatement ps = connection.prepareStatement(sql.toString())) {
            if (filtering) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(mapRow(rs));
                }
                return books;
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list books", e);
        }
    }

    public synchronized Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to fetch book " + id, e);
        }
    }

    /**
     * Updates the book with the given id. Returns the updated book, or empty if
     * no book with that id exists.
     */
    public synchronized Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            int rows = ps.executeUpdate();
            if (rows == 0) {
                return Optional.empty();
            }
            book.setId(id);
            return Optional.of(book);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book " + id, e);
        }
    }

    /**
     * Deletes the book with the given id. Returns true if a row was removed.
     */
    public synchronized boolean delete(long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete book " + id, e);
        }
    }

    private static void setNullableInt(PreparedStatement ps, int index, Integer value) throws SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.INTEGER);
        } else {
            ps.setInt(index, value);
        }
    }

    private static Book mapRow(ResultSet rs) throws SQLException {
        Integer year = rs.getInt("year");
        if (rs.wasNull()) {
            year = null;
        }
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                year,
                rs.getString("isbn"));
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            // best effort
        }
    }
}
