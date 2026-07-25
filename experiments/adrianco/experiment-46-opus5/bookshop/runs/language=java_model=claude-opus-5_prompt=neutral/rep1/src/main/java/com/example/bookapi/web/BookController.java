package com.example.bookapi.web;

import com.example.bookapi.model.Book;
import com.example.bookapi.service.BookService;
import com.example.bookapi.web.dto.BookRequest;
import com.example.bookapi.web.dto.BookResponse;
import jakarta.validation.Valid;
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
import org.springframework.web.util.UriComponentsBuilder;

import java.util.List;

@RestController
@RequestMapping(path = "/books", produces = "application/json")
public class BookController {

    private final BookService service;

    public BookController(BookService service) {
        this.service = service;
    }

    @GetMapping
    public List<BookResponse> list(@RequestParam(name = "author", required = false) String author) {
        return service.list(author).stream().map(BookResponse::from).toList();
    }

    @GetMapping("/{id}")
    public BookResponse get(@PathVariable long id) {
        return BookResponse.from(service.get(id));
    }

    @PostMapping(consumes = "application/json")
    public ResponseEntity<BookResponse> create(@Valid @RequestBody BookRequest request) {
        Book created = service.create(request);
        return ResponseEntity
                .created(UriComponentsBuilder.fromPath("/books/{id}").buildAndExpand(created.id()).toUri())
                .body(BookResponse.from(created));
    }

    @PutMapping(path = "/{id}", consumes = "application/json")
    public BookResponse replace(@PathVariable long id, @Valid @RequestBody BookRequest request) {
        return BookResponse.from(service.replace(id, request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
