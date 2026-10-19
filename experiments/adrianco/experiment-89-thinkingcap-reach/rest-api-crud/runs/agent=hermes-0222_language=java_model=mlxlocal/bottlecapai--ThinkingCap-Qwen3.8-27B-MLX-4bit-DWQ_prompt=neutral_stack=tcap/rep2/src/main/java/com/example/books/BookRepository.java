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

    private static final RowMapper<Book> ROW_MAPPER = (rs, rowNum) -> {
        Book book = new Book();
        book.setId(rs.getLong("id"));
        book.setTitle(rs.getString("title"));
        book.setAuthor(rs.getString("author"));
        int year = rs.getInt("year");
        book.setYear(rs.wasNull() ? null : year);
        book.setIsbn(rs.getString("isbn"));
        return book;
    };

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Book save(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.getTitle());
            ps.setString(2, book.getAuthor());
            if (book.getYear() == null) {
                ps.setNull(3, java.sql.Types.INTEGER);
            } else {
                ps.setInt(3, book.getYear());
            }
            ps.setString(4, book.getIsbn());
            return ps;
        }, keyHolder);
        book.setId(keyHolder.getKey().longValue());
        return book;
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", ROW_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                ROW_MAPPER, author);
    }

    public Optional<Book> findById(long id) {
        List<Book> results = jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?", ROW_MAPPER, id);
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    public Book update(long id, Book book) {
        jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                book.getTitle(),
                book.getAuthor(),
                book.getYear(),
                book.getIsbn(),
                id);
        return findById(id).orElseThrow();
    }

    public boolean deleteById(long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id) > 0;
    }
}
