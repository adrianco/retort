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

public class BookRepository {
    private final String jdbcUrl;

    public BookRepository(String jdbcUrl) {
        this.jdbcUrl = jdbcUrl;
        init();
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void init() {
        String sql = "CREATE TABLE IF NOT EXISTS books (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "title TEXT NOT NULL, " +
                "author TEXT NOT NULL, " +
                "year INTEGER, " +
                "isbn TEXT)";
        try (Connection c = connect(); Statement s = c.createStatement()) {
            s.execute(sql);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize database", e);
        }
    }

    public Book create(Book book) {
        String sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)";
        try (Connection c = connect();
             PreparedStatement ps = c.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
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
        String sql = "SELECT id, title, author, year, isbn FROM books";
        if (authorFilter != null) sql += " WHERE author = ?";
        sql += " ORDER BY id";
        List<Book> books = new ArrayList<>();
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            if (authorFilter != null) ps.setString(1, authorFilter);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    books.add(map(rs));
                }
            }
            return books;
        } catch (SQLException e) {
            throw new RuntimeException("Failed to list books", e);
        }
    }

    public Optional<Book> findById(long id) {
        String sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return Optional.of(map(rs));
                return Optional.empty();
            }
        } catch (SQLException e) {
            throw new RuntimeException("Failed to load book", e);
        }
    }

    public Optional<Book> update(long id, Book book) {
        String sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) ps.setInt(3, book.getYear()); else ps.setNull(3, java.sql.Types.INTEGER);
            ps.setString(4, book.getIsbn());
            ps.setLong(5, id);
            int rows = ps.executeUpdate();
            if (rows == 0) return Optional.empty();
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
        Integer year = rs.getObject("year") == null ? null : rs.getInt("year");
        return new Book(
                rs.getLong("id"),
                rs.getString("title"),
                rs.getString("author"),
                year,
                rs.getString("isbn"));
    }
}
