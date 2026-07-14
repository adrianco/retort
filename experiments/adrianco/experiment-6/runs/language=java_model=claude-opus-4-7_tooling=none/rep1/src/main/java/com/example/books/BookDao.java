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

public class BookDao {
    private final String jdbcUrl;

    public BookDao(String jdbcUrl) {
        this.jdbcUrl = jdbcUrl;
        init();
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void init() {
        String sql = "CREATE TABLE IF NOT EXISTS books (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "title TEXT NOT NULL," +
                "author TEXT NOT NULL," +
                "year INTEGER," +
                "isbn TEXT)";
        try (Connection c = connect(); Statement s = c.createStatement()) {
            s.execute(sql);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize database", e);
        }
    }

    public Book create(Book book) {
        String sql = "INSERT INTO books(title, author, year, isbn) VALUES(?,?,?,?)";
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet rs = ps.getGeneratedKeys()) {
                if (rs.next()) {
                    book.setId(rs.getLong(1));
                }
            }
            return book;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to insert book", e);
        }
    }

    public List<Book> findAll(String authorFilter) {
        StringBuilder sql = new StringBuilder("SELECT id, title, author, year, isbn FROM books");
        if (authorFilter != null && !authorFilter.isBlank()) {
            sql.append(" WHERE author = ?");
        }
        sql.append(" ORDER BY id");
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql.toString())) {
            if (authorFilter != null && !authorFilter.isBlank()) {
                ps.setString(1, authorFilter);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(map(rs));
                }
                return books;
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to query books", e);
        }
    }

    public Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(map(rs));
                }
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to query book", e);
        }
    }

    public Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            int updated = ps.executeUpdate();
            if (updated == 0) return Optional.empty();
            book.setId(id);
            return Optional.of(book);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to update book", e);
        }
    }

    public boolean delete(long id) {
        String sql = "DELETE FROM books WHERE id = ?";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setLong(1, id);
            return ps.executeUpdate() > 0;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to delete book", e);
        }
    }

    private Book map(ResultSet rs) throws SQLException {
        Integer year = rs.getInt("year");
        if (rs.wasNull()) year = null;
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                year,
                rs.getString("isbn")
        );
    }
}
