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
 * Stores books in a SQLite database via JDBC.
 *
 * <p>Keeps a single {@link Connection} open for the lifetime of the repository
 * and synchronizes access, which is sufficient for this service and keeps an
 * in-memory database alive across calls during tests.
 */
public final class BookRepository implements AutoCloseable {

    private final Connection connection;

    /**
     * Opens a repository against the given JDBC URL, e.g.
     * {@code jdbc:sqlite:books.db} or {@code jdbc:sqlite::memory:}.
     */
    public BookRepository(String jdbcUrl) {
        try {
            this.connection = DriverManager.getConnection(jdbcUrl);
            initSchema();
        } catch (SQLException e) {
            throw new RepositoryException("could not open database: " + e.getMessage(), e);
        }
    }

    private void initSchema() throws SQLException {
        try (Statement st = connection.createStatement()) {
            st.execute(
                "CREATE TABLE IF NOT EXISTS books ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "title TEXT NOT NULL, "
                    + "author TEXT NOT NULL, "
                    + "year INTEGER, "
                    + "isbn TEXT)");
        }
    }

    public synchronized Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (PreparedStatement ps =
                 connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            bindBook(ps, book);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getLong(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new RepositoryException("could not create book: " + e.getMessage(), e);
        }
    }

    public synchronized List<Book> findAll(String authorFilter) {
        StringBuilder sql = new StringBuilder("SELECT * FROM books");
        boolean filtering = authorFilter != null && !authorFilter.isEmpty();
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
            throw new RepositoryException("could not list books: " + e.getMessage(), e);
        }
    }

    public synchronized Optional<Book> findById(long id) {
        try (PreparedStatement ps =
                 connection.prepareStatement("SELECT * FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new RepositoryException("could not fetch book: " + e.getMessage(), e);
        }
    }

    /** Updates the book with the given id; returns the updated book if it existed. */
    public synchronized Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            bindBook(ps, book);
            ps.setLong(5, id);
            int rows = ps.executeUpdate();
            if (rows == 0) {
                return Optional.empty();
            }
            book.setId(id);
            return Optional.of(book);
        } catch (SQLException e) {
            throw new RepositoryException("could not update book: " + e.getMessage(), e);
        }
    }

    /** Deletes the book with the given id; returns true if a row was removed. */
    public synchronized boolean delete(long id) {
        try (PreparedStatement ps =
                 connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RepositoryException("could not delete book: " + e.getMessage(), e);
        }
    }

    private static void bindBook(PreparedStatement ps, Book book) throws SQLException {
        ps.setString(1, book.getTitle());
        ps.setString(2, book.getAuthor());
        if (book.getYear() != null) {
            ps.setInt(3, book.getYear());
        } else {
            ps.setNull(3, java.sql.Types.INTEGER);
        }
        ps.setString(4, book.getIsbn());
    }

    private static Book mapRow(ResultSet rs) throws SQLException {
        long id = rs.getLong("id");
        String title = rs.getString("title");
        String author = rs.getString("author");
        int yearValue = rs.getInt("year");
        Integer year = rs.wasNull() ? null : yearValue;
        String isbn = rs.getString("isbn");
        return new Book(id, title, author, year, isbn);
    }

    @Override
    public synchronized void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            // Best-effort close.
        }
    }

    /** Wraps low-level persistence failures. */
    public static final class RepositoryException extends RuntimeException {
        public RepositoryException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
