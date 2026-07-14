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
 * SQLite-backed storage for {@link Book} entities.
 *
 * <p>The JDBC URL is supplied at construction time so the same code can run
 * against a file-based database (production) or an in-memory database (tests).
 */
public class BookRepository {

    private final String jdbcUrl;

    public BookRepository(String jdbcUrl) {
        this.jdbcUrl = jdbcUrl;
        initSchema();
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void initSchema() {
        String ddl = """
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT    NOT NULL,
                    author TEXT    NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """;
        try (Connection conn = connect(); Statement stmt = conn.createStatement()) {
            stmt.execute(ddl);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize database schema", e);
        }
    }

    public Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) {
                    book.setId(keys.getInt(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to create book", e);
        }
    }

    public List<Book> findAll(String authorFilter) {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        boolean filter = authorFilter != null && !authorFilter.isBlank();
        if (filter) {
            sql.append(" WHERE author = ?");
        }
        sql.append(" ORDER BY id");
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql.toString())) {
            if (filter) {
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

    public Optional<Book> findById(int id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRow(rs));
                }
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to fetch book", e);
        }
    }

    /**
     * Updates an existing book. Returns the updated book, or empty if no row
     * with the given id exists.
     */
    public Optional<Book> update(int id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.setInt(5, id);
            int rows = ps.executeUpdate();
            if (rows == 0) {
                return Optional.empty();
            }
            book.setId(id);
            return Optional.of(book);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book", e);
        }
    }

    /** Deletes a book by id. Returns true if a row was removed. */
    public boolean delete(int id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection conn = connect();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete book", e);
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
        int year = rs.getInt("year");
        Integer yearValue = rs.wasNull() ? null : year;
        return new Book(
                rs.getInt("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearValue,
                rs.getString("isbn"));
    }
}
