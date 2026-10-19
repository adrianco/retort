package com.example.bookapi;

import jakarta.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.List;
import java.util.Optional;

/**
 * SQLite-backed persistence for books (via Spring JdbcTemplate).
 */
@Repository
public class BookRepository {

    private static final RowMapper<Book> ROW_MAPPER = (rs, rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            (Integer) rs.getObject("year"),
            rs.getString("isbn")
    );

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @PostConstruct
    void initSchema() {
        jdbc.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """);
    }

    public Book create(BookRequest request) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, request.title());
            ps.setString(2, request.author());
            setNullableInt(ps, 3, request.year());
            setNullableString(ps, 4, request.isbn());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        long id = key != null ? key.longValue() : 0L;
        return findById(id).orElseThrow(
                () -> new IllegalStateException("Insert succeeded but book " + id + " not found"));
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT id, title, author, year, isbn FROM books ORDER BY id", ROW_MAPPER);
    }

    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
                ROW_MAPPER, author);
    }

    public Optional<Book> findById(long id) {
        List<Book> rows = jdbc.query(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?", ROW_MAPPER, id);
        return rows.isEmpty() ? Optional.empty() : Optional.of(rows.get(0));
    }

    /**
     * Replaces the stored book with the given values.
     *
     * @return the updated book, or empty if no book has the given id
     */
    public Optional<Book> update(long id, BookRequest request) {
        int updated = jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                request.title(), request.author(), request.year(), request.isbn(), id);
        return updated > 0 ? findById(id) : Optional.empty();
    }

    /**
     * @return true if a row was deleted, false if no book has the given id
     */
    public boolean delete(long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id) > 0;
    }

    private static void setNullableInt(PreparedStatement ps, int index, Integer value)
            throws java.sql.SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.INTEGER);
        } else {
            ps.setInt(index, value);
        }
    }

    private static void setNullableString(PreparedStatement ps, int index, String value)
            throws java.sql.SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.VARCHAR);
        } else {
            ps.setString(index, value);
        }
    }
}
