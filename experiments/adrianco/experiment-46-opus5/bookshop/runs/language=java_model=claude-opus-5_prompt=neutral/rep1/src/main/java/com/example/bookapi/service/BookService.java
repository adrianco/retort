package com.example.bookapi.service;

import com.example.bookapi.error.BookNotFoundException;
import com.example.bookapi.error.DuplicateIsbnException;
import com.example.bookapi.model.Book;
import com.example.bookapi.repository.BookRepository;
import com.example.bookapi.web.dto.BookRequest;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.List;

/** Business rules for the book collection. */
@Service
public class BookService {

    private final BookRepository repository;
    private final Clock clock;

    public BookService(BookRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    /** All books, optionally narrowed to a single author (case-insensitive). */
    public List<Book> list(String author) {
        if (author == null || author.isBlank()) {
            return repository.findAll();
        }
        return repository.findByAuthor(author);
    }

    public Book get(long id) {
        return repository.findById(id).orElseThrow(() -> new BookNotFoundException(id));
    }

    @Transactional
    public Book create(BookRequest request) {
        String isbn = request.normalisedIsbn();
        requireUniqueIsbn(isbn, null);

        Instant now = clock.instant();
        Book toInsert = new Book(null, request.title(), request.author(), request.year(), isbn, now, now);
        try {
            return repository.insert(toInsert);
        } catch (DataAccessException e) {
            throw translate(e, isbn);
        }
    }

    /** Full replacement of an existing book; 404 if the id is unknown. */
    @Transactional
    public Book replace(long id, BookRequest request) {
        Book existing = get(id);
        String isbn = request.normalisedIsbn();
        requireUniqueIsbn(isbn, id);

        Book updated = new Book(
                id,
                request.title(),
                request.author(),
                request.year(),
                isbn,
                existing.createdAt(),
                clock.instant());
        try {
            if (repository.update(updated) == 0) {
                throw new BookNotFoundException(id);
            }
        } catch (DataAccessException e) {
            throw translate(e, isbn);
        }
        return updated;
    }

    @Transactional
    public void delete(long id) {
        if (repository.deleteById(id) == 0) {
            throw new BookNotFoundException(id);
        }
    }

    private void requireUniqueIsbn(String isbn, Long excludedId) {
        if (isbn != null && repository.existsByIsbn(isbn, excludedId)) {
            throw new DuplicateIsbnException(isbn);
        }
    }

    /**
     * The unique index is the real guard against duplicate ISBNs; the pre-check
     * above only lets us fail early with a friendlier message. SQLite reports the
     * violation as a plain error string, so it has to be matched on text.
     */
    private RuntimeException translate(DataAccessException e, String isbn) {
        String message = String.valueOf(e.getMostSpecificCause().getMessage());
        if (message.contains("UNIQUE constraint failed") && message.contains("isbn")) {
            return new DuplicateIsbnException(isbn);
        }
        return e;
    }
}
