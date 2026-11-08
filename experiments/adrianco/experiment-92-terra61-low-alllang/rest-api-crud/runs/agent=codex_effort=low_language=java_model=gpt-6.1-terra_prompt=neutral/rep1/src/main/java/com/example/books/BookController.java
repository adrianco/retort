package com.example.books;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.net.URI;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class BookController {
    private final JdbcTemplate db;
    private final RowMapper<Book> mapper = (rs, row) -> new Book(rs.getLong("id"), rs.getString("title"), rs.getString("author"), (Integer) rs.getObject("year"), rs.getString("isbn"));

    public BookController(JdbcTemplate db) { this.db = db; }

    public record BookInput(@NotBlank String title, @NotBlank String author, Integer year, String isbn) {}
    public record Book(long id, String title, String author, Integer year, String isbn) {}

    @GetMapping("/health")
    public Map<String, String> health() { return Map.of("status", "ok"); }

    @PostMapping("/books")
    public ResponseEntity<Book> create(@Valid @RequestBody BookInput input) {
        KeyHolder keys = new GeneratedKeyHolder();
        db.update(connection -> {
            var statement = connection.prepareStatement("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", new String[]{"id"});
            statement.setString(1, input.title());
            statement.setString(2, input.author());
            if (input.year() == null) statement.setNull(3, java.sql.Types.INTEGER); else statement.setInt(3, input.year());
            statement.setString(4, input.isbn());
            return statement;
        }, keys);
        long id = keys.getKey().longValue();
        return ResponseEntity.created(URI.create("/books/" + id)).body(get(id));
    }

    @GetMapping("/books")
    public List<Book> list(@RequestParam(required = false) String author) {
        if (author == null) return db.query("SELECT * FROM books ORDER BY id", mapper);
        return db.query("SELECT * FROM books WHERE author = ? ORDER BY id", mapper, author);
    }

    @GetMapping("/books/{id}")
    public Book get(@PathVariable long id) {
        return db.query("SELECT * FROM books WHERE id = ?", mapper, id).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found"));
    }

    @PutMapping("/books/{id}")
    public Book update(@PathVariable long id, @Valid @RequestBody BookInput input) {
        int changed = db.update("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", input.title(), input.author(), input.year(), input.isbn(), id);
        if (changed == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found");
        return get(id);
    }

    @DeleteMapping("/books/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        if (db.update("DELETE FROM books WHERE id = ?", id) == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found");
        return ResponseEntity.noContent().build();
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, String>> invalid(MethodArgumentNotValidException ex) {
        return ResponseEntity.badRequest().body(Map.of("error", "Title and author are required"));
    }
}
