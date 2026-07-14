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
 * Data access for {@link Book} records, backed by SQLite.
 *
 * <p>A single shared connection is kept open for the lifetime of the DAO.
 * SQLite serializes writes internally, and Javalin's request handling does not
 * require a connection pool for this small service.
 */
public class BookDao implements AutoCloseable {

    private final Connection connection;

    public BookDao(String jdbcUrl) {
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

    public Book create(Book book) {
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

    public List<Book> findAll(String authorFilter) {
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

    public Optional<Book> findById(long id) {
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

    public Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            setNullableInt(ps, 3, book.getYear());
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            int updated = ps.executeUpdate();
            if (updated == 0) {
                return Optional.empty();
            }
            book.setId(id);
            return Optional.of(book);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book " + id, e);
        }
    }

    public boolean delete(long id) {
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
        int year = rs.getInt("year");
        Integer yearValue = rs.wasNull() ? null : year;
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearValue,
                rs.getString("isbn"));
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            // best effort on shutdown
        }
    }
}
