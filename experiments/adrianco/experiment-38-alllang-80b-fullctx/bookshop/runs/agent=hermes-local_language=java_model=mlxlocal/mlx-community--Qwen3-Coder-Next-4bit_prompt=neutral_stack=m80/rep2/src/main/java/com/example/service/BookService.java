package com.example.service;

import com.example.model.Book;
import com.example.repository.BookRepository;

import java.util.List;
import java.util.Optional;

public class BookService {
    private final BookRepository repository;

    public BookService(BookRepository repository) {
        this.repository = repository;
    }

    public Book createBook(Book book) {
        if (book.getTitle() == null || book.getTitle().trim().isEmpty()) {
            throw new IllegalArgumentException("Title is required");
        }
        if (book.getAuthor() == null || book.getAuthor().trim().isEmpty()) {
            throw new IllegalArgumentException("Author is required");
        }
        return repository.save(book);
    }

    public Optional<Book> getBookById(Long id) {
        return repository.findById(id);
    }

    public List<Book> getAllBooks() {
        return repository.findAll();
    }

    public List<Book> findBooksByAuthor(String author) {
        if (author == null || author.trim().isEmpty()) {
            return repository.findAll();
        }
        return repository.findByAuthor(author);
    }

    public Optional<Book> updateBook(Book book) {
        if (book.getId() == null) {
            throw new IllegalArgumentException("Book ID is required for update");
        }
        if (book.getTitle() == null || book.getTitle().trim().isEmpty()) {
            throw new IllegalArgumentException("Title is required");
        }
        if (book.getAuthor() == null || book.getAuthor().trim().isEmpty()) {
            throw new IllegalArgumentException("Author is required");
        }
        return repository.findById(book.getId())
                .map(existing -> repository.save(book));
    }

    public boolean deleteBook(Long id) {
        return repository.findById(id)
                .map(book -> {
                    repository.delete(id);
                    return true;
                })
                .orElse(false);
    }
}
