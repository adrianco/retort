package com.example.bookapi.repository;

import com.example.bookapi.model.Book;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

/** Data access for the {@code books} table. */
@Repository
public class BookRepository {

    private static final String COLUMNS = "id, title, author, year, isbn, created_at, updated_at";

    private static final RowMapper<Book> ROW_MAPPER = (ResultSet rs, int rowNum) -> new Book(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("author"),
            nullableInt(rs, "year"),
            rs.getString("isbn"),
            Instant.parse(rs.getString("created_at")),
            Instant.parse(rs.getString("updated_at")));

    private final JdbcTemplate jdbc;

    public BookRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Book> findAll() {
        return jdbc.query("SELECT " + COLUMNS + " FROM books ORDER BY id", ROW_MAPPER);
    }

    /** Case-insensitive exact match on the author name. */
    public List<Book> findByAuthor(String author) {
        return jdbc.query(
                "SELECT " + COLUMNS + " FROM books WHERE author COLLATE NOCASE = ? ORDER BY id",
                ROW_MAPPER,
                author.trim());
    }

    public Optional<Book> findById(long id) {
        return jdbc.query("SELECT " + COLUMNS + " FROM books WHERE id = ?", ROW_MAPPER, id)
                .stream()
                .findFirst();
    }

    /** True if any book other than {@code excludedId} already uses this ISBN. */
    public boolean existsByIsbn(String isbn, Long excludedId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM books WHERE isbn = ? AND id <> ?",
                Integer.class,
                isbn,
                excludedId == null ? -1L : excludedId);
        return count != null && count > 0;
    }

    /** Inserts the book and returns it with the generated id applied. */
    public Book insert(Book book) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(
                    "INSERT INTO books (title, author, year, isbn, created_at, updated_at) "
                            + "VALUES (?, ?, ?, ?, ?, ?)",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, book.title());
            ps.setString(2, book.author());
            setNullableInt(ps, 3, book.year());
            ps.setString(4, book.isbn());
            ps.setString(5, book.createdAt().toString());
            ps.setString(6, book.updatedAt().toString());
            return ps;
        }, keyHolder);

        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Insert did not return a generated id");
        }
        return new Book(
                key.longValue(),
                book.title(),
                book.author(),
                book.year(),
                book.isbn(),
                book.createdAt(),
                book.updatedAt());
    }

    /** Replaces the mutable fields of an existing row. Returns the number of rows changed. */
    public int update(Book book) {
        return jdbc.update(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
                book.title(),
                book.author(),
                book.year(),
                book.isbn(),
                book.updatedAt().toString(),
                book.id());
    }

    /** Returns the number of rows deleted (0 when the id is unknown). */
    public int deleteById(long id) {
        return jdbc.update("DELETE FROM books WHERE id = ?", id);
    }

    private static Integer nullableInt(ResultSet rs, String column) throws SQLException {
        int value = rs.getInt(column);
        return rs.wasNull() ? null : value;
    }

    private static void setNullableInt(PreparedStatement ps, int index, Integer value) throws SQLException {
        if (value == null) {
            ps.setNull(index, Types.INTEGER);
        } else {
            ps.setInt(index, value);
        }
    }
}
