package com.example.books;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * SQLite-backed data access for books. Holds a single connection, so all
 * operations are synchronized; SQLite serializes writers anyway.
 */
public class BookDao {
    private final Connection conn;

    public BookDao(Connection conn) throws SQLException {
        this.conn = conn;
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
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
            }
            ps.setString(4, book.getIsbn());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                keys.next();
                book.setId(keys.getInt(1));
            }
        }
        return book;
    }

    public synchronized List<Book> findAll(String author) throws SQLException {
        String sql = "SELECT id, title, author, year, isbn FROM books";
        if (author != null) {
            sql += " WHERE author = ?";
        }
        sql += " ORDER BY id";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            if (author != null) {
                ps.setString(1, author);
            }
            try (ResultSet rs = ps.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (rs.next()) {
                    books.add(fromRow(rs));
                }
                return books;
            }
        }
    }

    public synchronized Optional<Book> findById(int id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?")) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? Optional.of(fromRow(rs)) : Optional.empty();
            }
        }
    }

    public synchronized boolean update(int id, Book book) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() != null) {
                ps.setInt(3, book.getYear());
            } else {
                ps.setNull(3, java.sql.Types.INTEGER);
            }
            ps.setString(4, book.getIsbn());
            ps.setInt(5, id);
            return ps.executeUpdate() > 0;
        }
    }

    public synchronized boolean delete(int id) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("DELETE FROM books WHERE id = ?")) {
            ps.setInt(1, id);
            return ps.executeUpdate() > 0;
        }
    }

    private static Book fromRow(ResultSet rs) throws SQLException {
        int year = rs.getInt("year");
        Integer yearOrNull = rs.wasNull() ? null : year;
        return new Book(
                rs.getInt("id"),
                rs.getString("title"),
                rs.getString("author"),
                yearOrNull,
                rs.getString("isbn"));
    }
}
