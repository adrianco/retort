package com.example.books;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public final class BookRepository implements AutoCloseable {
    private final Connection connection;

    public BookRepository(String databaseUrl) throws SQLException {
        connection = DriverManager.getConnection(databaseUrl);
        try (Statement statement = connection.createStatement()) {
            statement.executeUpdate("""
                CREATE TABLE IF NOT EXISTS books (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  author TEXT NOT NULL,
                  year INTEGER,
                  isbn TEXT
                )
                """);
        }
    }

    public Book create(BookRequest request) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)", Statement.RETURN_GENERATED_KEYS)) {
            setValues(statement, request);
            statement.executeUpdate();
            try (ResultSet keys = statement.getGeneratedKeys()) {
                keys.next();
                return new Book(keys.getLong(1), request.title(), request.author(), request.year(), request.isbn());
            }
        }
    }

    public List<Book> findAll(String author) throws SQLException {
        String sql = author == null ? "SELECT * FROM books ORDER BY id" : "SELECT * FROM books WHERE author = ? ORDER BY id";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            if (author != null) statement.setString(1, author);
            try (ResultSet results = statement.executeQuery()) {
                List<Book> books = new ArrayList<>();
                while (results.next()) books.add(toBook(results));
                return books;
            }
        }
    }

    public Optional<Book> findById(long id) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("SELECT * FROM books WHERE id = ?")) {
            statement.setLong(1, id);
            try (ResultSet results = statement.executeQuery()) {
                return results.next() ? Optional.of(toBook(results)) : Optional.empty();
            }
        }
    }

    public Optional<Book> update(long id, BookRequest request) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")) {
            setValues(statement, request);
            statement.setLong(5, id);
            return statement.executeUpdate() == 1 ? findById(id) : Optional.empty();
        }
    }

    public boolean delete(long id) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("DELETE FROM books WHERE id = ?")) {
            statement.setLong(1, id);
            return statement.executeUpdate() == 1;
        }
    }

    private static void setValues(PreparedStatement statement, BookRequest request) throws SQLException {
        statement.setString(1, request.title());
        statement.setString(2, request.author());
        if (request.year() == null) statement.setNull(3, Types.INTEGER); else statement.setInt(3, request.year());
        statement.setString(4, request.isbn());
    }

    private static Book toBook(ResultSet result) throws SQLException {
        int year = result.getInt("year");
        return new Book(result.getLong("id"), result.getString("title"), result.getString("author"),
                result.wasNull() ? null : year, result.getString("isbn"));
    }

    @Override public void close() throws SQLException { connection.close(); }
}
