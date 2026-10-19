package com.example.bookapi;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

/**
 * REST endpoints for managing the book collection.
 */
@RestController
@RequestMapping("/books")
public class BookController {

    private final BookRepository repository;

    public BookController(BookRepository repository) {
        this.repository = repository;
    }

    /** POST /books — create a new book. */
    @PostMapping
    public ResponseEntity<Book> create(@RequestBody BookRequest request) {
        Validation.validateOrThrow(request);
        Book created = repository.create(request);
        return ResponseEntity
                .created(URI.create("/books/" + created.id()))
                .body(created);
    }

    /** GET /books — list all books, optionally filtered by ?author=. */
    @GetMapping
    public List<Book> list(@RequestParam(name = "author", required = false) String author) {
        if (author == null || author.isBlank()) {
            return repository.findAll();
        }
        return repository.findByAuthor(author);
    }

    /** GET /books/{id} — fetch a single book. */
    @GetMapping("/{id}")
    public Book get(@PathVariable long id) {
        return repository.findById(id)
                .orElseThrow(() -> new BookNotFoundException("Book with id " + id + " not found"));
    }

    /** PUT /books/{id} — update a book. */
    @PutMapping("/{id}")
    public Book update(@PathVariable long id, @RequestBody BookRequest request) {
        Validation.validateOrThrow(request);
        return repository.update(id, request)
                .orElseThrow(() -> new BookNotFoundException("Book with id " + id + " not found"));
    }

    /** DELETE /books/{id} — delete a book. */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        if (!repository.delete(id)) {
            throw new BookNotFoundException("Book with id " + id + " not found");
        }
        return ResponseEntity.noContent().build();
    }
}
