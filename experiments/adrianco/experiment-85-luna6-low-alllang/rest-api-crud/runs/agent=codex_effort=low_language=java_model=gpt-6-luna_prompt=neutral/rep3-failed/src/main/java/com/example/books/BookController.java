package com.example.books;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
public class BookController {
    private final JdbcTemplate jdbc;
    private final RowMapper<Book> mapper = (rs, row) -> {
        Number year = (Number) rs.getObject("year");
        return new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"),
                year == null ? null : year.intValue(), rs.getString("isbn"));
    };

    public BookController(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @PostMapping("/books")
    public ResponseEntity<Book> create(@Valid @RequestBody BookRequest request) {
        KeyHolder keys = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            var statement = connection.prepareStatement("INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)", new String[] {"id"});
            statement.setString(1, request.title().trim());
            statement.setString(2, request.author().trim());
            if (request.year() == null) statement.setNull(3, java.sql.Types.INTEGER); else statement.setInt(3, request.year());
            statement.setString(4, request.isbn());
            return statement;
        }, keys);
        Book created = find(keys.getKey().longValue());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/books")
    public List<Book> list(@RequestParam(required = false) String author) {
        if (author == null || author.isBlank()) return jdbc.query("SELECT * FROM books ORDER BY id", mapper);
        return jdbc.query("SELECT * FROM books WHERE lower(author) = lower(?) ORDER BY id", mapper, author.trim());
    }

    @GetMapping("/books/{id}")
    public Book get(@PathVariable long id) { return find(id); }

    @PutMapping("/books/{id}")
    public Book update(@PathVariable long id, @Valid @RequestBody BookRequest request) {
        find(id);
        jdbc.update("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", request.title().trim(), request.author().trim(), request.year(), request.isbn(), id);
        return find(id);
    }

    @DeleteMapping("/books/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        int removed = jdbc.update("DELETE FROM books WHERE id = ?", id);
        if (removed == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found");
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/health")
    public Health health() { return new Health("ok"); }

    private Book find(long id) {
        List<Book> books = jdbc.query("SELECT * FROM books WHERE id = ?", mapper, id);
        if (books.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found");
        return books.get(0);
    }

    public record Health(String status) { }
}
