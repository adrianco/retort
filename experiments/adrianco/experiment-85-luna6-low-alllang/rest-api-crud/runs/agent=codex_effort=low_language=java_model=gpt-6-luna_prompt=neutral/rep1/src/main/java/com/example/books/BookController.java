package com.example.books;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/books")
public class BookController {
    private final BookRepository books;

    public BookController(BookRepository books) { this.books = books; }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Book create(@Valid @RequestBody BookRequest request) { return books.create(request); }

    @GetMapping
    public List<Book> list(@RequestParam(required = false) String author) { return books.findAll(author); }

    @GetMapping("/{id}")
    public Book get(@PathVariable long id) { return books.findById(id).orElseThrow(() -> new BookNotFoundException(id)); }

    @PutMapping("/{id}")
    public Book update(@PathVariable long id, @Valid @RequestBody BookRequest request) {
        return books.update(id, request).orElseThrow(() -> new BookNotFoundException(id));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable long id) {
        if (!books.delete(id)) throw new BookNotFoundException(id);
    }
}
