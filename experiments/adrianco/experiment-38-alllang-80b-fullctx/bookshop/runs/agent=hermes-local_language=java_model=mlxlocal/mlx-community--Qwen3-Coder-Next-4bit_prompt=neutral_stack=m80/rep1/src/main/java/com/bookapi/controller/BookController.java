package com.bookapi.controller;

import com.bookapi.dto.BookRequest;
import com.bookapi.dto.BookResponse;
import com.bookapi.entity.Book;
import com.bookapi.service.BookService;
import com.bookapi.service.ResourceNotFoundException;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/books")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    @PostMapping
    public ResponseEntity<BookResponse> createBook(@Valid @RequestBody BookRequest request) {
        Book book = new Book();
        book.setTitle(request.getTitle());
        book.setAuthor(request.getAuthor());
        book.setYear(request.getYear());
        book.setIsbn(request.getIsbn());
        
        Book saved = bookService.createBook(book);
        BookResponse response = convertToResponse(saved);
        return ResponseEntity
                .created(URI.create("/api/books/" + saved.getId()))
                .body(response);
    }

    @GetMapping
    public ResponseEntity<List<BookResponse>> getAllBooks(
            @RequestParam(required = false) String author) {
        List<Book> books;
        if (author != null) {
            books = bookService.findByAuthor(author);
        } else {
            books = bookService.findAll();
        }
        List<BookResponse> responses = books.stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/{id}")
    public ResponseEntity<BookResponse> getBookById(@PathVariable Long id) {
        Book book = bookService.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + id));
        return ResponseEntity.ok(convertToResponse(book));
    }

    @PutMapping("/{id}")
    public ResponseEntity<BookResponse> updateBook(
            @PathVariable Long id,
            @Valid @RequestBody BookRequest request) {
        Book book = bookService.updateBook(id, request);
        return ResponseEntity.ok(convertToResponse(book));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteBook(@PathVariable Long id) {
        bookService.deleteBook(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("OK");
    }

    private BookResponse convertToResponse(Book book) {
        BookResponse response = new BookResponse();
        response.setId(book.getId());
        response.setTitle(book.getTitle());
        response.setAuthor(book.getAuthor());
        response.setYear(book.getYear());
        response.setIsbn(book.getIsbn());
        return response;
    }
}
