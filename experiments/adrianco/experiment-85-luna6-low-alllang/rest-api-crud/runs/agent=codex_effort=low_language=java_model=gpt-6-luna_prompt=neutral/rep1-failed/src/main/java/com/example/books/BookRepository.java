package com.example.books;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

@Repository
public class BookRepository {
    private static final RowMapper<Book> BOOK_MAPPER = (rs, rowNum) ->
            new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"),
                    (Integer) rs.getObject("year"), rs.getString("isbn"));

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        jdbc.execute("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
    }

    public Book create(BookRequest request) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", Statement.RETURN_GENERATED_KEYS);
            statement.setString(1, request.title().trim());
            statement.setString(2, request.author().trim());
            statement.setObject(3, request.year());
            statement.setString(4, request.isbn());
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            return jdbc.queryForObject("SELECT * FROM books ORDER BY id DESC LIMIT 1", BOOK_MAPPER);
        }
        return findById(key.longValue()).orElseThrow();
    }

    public List<Book> findAll(String author) {
        if (author == null || author.isBlank()) {
            return jdbc.query("SELECT * FROM books ORDER BY id", BOOK_MAPPER);
        }
        return jdbc.query("SELECT * FROM books WHERE author = ? ORDER BY id", BOOK_MAPPER, author);
    }

    public Optional<Book> findById(long id) {
        return jdbc.query("SELECT * FROM books WHERE id = ?", BOOK_MAPPER, id).stream().findFirst();
    }

    public Optional<Book> update(long id, BookRequest request) {
        int changed = jdbc.update("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                request.title().trim(), request.author().trim(), request.year(), request.isbn(), id);
        return changed == 0 ? Optional.empty() : findById(id);
    }

    public boolean delete(long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id) > 0;
    }
}
